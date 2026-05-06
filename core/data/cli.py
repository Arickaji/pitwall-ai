"""
PitWall AI — CLI entry point for the data loader.
Allows testing the loader directly from terminal via `pitwall-load`.
"""

import argparse
from loguru import logger
from core.data.f1_loader import load_laps


def load_command() -> None:
    """
    CLI command: pitwall-load

    Example usage:
        pitwall-load --year 2024 --gp Bahrain --session R
        pitwall-load --year 2024 --gp Monaco --session Q --driver LEC
    """
    parser = argparse.ArgumentParser(
        prog="pitwall-load",
        description="PitWall AI — Load F1 race data from the terminal",
    )
    parser.add_argument("--year",    type=int, required=True, help="Championship year e.g. 2024")
    parser.add_argument("--gp",      type=str, required=True, help="Grand Prix name e.g. Bahrain")
    parser.add_argument("--session", type=str, required=True, help="Session type: R, Q, FP1, FP2, FP3")
    parser.add_argument("--driver",  type=str, default=None,  help="Optional driver code e.g. VER")

    args = parser.parse_args()

    logger.info(f"PitWall AI — Loading data...")

    laps = load_laps(
        year=args.year,
        gp=args.gp,
        session_type=args.session,
        driver=args.driver,
    )

    print(f"\n✅ Loaded {len(laps)} laps")
    print(f"Columns: {list(laps.columns)}")
    print(f"\nFirst 5 laps:\n{laps[['Driver','LapNumber','LapTime','Compound']].head()}")


if __name__ == "__main__":
    load_command()
