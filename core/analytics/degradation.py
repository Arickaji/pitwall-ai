"""
PitWall AI — Tire Degradation Model
Models how lap time increases as tires wear across a stint.
Foundation of all pit stop strategy decisions.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from loguru import logger

# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class StintDegradation:
    """
    Degradation model for a single stint.

    degradation_rate: seconds lost per lap of tyre life
    base_pace:        theoretical lap time on fresh tyres (intercept)
    r_squared:        model fit quality 0-1 (1 = perfect linear fit)
    cliff_lap:        tyre life lap where degradation accelerates sharply
    """

    driver: str
    compound: str
    stint: int
    laps: int
    degradation_rate: float  # seconds per lap
    base_pace: float  # seconds (fresh tyre pace)
    r_squared: float  # model fit quality
    cliff_lap: int | None


@dataclass
class CompoundDegradation:
    """
    Average degradation model across all drivers for a compound.
    Used for strategic planning — what does a SOFT tyre cost per lap?
    """

    compound: str
    avg_degradation: float
    min_degradation: float
    max_degradation: float
    sample_stints: int


# ── Core Functions ─────────────────────────────────────────────────────────────


def calculate_stint_degradation(
    stint_laps: pd.DataFrame,
    min_laps: int = 5,
) -> StintDegradation | None:
    """
    Calculate degradation rate for a single stint using linear regression.

    The slope of the regression line (TyreLife → LapTime) gives us
    degradation rate in seconds per lap. A slope of 0.08 means the
    tyre costs 0.08s extra per lap as it wears.

    Args:
        stint_laps: DataFrame of clean laps for one driver one stint
        min_laps:   Minimum laps needed for reliable regression

    Returns:
        StintDegradation dataclass or None if insufficient data
    """
    # Need minimum laps for regression to be meaningful
    if len(stint_laps) < min_laps:
        return None

    # Extract arrays for regression
    tyre_life = stint_laps["TyreLife"].values
    lap_times = stint_laps["LapTimeSeconds"].values

    # Remove any remaining NaN values
    mask = ~(np.isnan(tyre_life) | np.isnan(lap_times))
    tyre_life = tyre_life[mask]
    lap_times = lap_times[mask]

    if len(tyre_life) < min_laps:
        return None

    # Linear regression using numpy polyfit
    # degree=1 fits a straight line: laptime = slope * tyrelife + intercept
    # slope = degradation rate (seconds per lap)
    # intercept = base pace (theoretical fresh tyre time)
    coeffs = np.polyfit(tyre_life, lap_times, deg=1)
    slope = coeffs[0]  # degradation rate
    intercept = coeffs[1]  # base pace

    # Calculate R² — how well the line fits the data
    # R² = 1.0 means perfect fit, 0.0 means no relationship
    predicted = np.polyval(coeffs, tyre_life)
    ss_res = np.sum((lap_times - predicted) ** 2)
    ss_tot = np.sum((lap_times - np.mean(lap_times)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Detect cliff point — lap where degradation suddenly accelerates
    cliff_lap = _detect_cliff(stint_laps)

    driver = stint_laps["Driver"].iloc[0]
    compound = stint_laps["Compound"].iloc[0]
    stint = int(stint_laps["Stint"].iloc[0])

    return StintDegradation(
        driver=driver,
        compound=compound,
        stint=stint,
        laps=len(tyre_life),
        degradation_rate=round(float(slope), 4),
        base_pace=round(float(intercept), 3),
        r_squared=round(float(r_squared), 4),
        cliff_lap=cliff_lap,
    )


def _detect_cliff(stint_laps: pd.DataFrame, threshold: float = 0.3) -> int | None:
    """
    Detect the lap where degradation suddenly accelerates — the cliff point.

    Method: calculate lap-over-lap delta. If delta suddenly jumps above
    threshold (0.3s default), that's the cliff.

    Args:
        stint_laps: Clean laps for one stint
        threshold:  Seconds jump that signals a cliff

    Returns:
        TyreLife lap number of cliff or None if no cliff detected
    """
    if len(stint_laps) < 6:
        return None

    laps_sorted = stint_laps.sort_values("TyreLife")
    deltas = laps_sorted["LapTimeSeconds"].diff()

    cliff_mask = deltas > threshold
    if cliff_mask.any():
        cliff_idx = deltas[cliff_mask].index[0]
        return int(laps_sorted.loc[cliff_idx, "TyreLife"])

    return None


def analyze_race_degradation(
    laps: pd.DataFrame,
) -> pd.DataFrame:
    """
    Analyze tire degradation for all drivers and stints in a race.

    Args:
        laps: Full race lap DataFrame (clean laps recommended)

    Returns:
        pd.DataFrame: One row per driver per stint with degradation metrics
    """
    logger.info(f"Analyzing degradation for {laps['Driver'].nunique()} drivers")

    # Convert LapTime to seconds if needed
    if "LapTimeSeconds" not in laps.columns:
        laps = laps.copy()
        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

    # Filter to accurate laps only
    clean = laps[
        laps["IsAccurate"]
        & (laps["LapTimeSeconds"].notna())
        & (laps["LapTimeSeconds"] > 60)
    ].copy()

    results = []

    # Group by driver and stint
    for (_, _), stint_laps in clean.groupby(["Driver", "Stint"]):
        degradation = calculate_stint_degradation(stint_laps)

        if degradation is not None:
            results.append(
                {
                    "Driver": degradation.driver,
                    "Compound": degradation.compound,
                    "Stint": degradation.stint,
                    "Laps": degradation.laps,
                    "DegradationRate": degradation.degradation_rate,
                    "BasePace": degradation.base_pace,
                    "RSquared": degradation.r_squared,
                    "CliffLap": degradation.cliff_lap,
                }
            )

    df = pd.DataFrame(results).sort_values(["Driver", "Stint"]).reset_index(drop=True)

    logger.success(
        f"Degradation analyzed: {len(df)} stints across {df['Driver'].nunique()} drivers"
    )
    return df


def compound_degradation_summary(
    degradation_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Summarize average degradation rate per compound.

    This answers: "On average, how many seconds per lap does each
    compound cost as it wears?" — key input for strategy planning.

    Args:
        degradation_df: Output from analyze_race_degradation()

    Returns:
        pd.DataFrame: Compound-level degradation summary
    """
    summary = (
        degradation_df.groupby("Compound")["DegradationRate"]
        .agg(
            AvgDegradation="mean",
            MinDegradation="min",
            MaxDegradation="max",
            SampleStints="count",
        )
        .round(4)
        .reset_index()
        .sort_values("AvgDegradation")
    )

    return summary
