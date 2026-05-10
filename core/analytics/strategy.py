"""
PitWall AI — Undercut/Overcut Analytics
Models whether pitting early (undercut) or staying out (overcut)
gains or loses position against a specific rival.
"""

from dataclasses import dataclass

import pandas as pd
from loguru import logger

from core.analytics.degradation import analyze_race_degradation
from core.analytics.pace import get_clean_race_laps

# ── Constants ──────────────────────────────────────────────────────────────────

PIT_STOP_LOSS = 22.0  # seconds lost during pit stop
FRESH_TYRE_DELTA = 0.5  # seconds gained immediately on fresh tyres


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class UndercutResult:
    """
    Result of undercut opportunity analysis between two drivers.

    is_viable: True if undercut can work mathematically
    laps_to_complete: Laps needed after pit to recover gap + pit loss
    gap_after_stop: Projected gap after undercut completes
    recommendation: Strategic recommendation string
    """

    driver: str
    rival: str
    current_gap: float  # seconds (positive = driver is behind)
    pit_stop_loss: float  # seconds lost in pit lane
    pace_delta: float  # seconds per lap gained on fresh tyres
    laps_remaining: int
    laps_to_complete: float  # laps needed for undercut to work
    is_viable: bool
    gap_after_stop: float  # projected gap after undercut
    recommendation: str


@dataclass
class OvercutResult:
    """
    Result of overcut opportunity analysis.

    is_viable: True if staying out gains position
    laps_to_stay: How many extra laps to stay out
    """

    driver: str
    rival: str
    current_gap: float
    laps_to_stay: int
    gap_after_rival_stops: float
    is_viable: bool
    recommendation: str


# ── Core Functions ─────────────────────────────────────────────────────────────


def analyze_undercut(
    current_gap: float,
    pace_delta: float,
    laps_remaining: int,
    pit_stop_loss: float = PIT_STOP_LOSS,
    driver: str = "Driver",
    rival: str = "Rival",
) -> UndercutResult:
    """
    Analyze whether an undercut opportunity exists.

    Math:
    - Driver pits now, loses pit_stop_loss seconds
    - Driver gains pace_delta seconds per lap on fresh tyres
    - Undercut works if: (pace_delta × laps_remaining) > (pit_stop_loss + current_gap)

    Args:
        current_gap: Gap to rival in seconds (positive = behind rival)
        pace_delta: Pace advantage per lap on fresh tyres (seconds/lap)
        laps_remaining: Laps left in race
        pit_stop_loss: Time lost during pit stop
        driver: Driver code for labeling
        rival: Rival driver code for labeling

    Returns:
        UndercutResult dataclass
    """
    # Total gap to recover = pit stop loss + current gap
    total_to_recover = pit_stop_loss + current_gap

    # Laps needed to recover at pace_delta per lap
    if pace_delta <= 0:
        laps_to_complete = float("inf")
        is_viable = False
    else:
        laps_to_complete = total_to_recover / pace_delta
        is_viable = laps_to_complete <= laps_remaining

    # Projected gap after undercut completes
    gap_after_stop = (pace_delta * laps_remaining) - total_to_recover

    # Build recommendation
    if is_viable:
        recommendation = (
            f"UNDERCUT VIABLE — Pit now. Need {laps_to_complete:.1f} laps "
            f"to complete. Projected gap: +{gap_after_stop:.1f}s ahead."
        )
    else:
        recommendation = (
            f"UNDERCUT NOT VIABLE — Need {laps_to_complete:.1f} laps "
            f"but only {laps_remaining} remaining. Stay out or wait."
        )

    result = UndercutResult(
        driver=driver,
        rival=rival,
        current_gap=round(current_gap, 3),
        pit_stop_loss=pit_stop_loss,
        pace_delta=round(pace_delta, 3),
        laps_remaining=laps_remaining,
        laps_to_complete=round(laps_to_complete, 1),
        is_viable=is_viable,
        gap_after_stop=round(gap_after_stop, 3),
        recommendation=recommendation,
    )

    if is_viable:
        logger.success(f"Undercut VIABLE: {driver} vs {rival} — {recommendation}")
    else:
        logger.warning(f"Undercut NOT viable: {driver} vs {rival} — {recommendation}")

    return result


def analyze_overcut(
    current_gap: float,
    rival_deg_rate: float,
    laps_to_stay: int,
    pit_stop_loss: float = PIT_STOP_LOSS,
    driver: str = "Driver",
    rival: str = "Rival",
) -> OvercutResult:
    """
    Analyze whether an overcut opportunity exists.

    Logic: If rival pits now and driver stays out, rival loses
    pit_stop_loss seconds. Meanwhile rival's tyres were degrading
    at rival_deg_rate per lap — staying out builds a gap.

    Args:
        current_gap: Gap to rival in seconds (positive = behind)
        rival_deg_rate: Rival's tyre degradation rate (seconds/lap)
        laps_to_stay: How many extra laps driver plans to stay out
        pit_stop_loss: Time rival loses in pit lane
        driver: Driver code
        rival: Rival driver code

    Returns:
        OvercutResult dataclass
    """
    # Gap built while rival is in pits
    gap_during_stop = pit_stop_loss

    # Additional gap from rival's degradation before they pit
    deg_gap = rival_deg_rate * laps_to_stay

    # Total gap after rival stops
    gap_after_rival_stops = current_gap - gap_during_stop - deg_gap

    # Overcut works if driver comes out ahead (gap becomes negative)
    is_viable = gap_after_rival_stops < 0

    if is_viable:
        recommendation = (
            f"OVERCUT VIABLE — Stay out {laps_to_stay} more laps. "
            f"Projected gap after rival stops: {gap_after_rival_stops:.1f}s ahead."
        )
    else:
        recommendation = (
            f"OVERCUT NOT VIABLE — Gap after rival stops: "
            f"{gap_after_rival_stops:.1f}s still behind. Consider undercut."
        )

    result = OvercutResult(
        driver=driver,
        rival=rival,
        current_gap=round(current_gap, 3),
        laps_to_stay=laps_to_stay,
        gap_after_rival_stops=round(gap_after_rival_stops, 3),
        is_viable=is_viable,
        recommendation=recommendation,
    )

    if is_viable:
        logger.success(f"Overcut VIABLE: {driver} vs {rival}")
    else:
        logger.warning(f"Overcut NOT viable: {driver} vs {rival}")

    return result


def scan_undercut_opportunities(
    laps: pd.DataFrame,
    lap_number: int,
    laps_remaining: int,
) -> pd.DataFrame:
    """
    Scan all driver pairs for undercut opportunities at a given race lap.

    This is what a strategy engineer runs every lap during a race —
    scanning the entire field for opportunities.

    Args:
        laps: Full race lap DataFrame
        lap_number: Current race lap to analyze
        laps_remaining: Laps remaining in race

    Returns:
        pd.DataFrame: All viable undercut opportunities
    """
    logger.info(
        f"Scanning undercut opportunities at lap {lap_number} "
        f"({laps_remaining} remaining)"
    )

    clean = get_clean_race_laps(laps)
    degradation = analyze_race_degradation(laps)

    # Get positions at this lap
    lap_data = clean[clean["LapNumber"] == lap_number].copy()

    if lap_data.empty:
        logger.warning(f"No data found for lap {lap_number}")
        return pd.DataFrame()

    lap_data = lap_data.sort_values("Position")
    opportunities = []

    # Check each consecutive pair
    for i in range(len(lap_data) - 1):
        behind_driver = lap_data.iloc[i + 1]["Driver"]
        ahead_driver = lap_data.iloc[i]["Driver"]

        # Get gap — use cumulative lap time difference
        ahead_laps = clean[clean["Driver"] == ahead_driver]
        behind_laps = clean[clean["Driver"] == behind_driver]

        if ahead_laps.empty or behind_laps.empty:
            continue

        # Approximate gap from cumulative lap times
        ahead_total = ahead_laps[ahead_laps["LapNumber"] <= lap_number][
            "LapTimeSeconds"
        ].sum()

        behind_total = behind_laps[behind_laps["LapNumber"] <= lap_number][
            "LapTimeSeconds"
        ].sum()

        gap = behind_total - ahead_total

        # Get degradation rate for behind driver
        behind_deg = degradation[degradation["Driver"] == behind_driver]
        if behind_deg.empty:
            continue

        deg_rate = float(behind_deg["DegradationRate"].iloc[-1])

        # Fresh tyre pace delta = degradation accumulated + fresh tyre bonus
        pace_delta = (deg_rate * 5) + FRESH_TYRE_DELTA

        result = analyze_undercut(
            current_gap=gap,
            pace_delta=pace_delta,
            laps_remaining=laps_remaining,
            driver=behind_driver,
            rival=ahead_driver,
        )

        if result.is_viable:
            opportunities.append(
                {
                    "Driver": behind_driver,
                    "Rival": ahead_driver,
                    "Gap": result.current_gap,
                    "PaceDelta": result.pace_delta,
                    "LapsToComplete": result.laps_to_complete,
                    "GapAfterStop": result.gap_after_stop,
                }
            )

    df = pd.DataFrame(opportunities)

    if df.empty:
        logger.info("No undercut opportunities found at this lap")
    else:
        logger.success(f"Found {len(df)} undercut opportunities")

    return df
