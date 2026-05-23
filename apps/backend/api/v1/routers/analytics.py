"""
PitWall AI — Analytics & Simulation API Endpoints
"""

import pandas as pd
from fastapi import APIRouter, HTTPException

from apps.backend.api.v1.schemas.analytics_schemas import (
    DegradationRecord,
    DegradationRequest,
    DegradationResponse,
    FinalStanding,
    MonteCarloRequest,
    MonteCarloResponse,
    PaceRecord,
    PaceRequest,
    PaceResponse,
    PitOptimizerRequest,
    PitOptimizerResponse,
    PitOption,
    RaceSimRequest,
    RaceSimResponse,
    UndercutRecord,
    UndercutRequest,
    UndercutResponse,
    WinProbability,
)

router = APIRouter()


# ── Degradation ────────────────────────────────────────────────────────────────


@router.post("/analytics/degradation", response_model=DegradationResponse)
async def get_degradation(request: DegradationRequest):
    """
    Analyze tyre degradation for a race session.

    Returns degradation rate, base pace and cliff lap per driver per stint.
    """
    try:
        from core.analytics.degradation import analyze_race_degradation
        from core.data.f1_loader import load_laps

        laps = load_laps(
            request.year,
            request.gp,
            request.session_type,
            driver=request.driver,
        )
        deg = analyze_race_degradation(laps)

        records = [
            DegradationRecord(
                driver=row["Driver"],
                compound=row["Compound"],
                stint=row["Stint"],
                laps=int(row["Laps"]),
                degradation_rate=(
                    round(float(row["DegradationRate"]), 4)
                    if not pd.isna(row["DegradationRate"])
                    else 0.0
                ),
                base_pace=(
                    round(float(row["BasePace"]), 3)
                    if not pd.isna(row["BasePace"])
                    else 0.0
                ),
                r_squared=(
                    round(float(row["RSquared"]), 4)
                    if not pd.isna(row["RSquared"])
                    else 0.0
                ),
                cliff_lap=float(row["CliffLap"]) if pd.notna(row["CliffLap"]) else None,
            )
            for _, row in deg.iterrows()
        ]

        return DegradationResponse(
            data=records,
            meta={
                "year": request.year,
                "gp": request.gp,
                "session_type": request.session_type,
                "total_stints": len(records),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Pace ───────────────────────────────────────────────────────────────────────


@router.post("/analytics/pace", response_model=PaceResponse)
async def get_pace(request: PaceRequest):
    """
    Get full race pace summary for all drivers.

    Returns median pace, best lap, consistency and gap to fastest.
    """
    try:
        from core.analytics.pace import full_race_pace_summary
        from core.data.f1_loader import load_laps

        laps = load_laps(request.year, request.gp, request.session_type)
        summary = full_race_pace_summary(laps)

        records = [
            PaceRecord(
                driver=row["Driver"],
                median_pace=round(float(row["MedianPace"]), 3),
                best_pace=round(float(row["BestPace"]), 3),
                consistency=round(float(row["Consistency"]), 3),
                clean_laps=int(row["CleanLaps"]),
                gap_to_fastest=round(float(row["GapToFastest"]), 3),
            )
            for _, row in summary.iterrows()
        ]

        return PaceResponse(
            data=records,
            meta={
                "year": request.year,
                "gp": request.gp,
                "session_type": request.session_type,
                "drivers": len(records),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Undercut Scanner ───────────────────────────────────────────────────────────


@router.post("/analytics/undercut", response_model=UndercutResponse)
async def scan_undercut(request: UndercutRequest):
    """
    Scan for undercut opportunities at a specific race lap.

    Returns all viable undercut opportunities ranked by laps to complete.
    """
    try:
        from core.analytics.strategy import scan_undercut_opportunities
        from core.data.f1_loader import load_laps

        laps = load_laps(request.year, request.gp, request.session_type)
        opportunities = scan_undercut_opportunities(
            laps,
            lap_number=request.lap_number,
            laps_remaining=request.laps_remaining,
        )

        if opportunities.empty:
            return UndercutResponse(
                data=[],
                meta={
                    "year": request.year,
                    "gp": request.gp,
                    "lap_number": request.lap_number,
                    "opportunities_found": 0,
                },
            )

        records = [
            UndercutRecord(
                driver=row["Driver"],
                rival=row["Rival"],
                gap=round(float(row["Gap"]), 3),
                pace_delta=round(float(row["PaceDelta"]), 3),
                laps_to_complete=round(float(row["LapsToComplete"]), 1),
                gap_after_stop=round(float(row["GapAfterStop"]), 3),
            )
            for _, row in opportunities.iterrows()
        ]

        return UndercutResponse(
            data=records,
            meta={
                "year": request.year,
                "gp": request.gp,
                "lap_number": request.lap_number,
                "opportunities_found": len(records),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Monte Carlo ────────────────────────────────────────────────────────────────


@router.post("/simulate/monte-carlo", response_model=MonteCarloResponse)
async def run_monte_carlo(request: MonteCarloRequest):
    """
    Run Monte Carlo race simulation from any lap.

    Returns win probability distribution for all drivers.
    """
    try:
        from core.data.f1_loader import load_laps
        from core.simulation.monte_carlo import MonteCarloSimulator
        from core.simulation.race_simulator import RaceSimulator

        laps = load_laps(request.year, request.gp, request.session_type)
        total_laps = int(laps["LapNumber"].max())

        sim = RaceSimulator(laps, total_laps=total_laps)
        mc = MonteCarloSimulator(sim)
        state = sim.build_state_from_lap(request.from_lap)
        result = mc.run(state, n_simulations=request.n_simulations, seed=42)

        win_probs = [
            WinProbability(
                driver=row["Driver"],
                win_probability=float(row["WinProbability"]),
                wins=int(row["Wins"]),
            )
            for _, row in result.win_probabilities.iterrows()
            if row["WinProbability"] > 0
        ]

        return MonteCarloResponse(
            win_probabilities=win_probs,
            n_simulations=request.n_simulations,
            meta={
                "year": request.year,
                "gp": request.gp,
                "from_lap": request.from_lap,
                "total_laps": total_laps,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Pit Optimizer ──────────────────────────────────────────────────────────────


@router.post("/simulate/pit-optimizer", response_model=PitOptimizerResponse)
async def optimize_pit(request: PitOptimizerRequest):
    """
    Find optimal pit stop lap for a driver.

    Evaluates all pit options in window and ranks by projected position.
    """
    try:
        from core.data.f1_loader import load_laps
        from core.simulation.pit_optimizer import PitOptimizer
        from core.simulation.race_simulator import RaceSimulator

        laps = load_laps(request.year, request.gp, request.session_type)
        total_laps = int(laps["LapNumber"].max())

        sim = RaceSimulator(laps, total_laps=total_laps)
        opt = PitOptimizer(sim)
        state = sim.build_state_from_lap(request.from_lap)
        result = opt.optimize(
            state=state,
            driver=request.driver,
            new_compound=request.new_compound,
            earliest_pit=request.earliest_pit,
            latest_pit=request.latest_pit,
        )

        options = [
            PitOption(
                pit_lap=int(row["PitLap"]),
                projected_position=int(row["ProjectedPos"]),
                gap_to_ahead=float(row["GapToAhead"]),
                gap_to_behind=float(row["GapToBehind"]),
                compound=row["Compound"],
                score=float(row["Score"]),
            )
            for _, row in result.all_options.head(10).iterrows()
        ]

        return PitOptimizerResponse(
            optimal_lap=result.optimal_lap,
            recommendation=result.recommendation,
            all_options=options,
            meta={
                "year": request.year,
                "gp": request.gp,
                "driver": request.driver,
                "from_lap": request.from_lap,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Race Simulator ─────────────────────────────────────────────────────────────


@router.post("/simulate/race", response_model=RaceSimResponse)
async def simulate_race(request: RaceSimRequest):
    """
    Simulate race from a given lap to finish.

    Returns final standings and winner.
    """
    try:
        from core.data.f1_loader import load_laps
        from core.simulation.race_simulator import RaceSimulator

        laps = load_laps(request.year, request.gp, request.session_type)
        total_laps = int(laps["LapNumber"].max())

        sim = RaceSimulator(laps, total_laps=total_laps)
        state = sim.build_state_from_lap(request.from_lap)
        result = sim.simulate(state)

        standings = [
            FinalStanding(
                driver=row["Driver"],
                position=int(row["Position"]),
                compound=row["Compound"],
                tyre_age=int(row["TyreAge"]),
                gap_to_leader=float(row["GapToLeader"]),
            )
            for _, row in result.final_standings.iterrows()
        ]

        return RaceSimResponse(
            winner=result.final_standings["Driver"].iloc[0],
            final_standings=standings,
            meta={
                "year": request.year,
                "gp": request.gp,
                "from_lap": request.from_lap,
                "total_laps": total_laps,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
