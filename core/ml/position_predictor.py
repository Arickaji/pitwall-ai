"""
PitWall AI — Race Position Prediction Model
Predicts finishing position probability distribution for each driver
given current race state at any lap.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MODEL_DIR = _PROJECT_ROOT / "data" / "ml" / "models"
_DATASET_PATH = _PROJECT_ROOT / "data" / "ml" / "training_dataset.parquet"


# ── Feature Configuration ──────────────────────────────────────────────────────

POSITION_FEATURES = [
    "Position",
    "LapsRemaining",
    "TyreLife",
    "Stint",
    "GapAhead",
    "GapBehind",
    "LapTimeSeconds",
    "LapTimeTrend",
    "DegRate",
]

CATEGORICAL_FEATURES = [
    "Compound",
]

TARGET = "FinalPosition"


# ── Data Preparation ───────────────────────────────────────────────────────────


def _build_final_positions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add FinalPosition column — position at the last lap per driver per race.

    This is our prediction target — where did the driver actually finish?

    Args:
        df: Full feature DataFrame

    Returns:
        pd.DataFrame: DataFrame with FinalPosition column added
    """
    # Get final position per driver per race
    final_pos = (
        df.groupby(["Season", "Circuit", "Driver"])
        .apply(
            lambda x: x.loc[x["LapNumber"].idxmax(), "Position"], include_groups=False
        )
        .reset_index()
        .rename(columns={0: "FinalPosition"})
    )

    df = df.merge(final_pos, on=["Season", "Circuit", "Driver"], how="left")

    # Convert to integer positions 1-20
    df["FinalPosition"] = df["FinalPosition"].fillna(20).astype(int).clip(1, 20)

    return df


def prepare_position_features(
    df: pd.DataFrame,
    encoders: dict = None,
    fit_encoders: bool = True,
) -> tuple:
    """
    Prepare features for position prediction.

    Args:
        df: DataFrame with lap data
        encoders: Pre-fitted encoders
        fit_encoders: Whether to fit new encoders

    Returns:
        tuple: (X, y, encoders)
    """
    df = df.copy()

    for col in POSITION_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    if encoders is None:
        encoders = {}

    for col in CATEGORICAL_FEATURES:
        if col not in df.columns:
            continue
        if fit_encoders:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
        else:
            le = encoders.get(col)
            if le:
                df[col] = (
                    df[col]
                    .astype(str)
                    .apply(
                        lambda x, _le=le: x if x in _le.classes_ else _le.classes_[0]
                    )
                )
                df[col] = le.transform(df[col])

    feature_cols = [
        c for c in POSITION_FEATURES + CATEGORICAL_FEATURES if c in df.columns
    ]

    X = df[feature_cols].values
    y = (df[TARGET].values - 1) if TARGET in df.columns else None

    return X, y, encoders


# ── Model Training ─────────────────────────────────────────────────────────────


def train_position_predictor(
    dataset_path: Path = _DATASET_PATH,
) -> dict:
    """
    Train race position prediction model.

    Predicts finishing position (1-20) given current race state.
    Uses XGBoost multiclass classifier.

    Evaluation metric: Top-3 accuracy
    (Did the model predict the correct position within ±3 places?)

    Season split: train 2022-2023, test on 2024.

    Args:
        dataset_path: Path to training Parquet

    Returns:
        dict: Results with model, metrics, feature importance
    """
    logger.info("Loading dataset for position predictor...")
    df = pd.read_parquet(dataset_path)

    # Add final position target
    df = _build_final_positions(df)

    # Filter to accurate laps with valid positions
    df = df[
        df["IsAccurate"] & df["Position"].notna() & df["FinalPosition"].notna()
    ].copy()

    logger.info(f"Valid laps: {len(df):,}")

    # Season split
    train_df = df[df["Season"].isin([2022, 2023])]
    test_df = df[df["Season"] == 2024]

    logger.info(f"Train: {len(train_df):,} | Test: {len(test_df):,}")

    X_train, y_train, encoders = prepare_position_features(train_df, fit_encoders=True)
    X_test, y_test, _ = prepare_position_features(
        test_df, encoders=encoders, fit_encoders=False
    )

    # ── Train XGBoost multiclass ───────────────────────────────────────────────
    logger.info("Training XGBoost multiclass classifier...")

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        num_class=20,
        objective="multi:softprob",
        random_state=42,
        verbosity=0,
        use_label_encoder=False,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # ── Evaluate ───────────────────────────────────────────────────────────────
    y_pred_prob = model.predict_proba(X_test)
    y_pred = y_pred_prob.argmax(axis=1)

    # Convert back to 1-based positions
    y_pred_pos = y_pred + 1
    y_test_pos = y_test + 1

    mae = mean_absolute_error(y_test_pos, y_pred_pos)

    # Top-3 accuracy: predicted within ±3 positions
    top3_acc = np.mean(np.abs(y_pred_pos - y_test_pos) <= 3)

    # Exact accuracy
    exact_acc = np.mean(y_pred_pos == y_test_pos)

    logger.success(
        f"Position Predictor:\n"
        f"  MAE:          {mae:.4f} positions\n"
        f"  Exact Acc:    {exact_acc:.4f}\n"
        f"  Top-3 Acc:    {top3_acc:.4f}\n"
    )

    # ── Feature importance ─────────────────────────────────────────────────────
    feature_cols = [
        c for c in POSITION_FEATURES + CATEGORICAL_FEATURES if c in train_df.columns
    ][: X_train.shape[1]]

    importance_df = pd.DataFrame(
        {
            "Feature": feature_cols,
            "Importance": model.feature_importances_,
        }
    ).sort_values("Importance", ascending=False)

    print("\n=== Feature Importance ===")
    print(importance_df.to_string(index=False))

    # ── Position error distribution ────────────────────────────────────────────
    errors = np.abs(y_pred_pos - y_test_pos)
    print("\n=== Prediction Error Distribution ===")
    print(f"  Exact (±0):  {(errors == 0).mean():.1%}")
    print(f"  Within ±1:   {(errors <= 1).mean():.1%}")
    print(f"  Within ±2:   {(errors <= 2).mean():.1%}")
    print(f"  Within ±3:   {(errors <= 3).mean():.1%}")
    print(f"  Within ±5:   {(errors <= 5).mean():.1%}")

    # ── Save ───────────────────────────────────────────────────────────────────
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(_MODEL_DIR / "position_predictor.pkl", "wb") as f:
        pickle.dump(model, f)
    with open(_MODEL_DIR / "position_encoders.pkl", "wb") as f:
        pickle.dump(encoders, f)

    logger.success("Position predictor saved")

    return {
        "model": model,
        "encoders": encoders,
        "mae": mae,
        "exact_acc": exact_acc,
        "top3_acc": top3_acc,
        "importance": importance_df,
    }


# ── Inference ──────────────────────────────────────────────────────────────────


def predict_position_distribution(
    current_position: int,
    laps_remaining: int,
    tyre_life: int,
    compound: str,
    gap_ahead: float,
    gap_behind: float,
    lap_time: float,
    lap_time_trend: float = 0.0,
    deg_rate: float = 0.05,
    stint: int = 2,
) -> dict:
    """
    Predict finishing position probability distribution.

    Args:
        current_position: Current race position (1-20)
        laps_remaining: Laps left in race
        tyre_life: Current tyre age in laps
        compound: Tyre compound
        gap_ahead: Gap to car ahead in seconds
        gap_behind: Gap to car behind in seconds
        lap_time: Current lap time in seconds
        lap_time_trend: Change in lap time vs previous lap
        deg_rate: Current degradation rate
        stint: Current stint number

    Returns:
        dict: Position probabilities and most likely finishing position
    """
    model_path = _MODEL_DIR / "position_predictor.pkl"
    encoder_path = _MODEL_DIR / "position_encoders.pkl"

    if not model_path.exists():
        raise FileNotFoundError(
            "Model not trained. Run train_position_predictor() first."
        )

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(encoder_path, "rb") as f:
        encoders = pickle.load(f)

    # Encode compound
    compound_encoded = 0
    le = encoders.get("Compound")
    if le and compound in le.classes_:
        compound_encoded = int(le.transform([compound])[0])

    # Build feature array in training order
    X = np.array(
        [
            [
                current_position,
                laps_remaining,
                tyre_life,
                stint,
                gap_ahead,
                gap_behind,
                lap_time,
                lap_time_trend,
                deg_rate,
                compound_encoded,
            ]
        ],
        dtype=float,
    )

    probs = model.predict_proba(X)[0]

    # Build position probability dict (1-based)
    position_probs = {i + 1: round(float(probs[i]), 4) for i in range(len(probs))}

    # Top 5 most likely positions
    top5 = sorted(position_probs.items(), key=lambda x: x[1], reverse=True)[:5]

    most_likely = top5[0][0]

    return {
        "most_likely_position": most_likely,
        "top5_positions": top5,
        "all_probabilities": position_probs,
        "current_position": current_position,
        "laps_remaining": laps_remaining,
    }
