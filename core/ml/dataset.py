"""
PitWall AI — ML Dataset Builder
Builds multi-season training dataset from processed Parquet files.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from core.data.f1_loader import load_laps
from core.ml.features import engineer_features

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ML_DIR = _PROJECT_ROOT / "data" / "ml"

# Total laps per circuit — needed for LapsRemaining feature
CIRCUIT_TOTAL_LAPS = {
    "Bahrain Grand Prix": 57,
    "Saudi Arabian Grand Prix": 50,
    "Australian Grand Prix": 58,
    "Japanese Grand Prix": 53,
    "Chinese Grand Prix": 56,
    "Miami Grand Prix": 57,
    "Emilia Romagna Grand Prix": 63,
    "Monaco Grand Prix": 78,
    "Canadian Grand Prix": 70,
    "Spanish Grand Prix": 66,
    "Austrian Grand Prix": 71,
    "British Grand Prix": 52,
    "Hungarian Grand Prix": 70,
    "Belgian Grand Prix": 44,
    "Dutch Grand Prix": 72,
    "Italian Grand Prix": 53,
    "Azerbaijan Grand Prix": 51,
    "Singapore Grand Prix": 62,
    "United States Grand Prix": 56,
    "Mexico City Grand Prix": 71,
    "São Paulo Grand Prix": 71,
    "Las Vegas Grand Prix": 50,
    "Qatar Grand Prix": 57,
    "Abu Dhabi Grand Prix": 58,
}

DEFAULT_TOTAL_LAPS = 57


def build_season_features(year: int) -> pd.DataFrame:
    """
    Build feature dataset for a full season.

    Args:
        year: Championship year

    Returns:
        pd.DataFrame: Feature vectors for all races in season
    """
    import logging

    import fastf1

    logging.getLogger("fastf1").setLevel(logging.WARNING)

    logger.info(f"Building features for {year} season...")

    schedule = fastf1.get_event_schedule(year, include_testing=False)
    races = [
        row["EventName"]
        for _, row in schedule.iterrows()
        if row["EventFormat"] != "testing"
    ]

    season_features = []
    succeeded = 0
    failed = 0

    for gp_name in races:
        try:
            laps = load_laps(year, gp_name, "R")
            total_laps = CIRCUIT_TOTAL_LAPS.get(gp_name, DEFAULT_TOTAL_LAPS)

            # Extract circuit short name
            circuit = gp_name.replace(" Grand Prix", "").strip()

            features = engineer_features(
                laps,
                total_laps=total_laps,
                circuit=circuit,
                season=year,
            )

            season_features.append(features)
            succeeded += 1
            logger.debug(f"✓ {gp_name}: {len(features)} rows")

        except Exception as e:
            failed += 1
            logger.warning(f"✗ {gp_name}: {e}")
            continue

    if not season_features:
        logger.error(f"No features built for {year}")
        return pd.DataFrame()

    season_df = pd.concat(season_features, ignore_index=True)

    logger.success(
        f"{year} season: {succeeded}/{len(races)} races | "
        f"{len(season_df)} feature rows | "
        f"{season_df['PittedNextLap'].sum()} pit stops"
    )

    return season_df


def build_ml_dataset(
    years: list = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Build full multi-season ML training dataset.

    Args:
        years: List of seasons to include. Default: 2022-2024
        save: Whether to save as Parquet

    Returns:
        pd.DataFrame: Full training dataset
    """
    if years is None:
        years = [2022, 2023, 2024]

    logger.info(f"Building ML dataset for seasons: {years}")

    all_seasons = []

    for year in years:
        season_df = build_season_features(year)
        if not season_df.empty:
            all_seasons.append(season_df)

    if not all_seasons:
        raise ValueError("No data built — check FastF1 connectivity")

    full_dataset = pd.concat(all_seasons, ignore_index=True)

    # Dataset statistics
    logger.success(
        f"ML Dataset built:\n"
        f"  Total rows:    {len(full_dataset):,}\n"
        f"  Seasons:       {full_dataset['Season'].nunique()}\n"
        f"  Circuits:      {full_dataset['Circuit'].nunique()}\n"
        f"  Drivers:       {full_dataset['Driver'].nunique()}\n"
        f"  Pit stop rate: {full_dataset['PittedNextLap'].mean():.2%}"
    )

    if save:
        _ML_DIR.mkdir(parents=True, exist_ok=True)
        path = _ML_DIR / "training_dataset.parquet"
        full_dataset.to_parquet(path, index=False)
        logger.success(f"Dataset saved: {path}")

    return full_dataset
