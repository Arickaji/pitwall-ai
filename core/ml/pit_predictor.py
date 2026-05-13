"""
PitWall AI — Pit Stop Prediction Model
XGBoost classifier predicting whether a driver will pit
on the current lap given race state features.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import LabelEncoder

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MODEL_DIR = _PROJECT_ROOT / "data" / "ml" / "models"
_DATASET_PATH = _PROJECT_ROOT / "data" / "ml" / "training_dataset.parquet"


# ── Feature Configuration ──────────────────────────────────────────────────────

# Numerical features used for training
NUMERICAL_FEATURES = [
    "LapNumber",
    "LapTimeSeconds",
    "LapTimeTrend",
    "TyreLife",
    "Stint",
    "Position",
    "GapAhead",
    "GapBehind",
    "LapsRemaining",
    "DegRate",
    "SpeedFL",
]

# Categorical features — will be label encoded
CATEGORICAL_FEATURES = [
    "Compound",
    "Circuit",
]

TARGET = "PittedNextLap"


# ── Data Preparation ───────────────────────────────────────────────────────────


def prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Prepare feature matrix and target vector for training.

    Handles:
    - Selecting relevant columns
    - Label encoding categorical features
    - Filling missing values
    - Returning encoders for inference

    Args:
        df: Training dataset DataFrame

    Returns:
        tuple: (X, y, encoders) where encoders is dict of LabelEncoders
    """
    df = df.copy()

    # Fill missing numerical values with median
    for col in NUMERICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # Label encode categorical features
    encoders = {}
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le

    # Build feature list from available columns
    feature_cols = [
        c for c in NUMERICAL_FEATURES + CATEGORICAL_FEATURES if c in df.columns
    ]

    X = df[feature_cols].values
    y = df[TARGET].values

    logger.info(
        f"Features prepared: {X.shape[0]} rows × {X.shape[1]} features | "
        f"Pit stops: {y.sum()} ({y.mean():.2%})"
    )

    return X, y, encoders


# ── Model Training ─────────────────────────────────────────────────────────────


def train_pit_predictor(
    dataset_path: Path = _DATASET_PATH,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """
    Train pit stop prediction model.

    Uses GradientBoostingClassifier with class_weight handling
    via sample_weight to address 3.4% pit stop class imbalance.

    Cross-validates across seasons to avoid data leakage:
    train on 2022-2023, test on 2024.

    Args:
        dataset_path: Path to training Parquet file
        test_size: Fraction of data for testing
        random_state: Random seed for reproducibility

    Returns:
        dict: Training results with model, metrics, encoders
    """
    logger.info("Loading training dataset...")
    df = pd.read_parquet(dataset_path)
    logger.info(f"Dataset: {df.shape[0]:,} rows, {df.shape[1]} columns")

    # ── Season-based train/test split ─────────────────────────────────────────
    # Train on 2022-2023, test on 2024
    # This is more realistic than random split — avoids data leakage
    train_df = df[df["Season"].isin([2022, 2023])]
    test_df = df[df["Season"] == 2024]

    logger.info(
        f"Train: {len(train_df):,} rows (2022-2023) | "
        f"Test: {len(test_df):,} rows (2024)"
    )

    X_train, y_train, encoders = prepare_features(train_df)
    X_test, y_test, _ = prepare_features(test_df)

    # Apply same encoders to test set
    test_df_copy = test_df.copy()

    for col, le in encoders.items():
        if col in test_df_copy.columns:
            test_df_copy[col] = (
                test_df_copy[col]
                .astype(str)
                .apply(lambda x, le=le: x if x in le.classes_ else le.classes_[0])
            )
            test_df_copy[col] = le.transform(test_df_copy[col])

    feature_cols = [
        c
        for c in NUMERICAL_FEATURES + CATEGORICAL_FEATURES
        if c in test_df_copy.columns
    ]
    X_test = test_df_copy[feature_cols].fillna(0).values

    # ── Class weight via sample weights ───────────────────────────────────────
    # Pit stop laps are ~28x rarer — weight them 28x more
    pit_weight = len(y_train) / (2 * y_train.sum())
    no_pit_weight = len(y_train) / (2 * (len(y_train) - y_train.sum()))
    sample_weights = np.where(y_train == 1, pit_weight, no_pit_weight)

    # ── Train model ───────────────────────────────────────────────────────────
    logger.info("Training GradientBoostingClassifier...")

    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=random_state,
        verbose=0,
    )

    model.fit(X_train, y_train, sample_weight=sample_weights)

    # ── Evaluate ───────────────────────────────────────────────────────────────
    # y_pred = model.predict(X_test)
    y_pred_prob = model.predict_proba(X_test)[:, 1]

    # Lower threshold to 0.3 to catch more pit stops
    y_pred_tuned = (y_pred_prob >= 0.3).astype(int)

    f1 = f1_score(y_test, y_pred_tuned)
    precision = precision_score(y_test, y_pred_tuned)
    recall = recall_score(y_test, y_pred_tuned)
    roc_auc = roc_auc_score(y_test, y_pred_prob)

    logger.success(
        f"Model trained:\n"
        f"  F1 Score:  {f1:.4f}\n"
        f"  Precision: {precision:.4f}\n"
        f"  Recall:    {recall:.4f}\n"
        f"  ROC-AUC:   {roc_auc:.4f}"
    )

    print("\n=== Classification Report ===")
    print(
        classification_report(y_test, y_pred_tuned, target_names=["No Pit", "Pit Stop"])
    )

    # ── Feature Importance ─────────────────────────────────────────────────────
    feature_cols = [
        c
        for c in NUMERICAL_FEATURES + CATEGORICAL_FEATURES
        if c in test_df_copy.columns
    ]
    importance_df = pd.DataFrame(
        {
            "Feature": feature_cols,
            "Importance": model.feature_importances_,
        }
    ).sort_values("Importance", ascending=False)

    print("\n=== Feature Importance ===")
    print(importance_df.to_string(index=False))

    # ── Save model ─────────────────────────────────────────────────────────────
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = _MODEL_DIR / "pit_predictor.pkl"
    encoder_path = _MODEL_DIR / "pit_predictor_encoders.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    with open(encoder_path, "wb") as f:
        pickle.dump(encoders, f)

    logger.success(f"Model saved: {model_path}")

    return {
        "model": model,
        "encoders": encoders,
        "f1": f1,
        "precision": precision,
        "recall": recall,
        "roc_auc": roc_auc,
        "importance": importance_df,
        "threshold": 0.3,
    }


# ── Inference ──────────────────────────────────────────────────────────────────


def load_pit_predictor() -> tuple:
    """
    Load trained pit stop predictor from disk.

    Returns:
        tuple: (model, encoders)
    """
    model_path = _MODEL_DIR / "pit_predictor.pkl"
    encoder_path = _MODEL_DIR / "pit_predictor_encoders.pkl"

    if not model_path.exists():
        raise FileNotFoundError(
            "Pit predictor not trained yet. Run train_pit_predictor() first."
        )

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(encoder_path, "rb") as f:
        encoders = pickle.load(f)

    logger.info("Pit predictor loaded from disk")
    return model, encoders


def predict_pit_probability(
    lap_features: dict,
    threshold: float = 0.3,
) -> dict:
    """
    Predict pit stop probability for a single lap.

    Args:
        lap_features: Dict of feature values for current lap
        threshold: Probability threshold for pit recommendation

    Returns:
        dict: Probability and recommendation

    Example:
        >>> prob = predict_pit_probability({
        ...     'TyreLife': 25, 'Compound': 'HARD',
        ...     'Position': 3, 'GapAhead': 8.5,
        ...     'LapsRemaining': 20, 'DegRate': 0.065,
        ... })
    """
    model, encoders = load_pit_predictor()

    # Build feature row
    row = {}
    for col in NUMERICAL_FEATURES:
        row[col] = lap_features.get(col, 0)

    for col in CATEGORICAL_FEATURES:
        val = str(lap_features.get(col, "UNKNOWN"))
        le = encoders.get(col)
        if le and val in le.classes_:
            row[col] = le.transform([val])[0]
        else:
            row[col] = 0

    feature_cols = [c for c in NUMERICAL_FEATURES + CATEGORICAL_FEATURES if c in row]
    X = np.array([[row[c] for c in feature_cols]])

    prob = model.predict_proba(X)[0][1]
    recommend = prob >= threshold

    return {
        "pit_probability": round(float(prob), 4),
        "recommend_pit": recommend,
        "threshold": threshold,
        "confidence": "HIGH" if prob > 0.6 else "MEDIUM" if prob > 0.3 else "LOW",
    }
