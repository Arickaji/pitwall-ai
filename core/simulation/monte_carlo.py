"""
PitWall AI — Monte Carlo Race Simulation
Runs thousands of race simulations with random variation to produce
probability distributions of race outcomes.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from loguru import logger

from core.simulation.race_simulator import RaceSimulator, RaceState

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_SIMULATIONS = 1000
RETIREMENT_PROB_PER_LAP = 0.0005  # 0.05% per lap
DEG_VARIATION = 0.20  # ±20% degradation rate variation
LAP_TIME_STD = 0.3  # seconds standard deviation per lap


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class MonteCarloResult:
    """
    Full result of Monte Carlo race simulation.

    n_simulations:      Number of simulations run
    win_probabilities:  Win probability per driver
    position_distribution: Probability of each position per driver
    avg_gaps:          Average finishing gap per driver
    retirement_rates:  Retirement probability per driver
    """

    n_simulations: int
    win_probabilities: pd.DataFrame
    position_distribution: pd.DataFrame
    avg_gaps: pd.DataFrame
    retirement_rates: pd.DataFrame


# ── Monte Carlo Engine ─────────────────────────────────────────────────────────


class MonteCarloSimulator:
    """
    Monte Carlo race simulation engine.

    Runs N simulations with randomized:
    - Lap time variation (driver mistakes, traffic)
    - Tyre degradation rate variation
    - Random retirements

    Usage:
        mc = MonteCarloSimulator(simulator)
        result = mc.run(state, n_simulations=1000)
    """

    def __init__(
        self,
        simulator: RaceSimulator,
        retirement_prob: float = RETIREMENT_PROB_PER_LAP,
        deg_variation: float = DEG_VARIATION,
        lap_time_std: float = LAP_TIME_STD,
    ):
        """
        Args:
            simulator:       Initialized RaceSimulator
            retirement_prob: Probability of retirement per lap per driver
            deg_variation:   Fractional variation in degradation rate
            lap_time_std:    Standard deviation of lap time noise
        """
        self.simulator = simulator
        self.retirement_prob = retirement_prob
        self.deg_variation = deg_variation
        self.lap_time_std = lap_time_std
        logger.debug("MonteCarloSimulator initialized")

    def _randomize_state(self, state: RaceState) -> RaceState:
        """
        Apply random variation to race state for one simulation.

        Varies degradation rates within ±deg_variation and
        adjusts base pace slightly for each driver.

        Args:
            state: Base race state

        Returns:
            RaceState: Randomized copy of state
        """
        import copy

        randomized = copy.deepcopy(state)

        for driver in randomized.drivers:
            # Vary degradation rate ±20%
            variation = np.random.uniform(
                1 - self.deg_variation, 1 + self.deg_variation
            )
            driver.deg_rate = max(0.0, driver.deg_rate * variation)

            # Slight base pace variation ±0.2s
            driver.base_pace += np.random.normal(0, 0.2)

        return randomized

    def _simulate_one(
        self,
        state: RaceState,
        pit_strategy: dict,
    ) -> dict:
        """
        Run one Monte Carlo simulation with randomized inputs.

        Also applies random retirements during simulation.

        Args:
            state: Randomized race state
            pit_strategy: Pit stop schedule

        Returns:
            dict: Final positions and retirement info
        """
        import copy

        state_copy = copy.deepcopy(state)
        total_laps = self.simulator.total_laps

        # Track retirements
        retirements = {}

        for lap in range(state_copy.current_lap, total_laps):

            # Check retirements
            for driver in state_copy.drivers:
                if driver.retired:
                    continue
                if np.random.random() < self.retirement_prob:
                    driver.retired = True
                    retirements[driver.driver] = lap

            # Get pit decisions
            pit_decisions = {}
            for drv, schedule in pit_strategy.items():
                if lap in schedule:
                    pit_decisions[drv] = schedule[lap]

            # Simulate lap with noise
            state_copy = self.simulator.simulate_lap(state_copy, pit_decisions)

        # Collect results
        results = {}
        for driver in state_copy.drivers:
            results[driver.driver] = {
                "position": driver.position if not driver.retired else 99,
                "gap": driver.gap_to_leader,
                "retired": driver.retired,
                "retired_lap": retirements.get(driver.driver),
            }

        return results

    def run(
        self,
        state: RaceState,
        n_simulations: int = DEFAULT_SIMULATIONS,
        pit_strategy: dict = None,
        seed: int | None = None,
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation.

        Args:
            state:          Current race state
            n_simulations:  Number of simulations to run
            pit_strategy:   Optional pit stop schedule
            seed:           Random seed for reproducibility

        Returns:
            MonteCarloResult with probability distributions
        """
        if pit_strategy is None:
            pit_strategy = {}

        if seed is not None:
            np.random.seed(seed)

        drivers = [d.driver for d in state.drivers]

        logger.info(
            f"Running {n_simulations} Monte Carlo simulations | "
            f"{len(drivers)} drivers | "
            f"{state.laps_remaining} laps remaining"
        )

        # Store results
        all_positions = {d: [] for d in drivers}
        all_gaps = {d: [] for d in drivers}
        all_retirements = {d: 0 for d in drivers}

        for i in range(n_simulations):
            # Randomize state for this simulation
            randomized_state = self._randomize_state(state)

            # Run simulation
            sim_result = self._simulate_one(randomized_state, pit_strategy)

            # Collect results
            for driver, result in sim_result.items():
                all_positions[driver].append(result["position"])
                all_gaps[driver].append(result["gap"])
                if result["retired"]:
                    all_retirements[driver] += 1

            # Progress logging
            if (i + 1) % 250 == 0:
                logger.debug(f"Completed {i + 1}/{n_simulations} simulations")

        # ── Win Probabilities ──────────────────────────────────────────────────
        win_probs = []
        for driver in drivers:
            wins = sum(1 for p in all_positions[driver] if p == 1)
            win_probs.append(
                {
                    "Driver": driver,
                    "WinProbability": round(wins / n_simulations * 100, 1),
                    "Wins": wins,
                }
            )

        win_df = (
            pd.DataFrame(win_probs)
            .sort_values("WinProbability", ascending=False)
            .reset_index(drop=True)
        )

        # ── Position Distribution ──────────────────────────────────────────────
        position_records = []
        for driver in drivers:
            positions = all_positions[driver]
            for pos in range(1, len(drivers) + 1):
                prob = sum(1 for p in positions if p == pos) / n_simulations
                position_records.append(
                    {
                        "Driver": driver,
                        "Position": pos,
                        "Probability": round(prob * 100, 1),
                    }
                )

        position_df = pd.DataFrame(position_records)

        # ── Average Gaps ───────────────────────────────────────────────────────
        avg_gaps_records = []
        for driver in drivers:
            gaps = [g for g in all_gaps[driver] if g < 900]
            avg_gaps_records.append(
                {
                    "Driver": driver,
                    "AvgGap": round(np.mean(gaps), 3) if gaps else 999.0,
                    "StdGap": round(np.std(gaps), 3) if gaps else 0.0,
                    "MinGap": round(np.min(gaps), 3) if gaps else 0.0,
                    "MaxGap": round(np.max(gaps), 3) if gaps else 0.0,
                }
            )

        avg_gaps_df = (
            pd.DataFrame(avg_gaps_records).sort_values("AvgGap").reset_index(drop=True)
        )

        # ── Retirement Rates ───────────────────────────────────────────────────
        retirement_df = (
            pd.DataFrame(
                [
                    {
                        "Driver": d,
                        "Retirements": all_retirements[d],
                        "RetirementRate": round(
                            all_retirements[d] / n_simulations * 100, 1
                        ),
                    }
                    for d in drivers
                ]
            )
            .sort_values("RetirementRate", ascending=False)
            .reset_index(drop=True)
        )

        logger.success(
            f"Monte Carlo complete — {n_simulations} simulations | "
            f"Most likely winner: {win_df['Driver'].iloc[0]} "
            f"({win_df['WinProbability'].iloc[0]}%)"
        )

        return MonteCarloResult(
            n_simulations=n_simulations,
            win_probabilities=win_df,
            position_distribution=position_df,
            avg_gaps=avg_gaps_df,
            retirement_rates=retirement_df,
        )
