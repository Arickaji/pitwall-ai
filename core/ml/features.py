"""
PitWall AI — ML Feature Engineering
Builds feature vectors for ML model training from raw lap data.
"""

import numpy as np
import pandas as pd
from loguru import logger

from core.analytics.degradation import analyze_race_degradation

# ── Feature Engineering ────────────────────────────────────────────────────────


def engineer_features(
    laps: pd.DataFrame,
    total_laps: int,
    circuit: str = "Unknown",
    season: int = 2024,
) -> pd.DataFrame:
    """
    Engineer ML features from raw lap data.

    Transforms raw FastF1 lap data into feature vectors
    suitable for ML model training.

    Features engineered:
    - LapTimeTrend: pace change vs previous lap
    - GapAhead/Behind: time gaps to adjacent cars
    - LapsRemaining: laps left in race
    - DegRate: current stint degradation rate
    - PittedNextLap: target label for pit prediction

    Args:
        laps: Raw lap DataFrame from FastF1
        total_laps: Total race laps
        circuit: Circuit name for feature
        season: Championship year

    Returns:
        pd.DataFrame: Feature vectors for ML training
    """
    logger.info(f"Engineering features: {circuit} {season} " f"({len(laps)} laps)")

    # Convert lap time to seconds
    if "LapTimeSeconds" not in laps.columns:
        laps = laps.copy()
        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

    # Get degradation rates
    degradation = analyze_race_degradation(laps)

    # Build features per driver
    all_features = []

    for driver, driver_laps in laps.groupby("Driver"):
        driver_laps = driver_laps.sort_values("LapNumber").copy()

        # ── Lap time trend ─────────────────────────────────────────────────────
        driver_laps["LapTimeTrend"] = driver_laps["LapTimeSeconds"].diff()

        # ── Laps remaining ─────────────────────────────────────────────────────
        driver_laps["LapsRemaining"] = total_laps - driver_laps["LapNumber"]

        # ── Degradation rate from Phase 3 model ────────────────────────────────
        driver_deg = degradation[degradation["Driver"] == driver]

        def get_deg_rate(row, _driver_deg=driver_deg):
            stint_deg = _driver_deg[_driver_deg["Stint"] == row["Stint"]]
            if stint_deg.empty:
                return 0.05
            return (
                float(stint_deg["DegradationRate"].iloc[0])
                if "DegradationRate" in stint_deg.columns
                else float(stint_deg["DegRate"].iloc[0])
            )

        driver_laps["DegRate"] = driver_laps.apply(get_deg_rate, axis=1)

        # ── Pitted next lap label ──────────────────────────────────────────────────
        # PitInTime is not null on the pit lap itself (always IsAccurate=False)
        # We label the LAP BEFORE the pit as PittedNextLap=1
        # So the model learns: "given this lap's features, will driver pit next?"
        driver_laps["PittedThisLap"] = driver_laps["PitInTime"].notna().astype(int)
        driver_laps["PittedNextLap"] = (
            driver_laps["PittedThisLap"].shift(-1).fillna(0).astype(int)
        )

        # Last lap has no next lap — drop it
        driver_laps = driver_laps.iloc[:-1]

        # ── Add metadata ───────────────────────────────────────────────────────
        driver_laps = driver_laps.copy()
        driver_laps["Circuit"] = circuit
        driver_laps["Season"] = season

        all_features.append(driver_laps)

    features = pd.concat(all_features, ignore_index=True)

    # ── Gap to ahead and behind ────────────────────────────────────────────────
    features = _calculate_gaps(features)

    # ── Select final feature columns ───────────────────────────────────────────
    feature_cols = [
        "Driver",
        "Season",
        "Circuit",
        "LapNumber",
        "LapTimeSeconds",
        "LapTimeTrend",
        "TyreLife",
        "Compound",
        "Stint",
        "Position",
        "GapAhead",
        "GapBehind",
        "LapsRemaining",
        "DegRate",
        "SpeedFL",
        "IsAccurate",
        "Team",
        "PittedNextLap",
    ]

    # Keep only columns that exist
    available_cols = [c for c in feature_cols if c in features.columns]
    features = features[available_cols].copy()

    # Filter to accurate laps only
    if "IsAccurate" in features.columns:
        features = features[features["IsAccurate"]]

    features = features.dropna(subset=["LapTimeSeconds", "TyreLife"])
    features = features.reset_index(drop=True)

    logger.success(
        f"Features engineered: {len(features)} rows | "
        f"{features['PittedNextLap'].sum()} pit stops labeled"
    )

    return features


def _calculate_gaps(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate gap to car ahead and behind for each lap.

    Uses cumulative lap time difference between adjacent positions.

    Args:
        laps: Lap DataFrame with Position column

    Returns:
        pd.DataFrame: Laps with GapAhead and GapBehind columns
    """
    laps = laps.copy()
    laps["GapAhead"] = np.nan
    laps["GapBehind"] = np.nan

    for lap_num, lap_group in laps.groupby("LapNumber"):
        lap_group = lap_group.sort_values("Position")

        # Calculate cumulative time per driver up to this lap
        cum_times = {}
        for _, row in lap_group.iterrows():
            driver = row["Driver"]
            driver_laps = laps[
                (laps["Driver"] == driver) & (laps["LapNumber"] <= lap_num)
            ]
            cum_times[driver] = driver_laps["LapTimeSeconds"].sum()

        # Calculate gaps between adjacent cars
        sorted_drivers = lap_group["Driver"].tolist()

        for i, driver in enumerate(sorted_drivers):
            if i > 0:
                ahead_driver = sorted_drivers[i - 1]
                gap_ahead = cum_times[driver] - cum_times[ahead_driver]
                laps.loc[
                    (laps["Driver"] == driver) & (laps["LapNumber"] == lap_num),
                    "GapAhead",
                ] = round(gap_ahead, 3)

            if i < len(sorted_drivers) - 1:
                behind_driver = sorted_drivers[i + 1]
                gap_behind = cum_times[behind_driver] - cum_times[driver]
                laps.loc[
                    (laps["Driver"] == driver) & (laps["LapNumber"] == lap_num),
                    "GapBehind",
                ] = round(gap_behind, 3)

    return laps
