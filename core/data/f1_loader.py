"""
PitWall AI — F1 Race Data Loader
Core module for loading and accessing Formula 1 session data via FastF1.
"""

from pathlib import Path

import fastf1
import pandas as pd
from loguru import logger

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
# ── Cache Configuration ────────────────────────────────────────────────────────
_CACHE_DIR = _PROJECT_ROOT / "data" / "cache"

# Enable cache at module level so all FastF1 calls use it
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(_CACHE_DIR))

# ── FastF1 Schedule Patch ──────────────────────────────────────────────────────


def _build_schedule_from_json(year: int):
    """
    Build a FastF1 EventSchedule from local JSON file.
    Handles pandas column-oriented JSON format.
    """
    import fastf1.events as _ev
    import pandas as pd

    schedule_file = _PROJECT_ROOT / "data" / "schedules" / f"schedule_{year}.json"
    if not schedule_file.exists():
        return None

    try:
        # pandas column-oriented format — read directly
        df = pd.read_json(schedule_file)

        # Rename snake_case columns to PascalCase
        KEY_MAP = {
            "round_number": "RoundNumber",
            "country": "Country",
            "location": "Location",
            "official_event_name": "OfficialEventName",
            "event_date": "EventDate",
            "event_name": "EventName",
            "gmt_offset": "GmtOffset",
            "event_format": "EventFormat",
            "session1": "Session1",
            "session1_date": "Session1Date",
            "session2": "Session2",
            "session2_date": "Session2Date",
            "session3": "Session3",
            "session3_date": "Session3Date",
            "session4": "Session4",
            "session4_date": "Session4Date",
            "session5": "Session5",
            "session5_date": "Session5Date",
            "f1_api_support": "F1ApiSupport",
        }
        df = df.rename(columns=KEY_MAP)

        # Add UTC columns if missing
        for i in range(1, 6):
            utc_col = f"Session{i}DateUtc"
            date_col = f"Session{i}Date"
            if utc_col not in df.columns and date_col in df.columns:
                df[utc_col] = df[date_col]

        # Parse date columns to datetime
        date_cols = (
            ["EventDate"]
            + [f"Session{i}Date" for i in range(1, 6)]
            + [f"Session{i}DateUtc" for i in range(1, 6)]
        )
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Ensure string columns are strings not dicts
        for col in ["EventName", "Country", "Location", "EventFormat"]:
            if col in df.columns:
                df[col] = df[col].astype(str)

        schedule = _ev.EventSchedule(df, year=year)
        logger.info(f"Schedule loaded from local file: {year} " f"({len(df)} events)")
        return schedule

    except Exception as e:
        logger.warning(f"Failed to load local schedule for {year}: {e}")
        return None


def _patch_fastf1_schedule():
    """
    Monkey-patch FastF1 get_event_schedule to use local JSON files.
    Falls back to network if local file unavailable.
    Called once at module import time.
    """
    import fastf1.events as _ev

    _original = _ev.get_event_schedule

    def _patched(year: int, **kwargs):
        schedule = _build_schedule_from_json(year)
        if schedule is not None:
            return schedule
        logger.warning(f"Local schedule not found for {year} — trying network")
        return _original(year, **kwargs)

    _ev.get_event_schedule = _patched
    # Also patch get_session to use patched get_event_schedule
    logger.debug("FastF1 schedule patched to use local JSON files")


# Apply patch immediately at module load
_patch_fastf1_schedule()


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

    # GP name to round number mapping — used as fallback when
    # FastF1 schedule API is unavailable (e.g. Docker/offline)
    GP_ROUNDS = {
        2024: {
            "Bahrain Grand Prix": 1,
            "Saudi Arabian Grand Prix": 2,
            "Australian Grand Prix": 3,
            "Japanese Grand Prix": 4,
            "Chinese Grand Prix": 5,
            "Miami Grand Prix": 6,
            "Emilia Romagna Grand Prix": 7,
            "Monaco Grand Prix": 8,
            "Canadian Grand Prix": 9,
            "Spanish Grand Prix": 10,
            "Austrian Grand Prix": 11,
            "British Grand Prix": 12,
            "Hungarian Grand Prix": 13,
            "Belgian Grand Prix": 14,
            "Dutch Grand Prix": 15,
            "Italian Grand Prix": 16,
            "Azerbaijan Grand Prix": 17,
            "Singapore Grand Prix": 18,
            "United States Grand Prix": 19,
            "Mexico City Grand Prix": 20,
            "São Paulo Grand Prix": 21,
            "Las Vegas Grand Prix": 22,
            "Qatar Grand Prix": 23,
            "Abu Dhabi Grand Prix": 24,
        },
        2023: {
            "Bahrain Grand Prix": 1,
            "Saudi Arabian Grand Prix": 2,
            "Australian Grand Prix": 3,
            "Azerbaijan Grand Prix": 4,
            "Miami Grand Prix": 5,
            "Monaco Grand Prix": 6,
            "Spanish Grand Prix": 7,
            "Canadian Grand Prix": 8,
            "Austrian Grand Prix": 9,
            "British Grand Prix": 10,
            "Hungarian Grand Prix": 11,
            "Belgian Grand Prix": 12,
            "Dutch Grand Prix": 13,
            "Italian Grand Prix": 14,
            "Singapore Grand Prix": 15,
            "Japanese Grand Prix": 16,
            "Qatar Grand Prix": 17,
            "United States Grand Prix": 18,
            "Mexico City Grand Prix": 19,
            "São Paulo Grand Prix": 20,
            "Las Vegas Grand Prix": 21,
            "Abu Dhabi Grand Prix": 22,
        },
        2022: {
            "Bahrain Grand Prix": 1,
            "Saudi Arabian Grand Prix": 2,
            "Australian Grand Prix": 3,
            "Emilia Romagna Grand Prix": 4,
            "Miami Grand Prix": 5,
            "Spanish Grand Prix": 6,
            "Monaco Grand Prix": 7,
            "Azerbaijan Grand Prix": 8,
            "Canadian Grand Prix": 9,
            "British Grand Prix": 10,
            "Austrian Grand Prix": 11,
            "French Grand Prix": 12,
            "Hungarian Grand Prix": 13,
            "Belgian Grand Prix": 14,
            "Dutch Grand Prix": 15,
            "Italian Grand Prix": 16,
            "Singapore Grand Prix": 17,
            "Japanese Grand Prix": 18,
            "United States Grand Prix": 19,
            "Mexico City Grand Prix": 20,
            "São Paulo Grand Prix": 21,
            "Abu Dhabi Grand Prix": 22,
        },
    }

    try:
        session = fastf1.get_session(year, gp, session_type)
        session.load()
        logger.success(
            f"Session loaded: {year} {gp} {session_label} "
            f"({len(session.laps)} laps)"
        )
        return session
    except Exception as e:
        # Fallback: use round number directly when schedule API unavailable
        round_num = GP_ROUNDS.get(year, {}).get(gp)
        if round_num:
            logger.warning(f"Schedule API unavailable, trying round number {round_num}")
            try:
                session = fastf1.get_session(year, round_num, session_type)
                session.load()
                logger.success(
                    f"Session loaded via round: {year} {gp} {session_label} "
                    f"({len(session.laps)} laps)"
                )
                return session
            except Exception as e2:
                logger.error(f"Round fallback failed: {e2}")
        logger.error(f"Failed to load session: {year} {gp} {session_type} — {e}")
        raise RuntimeError(
            f"Could not load session: {year} {gp} {session_type}. "
            f"Check GP name and session type are correct."
        ) from e


def load_laps(
    year: int,
    gp: str,
    session_type: str,
    driver: str | None = None,
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
    lap_number: int | None = None,
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
            raise ValueError(f"Lap {lap_number} not found for driver '{driver_upper}'.")
        lap = lap.iloc[0]
        logger.info(f"Loading telemetry: {driver_upper} lap {lap_number}")
    else:
        lap = driver_laps.pick_fastest()
        logger.info(f"Loading telemetry: {driver_upper} fastest lap")

    telemetry = lap.get_telemetry()
    logger.success(f"Telemetry loaded: {len(telemetry)} data points")

    return telemetry
