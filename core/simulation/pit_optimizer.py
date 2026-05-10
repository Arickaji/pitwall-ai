"""
PitWall AI — Pit Stop Optimization Engine
Finds the optimal pit stop lap by evaluating all possible
pit windows and ranking by projected finishing position.
"""

from dataclasses import dataclass

import pandas as pd
from loguru import logger

from core.simulation.race_simulator import RaceSimulator, RaceState

# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class PitOption:
    """
    Result of evaluating one specific pit lap.

    pit_lap:           The lap to pit on
    projected_position: Finishing position after this strategy
    gap_to_ahead:      Gap to car ahead at finish
    gap_to_behind:     Gap to car behind at finish
    compound:          New compound after pit
    score:             Overall strategy score (lower = better)
    """

    pit_lap: int
    projected_position: int
    gap_to_ahead: float
    gap_to_behind: float
    new_compound: str
    score: float


@dataclass
class OptimizationResult:
    """
    Full result of pit stop optimization.

    optimal_lap:    Best pit lap
    all_options:    All evaluated pit options ranked by score
    current_position: Driver's position before optimization
    """

    driver: str
    current_lap: int
    current_position: int
    optimal_lap: int
    optimal_compound: str
    all_options: pd.DataFrame
    recommendation: str


# ── Optimizer ──────────────────────────────────────────────────────────────────


class PitOptimizer:
    """
    Pit stop optimization engine.

    Evaluates all possible pit laps for a driver and ranks them
    by projected finishing position using the race simulator.

    Usage:
        optimizer = PitOptimizer(simulator)
        result = optimizer.optimize(state, driver='VER', new_compound='HARD')
    """

    def __init__(self, simulator: RaceSimulator):
        """
        Args:
            simulator: Initialized RaceSimulator instance
        """
        self.simulator = simulator
        logger.debug("PitOptimizer initialized")

    def _score_option(
        self,
        position: int,
        gap_to_ahead: float,
        gap_to_behind: float,
    ) -> float:
        """
        Score a pit option — lower is better.

        Scoring formula:
        - Position is the primary factor (×100 weight)
        - Gap to ahead is secondary — smaller gap = better for racing
        - Gap to behind is tertiary — larger gap = safer position

        Args:
            position: Projected finishing position
            gap_to_ahead: Gap to car ahead at finish
            gap_to_behind: Gap to car behind at finish

        Returns:
            float: Score (lower = better strategy)
        """
        position_score = position * 100
        gap_ahead_score = gap_to_ahead * 0.5
        gap_behind_score = -gap_to_behind * 0.1  # negative = reward big gap behind

        return position_score + gap_ahead_score + gap_behind_score

    def optimize(
        self,
        state: RaceState,
        driver: str,
        new_compound: str,
        earliest_pit: int | None = None,
        latest_pit: int | None = None,
    ) -> OptimizationResult:
        """
        Find optimal pit lap for a driver.

        Evaluates every possible pit lap in the window and
        simulates the race for each option.

        Args:
            state: Current race state
            driver: Driver code to optimize e.g. 'VER'
            new_compound: Compound to put on after pit e.g. 'HARD'
            earliest_pit: Earliest lap to consider pitting (default: next lap)
            latest_pit: Latest lap to consider (default: 10 laps before end)

        Returns:
            OptimizationResult with ranked pit options
        """
        driver = driver.upper()

        # Find driver in state
        driver_state = next((d for d in state.drivers if d.driver == driver), None)

        if driver_state is None:
            raise ValueError(f"Driver '{driver}' not found in race state")

        current_position = driver_state.position
        current_lap = state.current_lap

        # Define pit window
        if earliest_pit is None:
            earliest_pit = current_lap + 1
        if latest_pit is None:
            latest_pit = self.simulator.total_laps - 10

        earliest_pit = max(earliest_pit, current_lap + 1)
        latest_pit = min(latest_pit, self.simulator.total_laps - 3)

        pit_window = range(earliest_pit, latest_pit + 1)

        logger.info(
            f"Optimizing pit stop: {driver} | "
            f"Window: lap {earliest_pit}–{latest_pit} | "
            f"New compound: {new_compound}"
        )

        options = []

        for pit_lap in pit_window:

            # Build pit strategy for this option
            pit_strategy = {driver: {pit_lap: new_compound}}

            # Run simulation with this pit strategy
            import copy

            state_copy = copy.deepcopy(state)
            result = self.simulator.simulate(state_copy, pit_strategy)

            # Get driver's final position
            driver_result = result.final_standings[
                result.final_standings["Driver"] == driver
            ]

            if driver_result.empty:
                continue

            projected_position = int(driver_result["Position"].iloc[0])
            gap_to_leader = float(driver_result["GapToLeader"].iloc[0])

            # Get gap to car ahead and behind
            standings = result.final_standings

            ahead_row = standings[standings["Position"] == projected_position - 1]
            behind_row = standings[standings["Position"] == projected_position + 1]

            gap_to_ahead = (
                gap_to_leader - float(ahead_row["GapToLeader"].iloc[0])
                if not ahead_row.empty
                else 999.0
            )

            gap_to_behind = (
                float(behind_row["GapToLeader"].iloc[0]) - gap_to_leader
                if not behind_row.empty
                else 999.0
            )

            score = self._score_option(
                projected_position,
                abs(gap_to_ahead),
                gap_to_behind,
            )

            options.append(
                PitOption(
                    pit_lap=pit_lap,
                    projected_position=projected_position,
                    gap_to_ahead=round(gap_to_ahead, 3),
                    gap_to_behind=round(gap_to_behind, 3),
                    new_compound=new_compound,
                    score=round(score, 2),
                )
            )

        if not options:
            raise ValueError(f"No valid pit options found for {driver}")

        # Sort by score
        options_sorted = sorted(options, key=lambda x: x.score)
        best_option = options_sorted[0]

        # Build DataFrame of all options
        options_df = pd.DataFrame(
            [
                {
                    "PitLap": o.pit_lap,
                    "ProjectedPos": o.projected_position,
                    "GapToAhead": o.gap_to_ahead,
                    "GapToBehind": o.gap_to_behind,
                    "Compound": o.new_compound,
                    "Score": o.score,
                }
                for o in options_sorted
            ]
        )

        recommendation = (
            f"PIT LAP {best_option.pit_lap} → {new_compound} | "
            f"Projected P{best_option.projected_position} | "
            f"Gap ahead: {best_option.gap_to_ahead:.1f}s | "
            f"Gap behind: {best_option.gap_to_behind:.1f}s"
        )

        logger.success(f"Optimal pit: {driver} — {recommendation}")

        return OptimizationResult(
            driver=driver,
            current_lap=current_lap,
            current_position=current_position,
            optimal_lap=best_option.pit_lap,
            optimal_compound=new_compound,
            all_options=options_df,
            recommendation=recommendation,
        )
