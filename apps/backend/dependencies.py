"""
PitWall AI — FastAPI Dependencies
Reusable dependency injection functions.
"""

from functools import lru_cache

from loguru import logger


@lru_cache(maxsize=32)
def get_cached_laps(year: int, gp: str, session_type: str):
    """
    Load and cache lap data — avoids repeated FastF1 API calls.
    LRU cache holds last 32 unique sessions in memory.
    """
    from core.data.f1_loader import load_laps

    logger.info(f"Loading laps: {year} {gp} {session_type}")
    return load_laps(year, gp, session_type)


@lru_cache(maxsize=8)
def get_cached_session(year: int, gp: str, session_type: str):
    """Load and cache full session object."""
    from core.data.f1_loader import load_session

    return load_session(year, gp, session_type)
