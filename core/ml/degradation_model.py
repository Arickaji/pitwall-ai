"""
PitWall AI — Tyre Degradation ML Model
XGBoost regressor predicting lap time DELTA from stint baseline.
Normalizes out circuit effect to focus purely on tyre degradation.
Replaces linear regression from Phase 3 with non-linear modeling.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MODEL_DIR = _PROJECT_ROOT / "data" / "ml" / "models"
_DATASET_PATH = _PROJECT_ROOT / "data" / "ml" / "training_dataset.parquet"


# ── Feature Configuration ──────────────────────────────────────────────────────

DEGRADATION_FEATURES = [
    "TyreLife",
    "Stint",
    "LapNumber",
    "LapsRemaining",
    "Position",
    "DegRate",
    "SpeedFL",
]

CATEGORICAL_FEATURES = [
    "Compound",
]

TARGET = "LapTimeDelta"


# ── Data Preparation ───────────────────────────────────────────────────────────


def prepare_degradation_features(
    df: pd.DataFrame,
    encoders: dict = None,
    fit_encoders: bool = True,
) -> tuple:
    """
    Prepare features for degradation model.

    Args:
        df: DataFrame with lap data
        encoders: Pre-fitted encoders for inference
        fit_encoders: Whether to fit new encoders

    Returns:
        tuple: (X, y, encoders)
    """
    df = df.copy()

    for col in DEGRADATION_FEATURES:
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
                valid_classes = set(le.classes_)
                default_class = le.classes_[0]

                df[col] = [
                    x if x in valid_classes else default_class
                    for x in df[col].astype(str)
                ]

                df[col] = le.transform(df[col])

    feature_cols = [
        c for c in DEGRADATION_FEATURES + CATEGORICAL_FEATURES if c in df.columns
    ]

    X = df[feature_cols].values
    y = df[TARGET].values if TARGET in df.columns else None

    return X, y, encoders


# ── Model Training ─────────────────────────────────────────────────────────────


def train_degradation_model(
    dataset_path: Path = _DATASET_PATH,
) -> dict:
    """
    Train XGBoost degradation model predicting lap time delta.

    Key design decision: predict LapTimeDelta (lap time above
    stint minimum) instead of absolute lap time. This removes
    the circuit effect — Monza vs Monaco baseline differences
    are irrelevant to tyre degradation modeling.

    Season split: train 2022-2023, test 2024.

    Args:
        dataset_path: Path to training Parquet

    Returns:
        dict: Results with model, metrics, feature importance
    """
    logger.info("Loading dataset for degradation model...")
    df = pd.read_parquet(dataset_path)

    # Filter to clean accurate laps
    df = df[df["IsAccurate"] & df["LapTimeSeconds"].between(60, 200)].copy()

    logger.info(f"Clean laps: {len(df):,}")

    # ── Target normalization ───────────────────────────────────────────────────
    # Predict delta from stint minimum pace
    # This removes circuit effect — model learns degradation not circuit speed
    df["StintBasePace"] = df.groupby(["Season", "Circuit", "Driver", "Stint"])[
        "LapTimeSeconds"
    ].transform("min")

    df["LapTimeDelta"] = df["LapTimeSeconds"] - df["StintBasePace"]

    # Remove negative deltas (fresh tyre outliers)
    df = df[df["LapTimeDelta"] >= 0].copy()

    logger.info(
        f"LapTimeDelta range: "
        f"{df['LapTimeDelta'].min():.2f}s – "
        f"{df['LapTimeDelta'].max():.2f}s | "
        f"Mean: {df['LapTimeDelta'].mean():.2f}s"
    )

    # Season split
    train_df = df[df["Season"].isin([2022, 2023])]
    test_df = df[df["Season"] == 2024]

    logger.info(f"Train: {len(train_df):,} | Test: {len(test_df):,}")

    X_train, y_train, encoders = prepare_degradation_features(
        train_df, fit_encoders=True
    )
    X_test, y_test, _ = prepare_degradation_features(
        test_df, encoders=encoders, fit_encoders=False
    )

    # ── Baseline ───────────────────────────────────────────────────────────────
    baseline_pred = np.full_like(y_test, y_train.mean())
    baseline_rmse = np.sqrt(mean_squared_error(y_test, baseline_pred))

    logger.info(f"Baseline RMSE: {baseline_rmse:.4f}s")

    # ── XGBoost ────────────────────────────────────────────────────────────────
    logger.info("Training XGBoost regressor...")

    model = XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=10,
        random_state=42,
        verbosity=0,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # ── Evaluate ───────────────────────────────────────────────────────────────
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    logger.success(
        f"XGBoost Degradation Model:\n"
        f"  MAE:  {mae:.4f}s\n"
        f"  RMSE: {rmse:.4f}s\n"
        f"  R²:   {r2:.4f}\n"
        f"  Baseline RMSE: {baseline_rmse:.4f}s\n"
        f"  Improvement: {baseline_rmse - rmse:.4f}s"
    )

    # ── Feature importance ─────────────────────────────────────────────────────
    feature_cols = [
        c for c in DEGRADATION_FEATURES + CATEGORICAL_FEATURES if c in train_df.columns
    ][: X_train.shape[1]]

    importance_df = pd.DataFrame(
        {
            "Feature": feature_cols,
            "Importance": model.feature_importances_,
        }
    ).sort_values("Importance", ascending=False)

    print("\n=== Feature Importance ===")
    print(importance_df.to_string(index=False))

    # ── Per compound RMSE ──────────────────────────────────────────────────────
    print("\n=== RMSE by Compound ===")
    test_df_eval = test_df.copy().reset_index(drop=True)
    test_df_eval = test_df_eval[test_df_eval["LapTimeDelta"] >= 0]
    test_df_eval["Predicted"] = y_pred[: len(test_df_eval)]

    for compound in ["SOFT", "MEDIUM", "HARD"]:
        mask = test_df_eval["Compound"] == compound
        if mask.sum() > 0:
            c_rmse = np.sqrt(
                mean_squared_error(
                    test_df_eval[mask]["LapTimeDelta"],
                    test_df_eval[mask]["Predicted"],
                )
            )
            print(f"  {compound}: RMSE={c_rmse:.4f}s ({mask.sum()} laps)")

    # ── Save ───────────────────────────────────────────────────────────────────
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(_MODEL_DIR / "degradation_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open(_MODEL_DIR / "degradation_encoders.pkl", "wb") as f:
        pickle.dump(encoders, f)

    logger.success(f"Model saved: {_MODEL_DIR / 'degradation_model.pkl'}")

    return {
        "model": model,
        "encoders": encoders,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "baseline_rmse": baseline_rmse,
        "improvement": baseline_rmse - rmse,
        "importance": importance_df,
    }


# ── Inference ──────────────────────────────────────────────────────────────────


def predict_lap_delta(
    tyre_life: int,
    compound: str,
    stint: int = 1,
    lap_number: int = 20,
    laps_remaining: int = 30,
    deg_rate: float = 0.05,
    position: int = 5,
    speed_fl: float = 210.0,
) -> dict:
    """
    Predict lap time delta above stint minimum for given conditions.
    """
    model_path = _MODEL_DIR / "degradation_model.pkl"
    encoder_path = _MODEL_DIR / "degradation_encoders.pkl"

    if not model_path.exists():
        raise FileNotFoundError(
            "Model not trained. Run train_degradation_model() first."
        )

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(encoder_path, "rb") as f:
        encoders = pickle.load(f)

    # Encode compound manually
    compound_encoded = 0
    le = encoders.get("Compound")
    if le and compound in le.classes_:
        compound_encoded = int(le.transform([compound])[0])

    # Build feature array in exact training order
    X = np.array(
        [
            [
                tyre_life,  # TyreLife
                stint,  # Stint
                lap_number,  # LapNumber
                laps_remaining,  # LapsRemaining
                position,  # Position
                deg_rate,  # DegRate
                speed_fl,  # SpeedFL
                compound_encoded,  # Compound (encoded)
            ]
        ],
        dtype=float,
    )

    delta = float(model.predict(X)[0])
    delta = max(0.0, delta)

    if delta < 0.5:
        interpretation = "Tyres still fresh — minimal degradation"
    elif delta < 1.5:
        interpretation = "Moderate degradation — monitor closely"
    elif delta < 3.0:
        interpretation = "Significant degradation — consider pitting soon"
    else:
        interpretation = "Critical degradation — pit recommended"

    return {
        "predicted_delta": round(delta, 3),
        "tyre_life": tyre_life,
        "compound": compound,
        "interpretation": interpretation,
    }
