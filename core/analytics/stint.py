"""
PitWall AI — Stint Analysis Engine
Analyzes race stints and predicts optimal pit windows.
Builds on tire degradation model from core/analytics/degradation.py
"""

from dataclasses import dataclass

import pandas as pd
from loguru import logger

from core.analytics.degradation import analyze_race_degradation
from core.analytics.pace import get_clean_race_laps

# ── Constants ──────────────────────────────────────────────────────────────────

PIT_STOP_TIME_LOSS = 22.0  # seconds lost during a pit stop (Bahrain avg)


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class PitWindow:
    """
    Predicted optimal pit window for a driver.

    earliest_lap: First lap where pitting makes strategic sense
    latest_lap:   Last lap before pace loss exceeds pit stop cost
    optimal_lap:  Best lap to pit based on degradation curve
    """

    driver: str
    current_stint: int
    compound: str
    earliest_lap: int
    optimal_lap: int
    latest_lap: int
    pace_loss: float  # seconds lost by staying out past optimal


# ── Core Functions ─────────────────────────────────────────────────────────────


def analyze_stints(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Full stint breakdown for all drivers in a race.

    For each stint shows: compound, length, avg pace,
    degradation rate, and whether a cliff was detected.

    Args:
        laps: Full race lap DataFrame

    Returns:
        pd.DataFrame: Stint summary per driver
    """
    logger.info("Running full stint analysis...")

    clean = get_clean_race_laps(laps)
    degradation = analyze_race_degradation(laps)

    # Build stint summary
    stint_summary = (
        clean.groupby(["Driver", "Stint", "Compound"])
        .agg(
            StintLaps=("LapNumber", "count"),
            AvgPace=("LapTimeSeconds", "mean"),
            BestPace=("LapTimeSeconds", "min"),
            StartLap=("LapNumber", "min"),
            EndLap=("LapNumber", "max"),
        )
        .round(3)
        .reset_index()
    )

    # Merge degradation rates in
    stint_summary = stint_summary.merge(
        degradation[["Driver", "Stint", "DegradationRate", "RSquared", "CliffLap"]],
        on=["Driver", "Stint"],
        how="left",
    )

    stint_summary = stint_summary.sort_values(["Driver", "Stint"]).reset_index(
        drop=True
    )

    logger.success(
        f"Stint analysis complete: {len(stint_summary)} stints "
        f"across {stint_summary['Driver'].nunique()} drivers"
    )

    return stint_summary


def predict_pit_window(
    laps: pd.DataFrame,
    driver: str,
    fresh_compound_pace: float,
    laps_remaining: int,
    pit_stop_loss: float = PIT_STOP_TIME_LOSS,
) -> PitWindow | None:
    """
    Predict optimal pit window for a driver based on current degradation.

    Logic:
    - Calculate how much pace is being lost per lap (degradation rate)
    - Calculate when cumulative pace loss exceeds pit stop time cost
    - That crossover point is the optimal pit lap

    Args:
        laps: Full race lap DataFrame
        driver: Driver code e.g. 'VER'
        fresh_compound_pace: Expected pace on fresh tyres (seconds)
        laps_remaining: Laps left in the race
        pit_stop_loss: Time lost during pit stop (default 22s)

    Returns:
        PitWindow dataclass or None if insufficient data
    """
    clean = get_clean_race_laps(laps)
    driver_laps = clean[clean["Driver"] == driver.upper()]

    if driver_laps.empty:
        logger.warning(f"No clean laps found for driver: {driver}")
        return None

    # Get current stint info
    current_stint = int(driver_laps["Stint"].max())
    current_stint_laps = driver_laps[driver_laps["Stint"] == current_stint]
    compound = current_stint_laps["Compound"].iloc[0]

    # Get degradation rate for current stint
    degradation = analyze_race_degradation(laps)
    driver_deg = degradation[
        (degradation["Driver"] == driver.upper())
        & (degradation["Stint"] == current_stint)
    ]

    if driver_deg.empty:
        logger.warning(f"No degradation data for {driver} stint {current_stint}")
        return None

    deg_rate = float(driver_deg["DegradationRate"].iloc[0])
    current_pace = float(current_stint_laps["LapTimeSeconds"].iloc[-1])

    # Calculate pace loss per lap vs fresh compound
    pace_advantage_fresh = current_pace - fresh_compound_pace

    # Find optimal pit lap
    # Pit when: cumulative_pace_loss > pit_stop_loss
    # n_laps × deg_rate > pit_stop_loss - pace_advantage_fresh × n_laps
    # This simplifies to finding crossover point

    optimal_lap = None
    cumulative_loss = 0.0

    for n in range(1, laps_remaining + 1):
        cumulative_loss += deg_rate
        net_benefit = (pace_advantage_fresh * n) - pit_stop_loss

        if net_benefit > 0 and optimal_lap is None:
            optimal_lap = n

    if optimal_lap is None:
        optimal_lap = laps_remaining  # Pit as late as possible

    current_lap = int(driver_laps["LapNumber"].max())

    return PitWindow(
        driver=driver.upper(),
        current_stint=current_stint,
        compound=compound,
        earliest_lap=current_lap + max(1, optimal_lap - 3),
        optimal_lap=current_lap + optimal_lap,
        latest_lap=current_lap + min(laps_remaining, optimal_lap + 5),
        pace_loss=round(cumulative_loss, 3),
    )


def compare_stint_strategies(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Compare stint strategies across all drivers.

    Shows number of stints, compounds used, and total laps per stint.
    Reveals strategic differences between teams.

    Args:
        laps: Full race lap DataFrame

    Returns:
        pd.DataFrame: Strategy comparison per driver
    """
    clean = get_clean_race_laps(laps)

    strategies = []

    for driver, driver_laps in clean.groupby("Driver"):
        stints = driver_laps.groupby("Stint")["Compound"].first()
        strategy_str = " → ".join(stints.values)
        total_stints = len(stints)

        strategies.append(
            {
                "Driver": driver,
                "TotalStints": total_stints,
                "Strategy": strategy_str,
                "TotalLaps": len(driver_laps),
            }
        )

    df = pd.DataFrame(strategies).sort_values("Driver").reset_index(drop=True)

    logger.success(f"Strategy comparison: {len(df)} drivers")
    return df
