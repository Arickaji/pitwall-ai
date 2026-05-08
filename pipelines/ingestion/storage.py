"""
PitWall AI — Processed Data Storage
Handles saving and loading of processed F1 data as Parquet files.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

# Project root — same pattern as f1_loader.py
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROCESSED_DIR = _PROJECT_ROOT / "data" / "processed"


def _build_path(year: int, gp: str, session_type: str, filename: str) -> Path:
    """
    Build the full path for a processed data file.

    Structure: data/processed/{year}/{gp}/{session_type}/{filename}

    This is a private helper — only used internally by save/load functions.
    The underscore prefix signals to other developers: don't call this directly.
    """
    return _PROCESSED_DIR / str(year) / gp / session_type / filename


def save_laps(
    laps: pd.DataFrame,
    year: int,
    gp: str,
    session_type: str,
) -> Path:
    """
    Save processed lap data as a Parquet file.

    Args:
        laps: Processed lap DataFrame
        year: Championship year
        gp: Grand Prix name
        session_type: Session type e.g. R, Q, FP1

    Returns:
        Path: The path where the file was saved

    Example:
        >>> path = save_laps(laps, 2024, 'Bahrain', 'R')
    """
    path = _build_path(year, gp, session_type, "laps.parquet")

    # Create folder structure if it doesn't exist
    # parents=True creates all intermediate folders
    # exist_ok=True means no error if folder already exists
    path.parent.mkdir(parents=True, exist_ok=True)

    laps.to_parquet(path, index=False)

    logger.success(f"Saved {len(laps)} laps → {path.relative_to(_PROJECT_ROOT)}")

    return path


def load_laps(
    year: int,
    gp: str,
    session_type: str,
) -> pd.DataFrame:
    """
    Load processed lap data from Parquet.

    Args:
        year: Championship year
        gp: Grand Prix name
        session_type: Session type e.g. R, Q, FP1

    Returns:
        pd.DataFrame: Processed lap data

    Raises:
        FileNotFoundError: If no processed data exists for this session

    Example:
        >>> laps = load_laps(2024, 'Bahrain', 'R')
    """
    path = _build_path(year, gp, session_type, "laps.parquet")

    if not path.exists():
        raise FileNotFoundError(
            f"No processed data found for {year} {gp} {session_type}. "
            f"Run the ingestion pipeline first: pitwall-load --year {year} --gp {gp} --session {session_type}"
        )

    laps = pd.read_parquet(path)

    logger.info(f"Loaded {len(laps)} laps ← {path.relative_to(_PROJECT_ROOT)}")

    return laps
