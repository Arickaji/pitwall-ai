"""
PitWall AI — F1 Race Data Loader
Core module for loading and accessing Formula 1 session data via FastF1.
"""

from pathlib import Path
from typing import Optional

import fastf1
import pandas as pd
from loguru import logger


# ── Cache Configuration ────────────────────────────────────────────────────────

# Always resolve cache path relative to project root, not cwd
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CACHE_DIR = _PROJECT_ROOT / "data" / "cache"


def _enable_cache() -> None:
    """Enable FastF1 cache, creating the directory if it doesn't exist."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(_CACHE_DIR))
    logger.debug(f"FastF1 cache enabled at: {_CACHE_DIR}")


# ── Input Validation ───────────────────────────────────────────────────────────

_VALID_SESSION_TYPES = {"R", "Q", "S", "SS", "FP1", "FP2", "FP3"}

_SESSION_LABELS = {
    "R": "Race",
    "Q": "Qualifying",
    "S": "Sprint",
    "SS": "Sprint Shootout",
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
}


def _validate_inputs(year: int, gp: str, session_type: str) -> str:
    """
    Validate inputs before making any API calls.

    Args:
        year: Championship year (2018 onwards, FastF1 coverage start)
        gp: Grand Prix name or round number
        session_type: One of R, Q, S, SS, FP1, FP2, FP3

    Returns:
        str: Normalized (uppercased) session type

    Raises:
        ValueError: If any input is invalid
    """
    current_year = 2026

    if not isinstance(year, int) or year < 2018 or year > current_year:
        raise ValueError(
            f"Invalid year '{year}'. Must be an integer between 2018 and {current_year}."
        )

    if not gp or not isinstance(gp, str):
        raise ValueError("Grand Prix name must be a non-empty string.")

    session_upper = session_type.upper()
    if session_upper not in _VALID_SESSION_TYPES:
        raise ValueError(
            f"Invalid session type '{session_type}'. "
            f"Must be one of: {', '.join(sorted(_VALID_SESSION_TYPES))}"
        )

    # Return normalized value so callers always pass correct case to FastF1
    return session_upper


# ── Core Loader ────────────────────────────────────────────────────────────────

def load_session(
    year: int,
    gp: str,
    session_type: str,
) -> fastf1.core.Session:
    """
    Load a full FastF1 session object.

    Use this when you need access to the raw session, including
    telemetry, weather, car data, and results.

    Args:
        year: Championship year (2018–2026)
        gp: Grand Prix name e.g. 'Bahrain', 'Monaco', 'British'
        session_type: Session identifier — R, Q, FP1, FP2, FP3, S, SS

    Returns:
        fastf1.core.Session: Fully loaded session object

    Raises:
        ValueError: If inputs are invalid
        RuntimeError: If session data cannot be loaded

    Example:
        >>> session = load_session(2024, 'Bahrain', 'R')
        >>> session.laps.shape
    """
    session_type = _validate_inputs(year, gp, session_type)
    _enable_cache()

    session_label = _SESSION_LABELS.get(session_type, session_type)
    logger.info(f"Loading {year} {gp} — {session_label}")

    try:
        session = fastf1.get_session(year, gp, session_type)
        session.load()
        logger.success(
            f"Session loaded: {year} {gp} {session_label} "
            f"({len(session.laps)} laps)"
        )
        return session

    except Exception as e:
        logger.error(f"Failed to load session: {year} {gp} {session_type} — {e}")
        raise RuntimeError(
            f"Could not load session: {year} {gp} {session_type}. "
            f"Check GP name and session type are correct."
        ) from e


def load_laps(
    year: int,
    gp: str,
    session_type: str,
    driver: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load lap data for a session, optionally filtered by driver.

    This is the most commonly used loader — returns a clean DataFrame
    of lap times, compounds, stints, and sector times.

    Args:
        year: Championship year (2018–2026)
        gp: Grand Prix name e.g. 'Bahrain', 'Monaco', 'British'
        session_type: Session identifier — R, Q, FP1, FP2, FP3, S, SS
        driver: Optional 3-letter driver code e.g. 'VER', 'HAM', 'LEC'

    Returns:
        pd.DataFrame: Lap data with timing, compound, and stint info

    Raises:
        ValueError: If inputs are invalid or driver code not found
        RuntimeError: If session data cannot be loaded

    Example:
        >>> laps = load_laps(2024, 'Bahrain', 'R')
        >>> laps = load_laps(2024, 'Bahrain', 'R', driver='VER')
    """
    session = load_session(year, gp, session_type)
    laps = session.laps

    if driver is not None:
        driver_upper = driver.upper()
        available = laps["Driver"].unique().tolist()

        if driver_upper not in available:
            raise ValueError(
                f"Driver '{driver_upper}' not found in this session. "
                f"Available drivers: {', '.join(sorted(available))}"
            )

        laps = laps.pick_drivers(driver_upper)
        logger.info(f"Filtered to driver: {driver_upper} ({len(laps)} laps)")

    return laps.reset_index(drop=True)


def load_telemetry(
    year: int,
    gp: str,
    session_type: str,
    driver: str,
    lap_number: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load telemetry data for a specific driver, optionally for one lap.

    Telemetry includes: Speed, RPM, Gear, Throttle, Brake, DRS,
    and track position (X, Y, Z).

    Args:
        year: Championship year (2018–2026)
        gp: Grand Prix name
        session_type: Session identifier
        driver: 3-letter driver code e.g. 'VER', 'HAM'
        lap_number: Optional specific lap number. If None, returns fastest lap.

    Returns:
        pd.DataFrame: Telemetry data for the specified lap

    Raises:
        ValueError: If driver not found or lap number doesn't exist
        RuntimeError: If session data cannot be loaded

    Example:
        >>> tel = load_telemetry(2024, 'Bahrain', 'R', 'VER')
        >>> tel = load_telemetry(2024, 'Bahrain', 'R', 'VER', lap_number=10)
    """
    session = load_session(year, gp, session_type)
    driver_upper = driver.upper()

    driver_laps = session.laps.pick_drivers(driver_upper)

    if driver_laps.empty:
        raise ValueError(f"No laps found for driver '{driver_upper}'.")

    if lap_number is not None:
        lap = driver_laps[driver_laps["LapNumber"] == lap_number]
        if lap.empty:
            raise ValueError(
                f"Lap {lap_number} not found for driver '{driver_upper}'."
            )
        lap = lap.iloc[0]
        logger.info(f"Loading telemetry: {driver_upper} lap {lap_number}")
    else:
        lap = driver_laps.pick_fastest()
        logger.info(f"Loading telemetry: {driver_upper} fastest lap")

    telemetry = lap.get_telemetry()
    logger.success(f"Telemetry loaded: {len(telemetry)} data points")

    return telemetry
