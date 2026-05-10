"""
PitWall AI — Race Trend Analysis
Analyzes gap evolution, safety car periods, and pace trends across a race.
"""

import pandas as pd
from loguru import logger

from core.analytics.pace import get_clean_race_laps

# ── Gap Evolution ──────────────────────────────────────────────────────────────


def calculate_gap_evolution(
    laps: pd.DataFrame,
    driver_ahead: str,
    driver_behind: str,
) -> pd.DataFrame:
    """
    Calculate lap-by-lap gap between two drivers.

    Positive gap = driver_behind is behind driver_ahead
    Shrinking gap = driver_behind is catching
    Growing gap = driver_ahead is pulling away

    Args:
        laps: Full race lap DataFrame
        driver_ahead: Driver code of the car in front e.g. 'VER'
        driver_behind: Driver code of the car behind e.g. 'SAI'

    Returns:
        pd.DataFrame: Lap-by-lap gap evolution
    """
    if "LapTimeSeconds" not in laps.columns:
        laps = laps.copy()
        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

    ahead = laps[laps["Driver"] == driver_ahead.upper()][
        ["LapNumber", "LapTimeSeconds"]
    ].rename(columns={"LapTimeSeconds": "LapTime_Ahead"})

    behind = laps[laps["Driver"] == driver_behind.upper()][
        ["LapNumber", "LapTimeSeconds"]
    ].rename(columns={"LapTimeSeconds": "LapTime_Behind"})

    merged = ahead.merge(behind, on="LapNumber", how="inner")

    # Gap delta per lap — positive means ahead pulling away
    merged["LapDelta"] = (merged["LapTime_Behind"] - merged["LapTime_Ahead"]).round(3)

    # Cumulative gap — total time between drivers
    merged["CumulativeGap"] = merged["LapDelta"].cumsum().round(3)

    merged["DriverAhead"] = driver_ahead.upper()
    merged["DriverBehind"] = driver_behind.upper()

    logger.info(
        f"Gap evolution: {driver_ahead} vs {driver_behind} "
        f"| Final gap: {merged['CumulativeGap'].iloc[-1]:.3f}s"
    )

    return merged.reset_index(drop=True)


# ── Safety Car Detection ───────────────────────────────────────────────────────


def detect_safety_car_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Detect safety car and virtual safety car periods.

    Method: During SC periods, ALL drivers slow significantly
    and lap times cluster tightly together. We detect this by
    looking for laps where:
    - Lap time is significantly above driver's median
    - Multiple drivers show this simultaneously

    FastF1 also provides TrackStatus which directly flags SC laps.

    Args:
        laps: Full race lap DataFrame

    Returns:
        pd.DataFrame: Laps flagged as safety car periods
    """
    if "LapTimeSeconds" not in laps.columns:
        laps = laps.copy()
        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

    # Method 1 — Use FastF1 TrackStatus directly
    # Status 4 = Safety Car, Status 5 = Red Flag, Status 6 = VSC
    if "TrackStatus" in laps.columns:
        sc_laps = laps[
            laps["TrackStatus"].astype(str).str.contains("4|6|7", na=False)
        ].copy()

        if not sc_laps.empty:
            logger.info(
                f"Safety car periods detected: "
                f"{sc_laps['LapNumber'].nunique()} laps affected"
            )
            return (
                sc_laps[["LapNumber", "Driver", "LapTimeSeconds", "TrackStatus"]]
                .drop_duplicates(subset=["LapNumber"])
                .sort_values("LapNumber")
            )

    # Method 2 — Statistical detection fallback
    driver_medians = laps.groupby("Driver")["LapTimeSeconds"].median()
    laps = laps.copy()
    laps["MedianPace"] = laps["Driver"].map(driver_medians)
    laps["PaceRatio"] = laps["LapTimeSeconds"] / laps["MedianPace"]

    # Flag laps where driver is >15% slower than their median
    slow_laps = laps[laps["PaceRatio"] > 1.15]

    # Count how many drivers are slow on each lap
    slow_per_lap = slow_laps.groupby("LapNumber")["Driver"].count()
    sc_lap_numbers = slow_per_lap[slow_per_lap >= 5].index

    sc_laps = (
        laps[laps["LapNumber"].isin(sc_lap_numbers)][
            ["LapNumber", "Driver", "LapTimeSeconds"]
        ]
        .drop_duplicates(subset=["LapNumber"])
        .sort_values("LapNumber")
    )

    logger.info(f"SC detection (statistical): {len(sc_laps)} laps flagged")
    return sc_laps


# ── Pace Evolution ─────────────────────────────────────────────────────────────


def pace_evolution(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Track how the overall field pace evolves across the race.

    Uses rolling median across all drivers per lap to show
    whether the circuit is getting faster (track evolution)
    or slower (degradation dominating).

    Args:
        laps: Full race lap DataFrame

    Returns:
        pd.DataFrame: Field pace per lap with rolling average
    """
    clean = get_clean_race_laps(laps)

    # Median field pace per lap
    field_pace = (
        clean.groupby("LapNumber")["LapTimeSeconds"]
        .agg(
            MedianFieldPace="median",
            FastestLap="min",
            FieldSpread="std",
            DriversOnLap="count",
        )
        .round(3)
        .reset_index()
    )

    # Rolling average to smooth noise
    field_pace["RollingPace"] = (
        field_pace["MedianFieldPace"].rolling(window=5, center=True).mean().round(3)
    )

    # Pace trend — positive means field getting slower
    field_pace["PaceTrend"] = field_pace["MedianFieldPace"].diff().round(3)

    logger.success(
        f"Pace evolution: {len(field_pace)} laps analyzed | "
        f"Track evolution: "
        f"{field_pace['MedianFieldPace'].iloc[0]:.2f}s → "
        f"{field_pace['MedianFieldPace'].iloc[-1]:.2f}s"
    )

    return field_pace


# ── Position Evolution ─────────────────────────────────────────────────────────


def position_evolution(
    laps: pd.DataFrame,
    drivers: list = None,
) -> pd.DataFrame:
    """
    Track position changes across the race for selected drivers.

    Args:
        laps: Full race lap DataFrame
        drivers: List of driver codes to track. None = all drivers.

    Returns:
        pd.DataFrame: Position per lap per driver
    """
    if drivers:
        drivers = [d.upper() for d in drivers]
        laps = laps[laps["Driver"].isin(drivers)]

    positions = (
        laps[["LapNumber", "Driver", "Position"]].dropna(subset=["Position"]).copy()
    )

    positions["Position"] = positions["Position"].astype(int)

    logger.info(f"Position evolution: {positions['Driver'].nunique()} drivers tracked")

    return positions.sort_values(["LapNumber", "Position"]).reset_index(drop=True)
