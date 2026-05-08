"""
PitWall AI — Season Ingestion Pipeline
Ingests all races for a given season and stores them as Parquet files.
"""

import logging

import fastf1
from loguru import logger

from core.data.f1_loader import load_laps
from pipelines.ingestion.storage import save_laps

logging.getLogger("fastf1").setLevel(logging.WARNING)


def get_season_calendar(year: int) -> list[dict]:
    """
    Fetch the official race calendar for a given season from FastF1.

    This is dynamic — works for any year FastF1 supports (2018+).
    No hardcoded race lists needed.

    Args:
        year: Championship year

    Returns:
        List of dicts with 'round' and 'gp_name' for each race
    """
    logger.info(f"Fetching {year} season calendar from FastF1...")

    schedule = fastf1.get_event_schedule(year, include_testing=False)

    races = [
        {
            "round": int(row["RoundNumber"]),
            "gp_name": row["EventName"],
        }
        for _, row in schedule.iterrows()
        if row["EventFormat"] != "testing"
    ]

    logger.info(f"Found {len(races)} races in {year} season")
    return races


def ingest_season(
    year: int,
    session_type: str = "R",
) -> dict:
    """
    Ingest all races for a given season and store as Parquet files.

    Continues on failure — one bad race won't stop the pipeline.
    Reports a full summary at the end.

    Args:
        year: Championship year (2018–2026)
        session_type: Session to ingest — default is Race ('R')

    Returns:
        dict: Summary with succeeded and failed races

    Example:
        >>> summary = ingest_season(2024)
        >>> summary = ingest_season(2023, session_type='Q')
    """
    logger.info(f"Starting ingestion: {year} season — session type: {session_type}")

    races = get_season_calendar(year)

    succeeded = []
    failed = []

    for race in races:
        gp_name = race["gp_name"]
        round_num = race["round"]

        logger.info(f"[Round {round_num:02d}/24] Processing: {gp_name}")

        try:
            # Load from FastF1
            laps = load_laps(year, gp_name, session_type)

            # Save as Parquet
            save_laps(laps, year, gp_name, session_type)

            succeeded.append(gp_name)
            logger.success(f"✓ {gp_name} — {len(laps)} laps saved")

        except Exception as e:
            # Log the error but continue to next race
            failed.append({"gp": gp_name, "error": str(e)})
            logger.error(f"✗ {gp_name} — {e}")
            continue

    # Summary report
    logger.info("=" * 50)
    logger.info(f"INGESTION COMPLETE — {year} Season")
    logger.info(f"✓ Succeeded: {len(succeeded)}/{len(races)}")
    logger.info(f"✗ Failed:    {len(failed)}/{len(races)}")

    if failed:
        logger.warning("Failed races:")
        for f in failed:
            logger.warning(f"  - {f['gp']}: {f['error']}")

    logger.info("=" * 50)

    return {
        "year": year,
        "session_type": session_type,
        "total": len(races),
        "succeeded": succeeded,
        "failed": failed,
    }


if __name__ == "__main__":
    # Run directly: python -m pipelines.ingestion.ingest_season
    import sys

    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    session_type = sys.argv[2] if len(sys.argv) > 2 else "R"
    ingest_season(year, session_type)
