"""
PitWall AI — Data Validation Layer
Validates processed lap data before storage to ensure quality and consistency.
"""

from typing import Any

import pandas as pd
from loguru import logger

# ── Validation Constants ───────────────────────────────────────────────────────

MIN_LAP_TIME_SECONDS = 60.0  # Slowest realistic F1 lap
MAX_LAP_TIME_SECONDS = 300.0  # 5 minutes — covers red flag laps
MIN_SPEED_KMH = 0.0
MAX_SPEED_KMH = 400.0
MIN_LAPS_PER_DRIVER = 3
QUALITY_THRESHOLD = 70.0  # Minimum % of valid laps to accept data

VALID_COMPOUNDS = {"SOFT", "MEDIUM", "HARD", "INTER", "WET", "UNKNOWN"}


# ── Core Validator ─────────────────────────────────────────────────────────────


def validate_laps(
    laps: pd.DataFrame,
    gp_name: str = "",
    session_type: str = "",
) -> dict[str, Any]:
    """
    Validate a lap DataFrame before storage.

    Runs 5 checks:
    1. Lap time null check
    2. Lap time range check (60s–300s)
    3. Compound validity check
    4. Speed range check (0–400 km/h)
    5. Minimum laps per driver check

    Args:
        laps: Raw lap DataFrame from FastF1
        gp_name: Grand Prix name for logging context
        session_type: Session type for logging context

    Returns:
        dict with is_valid, total_laps, valid_laps, invalid_laps,
        quality_score, issues, and flagged_drivers
    """
    context = f"{gp_name} {session_type}".strip()
    logger.info(f"Validating {len(laps)} laps — {context}")

    issues = []
    flagged_drivers = []

    # Convert LapTime to seconds if not already done
    if "LapTimeSeconds" not in laps.columns:
        laps = laps.copy()
        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

    # Track invalid lap indices
    invalid_indices = set()

    # ── Check 1: Null lap times ────────────────────────────────────────────────
    null_mask = laps["LapTimeSeconds"].isna()
    null_laps = laps[null_mask]

    for _, row in null_laps.iterrows():
        issues.append(
            {
                "lap": int(row["LapNumber"]) if pd.notna(row["LapNumber"]) else -1,
                "driver": row["Driver"],
                "issue": "LapTime is null",
            }
        )
        invalid_indices.add(row.name)

    # ── Check 2: Lap time range ────────────────────────────────────────────────
    range_mask = laps["LapTimeSeconds"].notna() & (
        (laps["LapTimeSeconds"] < MIN_LAP_TIME_SECONDS)
        | (laps["LapTimeSeconds"] > MAX_LAP_TIME_SECONDS)
    )
    range_laps = laps[range_mask]

    for _, row in range_laps.iterrows():
        issues.append(
            {
                "lap": int(row["LapNumber"]),
                "driver": row["Driver"],
                "issue": f"LapTime out of range: {row['LapTimeSeconds']:.3f}s",
            }
        )
        invalid_indices.add(row.name)

    # ── Check 3: Compound validity ─────────────────────────────────────────────
    if "Compound" in laps.columns:
        compound_mask = ~laps["Compound"].isin(VALID_COMPOUNDS)
        compound_laps = laps[compound_mask]

        for _, row in compound_laps.iterrows():
            issues.append(
                {
                    "lap": int(row["LapNumber"]),
                    "driver": row["Driver"],
                    "issue": f"Invalid compound: {row['Compound']}",
                }
            )
            invalid_indices.add(row.name)

    # ── Check 4: Speed range ───────────────────────────────────────────────────
    if "SpeedFL" in laps.columns:
        speed_mask = laps["SpeedFL"].notna() & (
            (laps["SpeedFL"] < MIN_SPEED_KMH) | (laps["SpeedFL"] > MAX_SPEED_KMH)
        )
        speed_laps = laps[speed_mask]

        for _, row in speed_laps.iterrows():
            issues.append(
                {
                    "lap": int(row["LapNumber"]),
                    "driver": row["Driver"],
                    "issue": f"SpeedFL out of range: {row['SpeedFL']:.1f} km/h",
                }
            )
            invalid_indices.add(row.name)

    # ── Check 5: Minimum laps per driver ──────────────────────────────────────
    driver_lap_counts = laps.groupby("Driver")["LapNumber"].count()
    low_lap_drivers = driver_lap_counts[
        driver_lap_counts < MIN_LAPS_PER_DRIVER
    ].index.tolist()

    for driver in low_lap_drivers:
        flagged_drivers.append(
            {
                "driver": driver,
                "issue": f"Only {driver_lap_counts[driver]} laps recorded",
            }
        )

    # ── Summary ────────────────────────────────────────────────────────────────
    total_laps = len(laps)
    invalid_laps = len(invalid_indices)
    valid_laps = total_laps - invalid_laps
    quality_score = (valid_laps / total_laps * 100) if total_laps > 0 else 0.0
    is_valid = quality_score >= QUALITY_THRESHOLD

    # Log summary
    if is_valid:
        logger.success(
            f"Validation passed — {context} | "
            f"Quality: {quality_score:.1f}% | "
            f"Valid: {valid_laps}/{total_laps}"
        )
    else:
        logger.warning(
            f"Validation failed — {context} | "
            f"Quality: {quality_score:.1f}% | "
            f"Valid: {valid_laps}/{total_laps}"
        )

    if issues:
        logger.debug(f"Issues found: {len(issues)}")
    if flagged_drivers:
        logger.warning(f"Flagged drivers: {[d['driver'] for d in flagged_drivers]}")

    return {
        "is_valid": is_valid,
        "total_laps": total_laps,
        "valid_laps": valid_laps,
        "invalid_laps": invalid_laps,
        "quality_score": round(quality_score, 2),
        "issues": issues,
        "flagged_drivers": flagged_drivers,
    }
