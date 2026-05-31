"""
PitWall AI — FastAPI Dependencies
Application-level session cache using a dictionary.
LRU cache doesn't work across uvicorn workers — use module-level dict instead.
"""

from loguru import logger

# Module-level cache — persists for the lifetime of the process
_SESSION_CACHE: dict = {}
_LAPS_CACHE: dict = {}


def get_cached_laps(year: int, gp: str, session_type: str):
    """
    Load and cache lap data at module level.
    Avoids repeated FastF1 session loading for the same session.
    """
    key = f"{year}_{gp}_{session_type}"
    if key not in _LAPS_CACHE:
        from core.data.f1_loader import load_laps

        logger.info(f"Cache MISS — loading laps: {year} {gp} {session_type}")
        _LAPS_CACHE[key] = load_laps(year, gp, session_type)
    else:
        logger.info(f"Cache HIT — {year} {gp} {session_type}")
    return _LAPS_CACHE[key]


def get_cached_session(year: int, gp: str, session_type: str):
    """
    Load and cache full session object at module level.
    """
    key = f"{year}_{gp}_{session_type}"
    if key not in _SESSION_CACHE:
        from core.data.f1_loader import load_session

        logger.info(f"Cache MISS — loading session: {year} {gp} {session_type}")
        _SESSION_CACHE[key] = load_session(year, gp, session_type)
    else:
        logger.info(f"Cache HIT — {year} {gp} {session_type}")
    return _SESSION_CACHE[key]
