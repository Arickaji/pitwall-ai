"""
PitWall AI — Safety Car Simulation Model
Models safety car probability and strategic impact on race outcomes.
Integrates with Monte Carlo simulation engine.
"""

from dataclasses import dataclass

import pandas as pd
from loguru import logger

from core.data.f1_loader import load_session

# ── Constants ──────────────────────────────────────────────────────────────────

# Default SC probability if insufficient historical data
DEFAULT_SC_PROBABILITY = 0.35  # 35% chance per race historically
SC_DURATION_LAPS = 5  # Average SC period length in laps
VSC_DURATION_LAPS = 3  # Average VSC period length in laps
SC_FIELD_BUNCH_GAP = 2.0  # Maximum gap between cars during SC (seconds)


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class SafetyCarEvent:
    """
    Represents a safety car period in a race.

    start_lap:  Lap SC was deployed
    end_lap:    Lap SC returned to pits
    event_type: 'SC' or 'VSC'
    """

    start_lap: int
    end_lap: int
    event_type: str  # 'SC' or 'VSC'

    @property
    def duration(self) -> int:
        return self.end_lap - self.start_lap


@dataclass
class SCStrategyResult:
    """
    Result of safety car strategy analysis.

    pit_recommendation: Should driver pit under SC?
    position_gain:      Estimated positions gained/lost
    tyre_advantage:     Laps of tyre life advantage gained
    """

    driver: str
    sc_lap: int
    tyre_age: int
    compound: str
    pit_recommendation: bool
    position_gain: int
    tyre_advantage: int
    reasoning: str


# ── Historical SC Analysis ─────────────────────────────────────────────────────


def calculate_sc_probability(
    gp_name: str,
    years: list = None,
) -> dict:
    """
    Calculate historical safety car probability for a circuit.

    Loads past races from FastF1 and counts SC/VSC periods
    using TrackStatus data.

    Args:
        gp_name: Grand Prix name e.g. 'Bahrain Grand Prix'
        years: List of years to analyze. Default: 2018-2024

    Returns:
        dict with SC probability and historical data
    """
    if years is None:
        years = list(range(2018, 2025))

    logger.info(f"Calculating SC probability for {gp_name} ({years[0]}-{years[-1]})")

    sc_count = 0
    vsc_count = 0
    races_analyzed = 0

    for year in years:
        try:
            session = load_session(year, gp_name, "R")
            laps = session.laps

            if "TrackStatus" not in laps.columns:
                continue

            # Check for SC periods — Status 4=SC, 6=VSC, 7=SC ending
            has_sc = laps["TrackStatus"].astype(str).str.contains("4", na=False).any()
            has_vsc = laps["TrackStatus"].astype(str).str.contains("6", na=False).any()

            if has_sc:
                sc_count += 1
                logger.debug(f"SC detected: {year} {gp_name}")

            if has_vsc:
                vsc_count += 1
                logger.debug(f"VSC detected: {year} {gp_name}")

            races_analyzed += 1

        except Exception as e:
            logger.warning(f"Could not load {year} {gp_name}: {e}")
            continue

    if races_analyzed == 0:
        logger.warning(f"No data found for {gp_name} — using default SC probability")
        return {
            "gp_name": gp_name,
            "races_analyzed": 0,
            "sc_count": 0,
            "vsc_count": 0,
            "sc_probability": DEFAULT_SC_PROBABILITY,
            "vsc_probability": DEFAULT_SC_PROBABILITY * 0.6,
        }

    sc_probability = sc_count / races_analyzed
    vsc_probability = vsc_count / races_analyzed

    logger.success(
        f"SC probability for {gp_name}: "
        f"SC={sc_probability:.1%} VSC={vsc_probability:.1%} "
        f"({races_analyzed} races analyzed)"
    )

    return {
        "gp_name": gp_name,
        "races_analyzed": races_analyzed,
        "sc_count": sc_count,
        "vsc_count": vsc_count,
        "sc_probability": round(sc_probability, 3),
        "vsc_probability": round(vsc_probability, 3),
    }


def detect_sc_events(laps: pd.DataFrame) -> list[SafetyCarEvent]:
    """
    Detect all SC and VSC events in a race.

    Uses FastF1 TrackStatus:
    - Status containing '4' = Safety Car
    - Status containing '6' = Virtual Safety Car

    Args:
        laps: Full race lap DataFrame

    Returns:
        List of SafetyCarEvent objects
    """
    if "TrackStatus" not in laps.columns:
        return []

    events = []
    sc_laps = laps[laps["TrackStatus"].astype(str).str.contains("4|6", na=False)].copy()

    if sc_laps.empty:
        logger.info("No SC events detected in race")
        return []

    # Group consecutive SC laps into events
    sc_lap_numbers = sorted(sc_laps["LapNumber"].unique())

    if not sc_lap_numbers:
        return []

    # Find continuous periods
    event_start = sc_lap_numbers[0]
    prev_lap = sc_lap_numbers[0]

    for lap in sc_lap_numbers[1:]:
        if lap > prev_lap + 2:  # Gap of more than 2 laps = new event
            # Determine event type
            period_laps = sc_laps[
                (sc_laps["LapNumber"] >= event_start)
                & (sc_laps["LapNumber"] <= prev_lap)
            ]
            has_sc = period_laps["TrackStatus"].astype(str).str.contains("4").any()
            event_type = "SC" if has_sc else "VSC"

            events.append(
                SafetyCarEvent(
                    start_lap=int(event_start),
                    end_lap=int(prev_lap),
                    event_type=event_type,
                )
            )
            event_start = lap

        prev_lap = lap

    # Add final event
    period_laps = sc_laps[sc_laps["LapNumber"] >= event_start]
    has_sc = period_laps["TrackStatus"].astype(str).str.contains("4").any()
    event_type = "SC" if has_sc else "VSC"

    events.append(
        SafetyCarEvent(
            start_lap=int(event_start),
            end_lap=int(prev_lap),
            event_type=event_type,
        )
    )

    logger.info(f"Detected {len(events)} SC/VSC events")
    return events


# ── SC Strategy Analysis ───────────────────────────────────────────────────────


def analyze_sc_strategy(
    driver: str,
    tyre_age: int,
    compound: str,
    position: int,
    gap_ahead: float,
    laps_remaining: int,
    sc_lap: int,
) -> SCStrategyResult:
    """
    Analyze whether to pit under safety car.

    Decision framework:
    1. Tyre age > 15 laps → strong case for pitting
    2. Gap to car ahead < 5s → pitting risks losing position
    3. Laps remaining < 10 → not worth pitting (no time to recover)
    4. Position P1-P3 → more conservative (protect position)
    5. Position P4+ → more aggressive (nothing to lose)

    Args:
        driver:         Driver code
        tyre_age:       Current tyre age in laps
        compound:       Current compound
        position:       Current race position
        gap_ahead:      Gap to car ahead in seconds
        laps_remaining: Laps remaining in race
        sc_lap:         Lap SC was deployed

    Returns:
        SCStrategyResult with recommendation
    """
    # Decision factors
    tyre_worn = tyre_age > 15
    enough_laps = laps_remaining > 10
    safe_to_pit = gap_ahead > 5.0 or position > 5
    front_runner = position <= 3

    # Tyre advantage from fresh set
    tyre_advantage = min(tyre_age, 20)  # capped at 20 laps benefit

    # Position gain/loss estimate
    if safe_to_pit and tyre_worn and enough_laps:
        pit_recommendation = True
        position_gain = 1 if front_runner else 2
        reasoning = (
            f"PIT RECOMMENDED — Tyre age {tyre_age} laps, "
            f"{laps_remaining} laps remaining. "
            f"Fresh tyres give {tyre_advantage} lap advantage. "
            f"Expected gain: +{position_gain} positions at restart."
        )
    elif not enough_laps:
        pit_recommendation = False
        position_gain = 0
        reasoning = (
            f"STAY OUT — Only {laps_remaining} laps remaining. "
            f"Not enough laps to recover pit stop loss."
        )
    elif not tyre_worn:
        pit_recommendation = False
        position_gain = 0
        reasoning = (
            f"STAY OUT — Tyres only {tyre_age} laps old. "
            f"Still competitive. Maintain track position."
        )
    else:
        pit_recommendation = False
        position_gain = -1
        reasoning = (
            f"STAY OUT — Gap ahead only {gap_ahead:.1f}s. "
            f"Pitting risks losing P{position}. "
            f"Monitor situation."
        )

    return SCStrategyResult(
        driver=driver,
        sc_lap=sc_lap,
        tyre_age=tyre_age,
        compound=compound,
        pit_recommendation=pit_recommendation,
        position_gain=position_gain,
        tyre_advantage=tyre_advantage,
        reasoning=reasoning,
    )


def inject_sc_into_simulation(
    lap_records: list,
    sc_event: SafetyCarEvent,
    field_bunch_gap: float = SC_FIELD_BUNCH_GAP,
) -> list:
    """
    Inject a safety car event into simulation lap records.

    During SC: compress all gaps to bunch_gap maximum.
    After SC: restore relative order but with compressed gaps.

    Args:
        lap_records: List of lap record dicts from simulator
        sc_event: SafetyCarEvent to inject
        field_bunch_gap: Max gap between cars during SC

    Returns:
        Modified lap records with SC effect applied
    """
    logger.info(
        f"Injecting {sc_event.event_type} "
        f"laps {sc_event.start_lap}-{sc_event.end_lap}"
    )

    for record in lap_records:
        lap = record.get("Lap", 0)

        if sc_event.start_lap <= lap <= sc_event.end_lap:
            # Compress gaps during SC period
            current_gap = record.get("GapToLeader", 0)
            position = record.get("Position", 1)

            # Each position has field_bunch_gap seconds gap
            record["GapToLeader"] = round(
                min(current_gap, (position - 1) * field_bunch_gap), 3
            )

    return lap_records
