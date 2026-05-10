"""
PitWall AI — Driver Pace Comparison Engine
Normalized pace comparison controlling for compound and tyre age.
"""

import pandas as pd
from loguru import logger


def get_clean_race_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to clean racing laps only — removes pit laps,
    safety car laps, and inaccurate laps.

    This is the foundation of all pace analysis.
    Garbage in = garbage out.

    Args:
        laps: Full race lap DataFrame

    Returns:
        pd.DataFrame: Clean laps only
    """
    if "LapTimeSeconds" not in laps.columns:
        laps = laps.copy()
        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

    clean = laps[
        laps["IsAccurate"]
        & (laps["LapTimeSeconds"].notna())
        & (laps["LapTimeSeconds"] > 60)
        & (laps["LapTimeSeconds"] < 300)
    ].copy()

    removed = len(laps) - len(clean)
    logger.debug(f"Clean laps: {len(clean)}/{len(laps)} ({removed} removed)")

    return clean.reset_index(drop=True)


def compound_normalized_pace(
    laps: pd.DataFrame,
    tyre_life_window: int = 10,
) -> pd.DataFrame:
    """
    Calculate normalized pace per driver per compound.

    Controls for tyre age by only comparing laps within the same
    tyre life window. This isolates true car/driver performance.

    Args:
        laps: Clean race lap DataFrame
        tyre_life_window: Max tyre life to include (removes heavily worn laps)

    Returns:
        pd.DataFrame: Normalized pace per driver per compound
    """
    clean = get_clean_race_laps(laps)

    # Filter to comparable tyre age window
    windowed = clean[clean["TyreLife"] <= tyre_life_window].copy()

    if windowed.empty:
        logger.warning("No laps found within tyre life window")
        return pd.DataFrame()

    pace = (
        windowed.groupby(["Driver", "Compound"])["LapTimeSeconds"]
        .agg(
            MedianPace="median",
            MeanPace="mean",
            BestPace="min",
            Consistency="std",
            LapCount="count",
        )
        .round(3)
        .reset_index()
        .sort_values(["Compound", "MedianPace"])
    )

    logger.info(f"Compound-normalized pace: {len(pace)} driver/compound combinations")
    return pace


def pace_delta(
    laps: pd.DataFrame,
    reference_driver: str,
    compound: str,
) -> pd.DataFrame:
    """
    Calculate pace delta of all drivers vs a reference driver
    on the same compound.

    Positive delta = slower than reference
    Negative delta = faster than reference

    Args:
        laps: Clean race lap DataFrame
        reference_driver: Driver code to compare against e.g. 'VER'
        compound: Compound to compare e.g. 'SOFT', 'HARD'

    Returns:
        pd.DataFrame: Pace delta vs reference driver
    """
    pace = compound_normalized_pace(laps)

    # Filter to requested compound
    compound_pace = pace[pace["Compound"] == compound.upper()].copy()

    if compound_pace.empty:
        raise ValueError(f"No pace data found for compound: {compound}")

    # Get reference driver pace
    ref_data = compound_pace[compound_pace["Driver"] == reference_driver.upper()]

    if ref_data.empty:
        raise ValueError(
            f"Driver '{reference_driver}' not found for compound '{compound}'"
        )

    ref_pace = ref_data["MedianPace"].iloc[0]

    # Calculate delta vs reference
    compound_pace["PaceDelta"] = (compound_pace["MedianPace"] - ref_pace).round(3)

    compound_pace["Reference"] = reference_driver.upper()

    return compound_pace.sort_values("PaceDelta").reset_index(drop=True)


def full_race_pace_summary(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Full race pace summary — median pace per driver across all compounds.

    Uses median to be robust against outliers. This gives the overall
    race pace picture regardless of strategy.

    Args:
        laps: Full race lap DataFrame

    Returns:
        pd.DataFrame: Race pace summary per driver
    """
    clean = get_clean_race_laps(laps)

    summary = (
        clean.groupby("Driver")["LapTimeSeconds"]
        .agg(
            MedianPace="median",
            BestPace="min",
            Consistency="std",
            CleanLaps="count",
        )
        .round(3)
        .reset_index()
        .sort_values("MedianPace")
        .reset_index(drop=True)
    )

    # Add gap to fastest driver
    fastest = summary["MedianPace"].iloc[0]
    summary["GapToFastest"] = (summary["MedianPace"] - fastest).round(3)

    logger.success(
        f"Race pace summary: {len(summary)} drivers | "
        f"Fastest: {summary['Driver'].iloc[0]} "
        f"({fastest:.3f}s)"
    )

    return summary
