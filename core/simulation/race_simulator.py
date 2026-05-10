"""
PitWall AI — Core Race Strategy Simulator
Simulates lap-by-lap race progression from any race state.
Foundation of the Phase 4 simulation engine.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from loguru import logger

from core.analytics.degradation import analyze_race_degradation
from core.analytics.pace import get_clean_race_laps

# ── Constants ──────────────────────────────────────────────────────────────────

PIT_STOP_LOSS = 22.0  # seconds lost during pit stop
BASE_LAP_NOISE = 0.1  # random variation in lap times (seconds)


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class DriverState:
    """
    Complete state of one driver at a point in the race.
    This is updated every simulated lap.
    """

    driver: str
    position: int
    compound: str
    tyre_age: int
    base_pace: float  # seconds — pace on fresh tyres
    deg_rate: float  # seconds per lap degradation
    gap_to_leader: float  # seconds behind race leader
    total_time: float  # cumulative race time
    laps_completed: int
    pit_laps: list = field(default_factory=list)
    retired: bool = False


@dataclass
class RaceState:
    """
    Complete state of the race at a given lap.
    Contains all driver states and race metadata.
    """

    current_lap: int
    total_laps: int
    drivers: list[DriverState]
    safety_car: bool = False
    rain: bool = False

    @property
    def laps_remaining(self) -> int:
        return self.total_laps - self.current_lap

    @property
    def leader(self) -> DriverState:
        return min(self.drivers, key=lambda d: d.gap_to_leader)


@dataclass
class SimulationResult:
    """
    Full result of a race simulation.
    Contains lap-by-lap data and final classification.
    """

    initial_lap: int
    total_laps: int
    lap_by_lap: pd.DataFrame  # full simulation data
    final_standings: pd.DataFrame  # final race classification
    pit_stops: dict  # pit stop decisions per driver


# ── Simulator ──────────────────────────────────────────────────────────────────


class RaceSimulator:
    """
    Core race strategy simulator.

    Simulates lap-by-lap race progression from any race state.
    Uses degradation models from Phase 3 analytics.

    Usage:
        simulator = RaceSimulator(laps, total_laps=57)
        state = simulator.build_state_from_lap(20)
        result = simulator.simulate(state)
    """

    def __init__(
        self,
        laps: pd.DataFrame,
        total_laps: int,
        noise: float = BASE_LAP_NOISE,
    ):
        """
        Args:
            laps: Full race lap DataFrame from FastF1
            total_laps: Total race laps
            noise: Random lap time variation in seconds
        """
        self.laps = laps
        self.total_laps = total_laps
        self.noise = noise

        # Pre-compute degradation models
        logger.info("Building degradation models for simulator...")
        self.degradation = analyze_race_degradation(laps)
        self.clean_laps = get_clean_race_laps(laps)
        logger.success("Simulator ready")

    def build_state_from_lap(self, lap_number: int) -> RaceState:
        """
        Build race state from actual race data at a given lap.

        This is the entry point for mid-race simulation —
        take real data up to lap N, simulate the rest.

        Args:
            lap_number: Lap to build state from

        Returns:
            RaceState: Current race state at that lap
        """
        logger.info(f"Building race state from lap {lap_number}")

        lap_data = self.clean_laps[self.clean_laps["LapNumber"] == lap_number].copy()

        if lap_data.empty:
            raise ValueError(f"No data found for lap {lap_number}")

        driver_states = []

        for _, row in lap_data.sort_values("Position").iterrows():
            driver = row["Driver"]

            # Get degradation model for current stint
            driver_deg = self.degradation[self.degradation["Driver"] == driver]

            if driver_deg.empty:
                deg_rate = 0.05  # default
                base_pace = float(row["LapTimeSeconds"])
            else:
                latest_stint = driver_deg.iloc[-1]
                deg_rate = float(latest_stint["DegradationRate"])
                base_pace = float(latest_stint["BasePace"])

            # Calculate cumulative time for gap computation
            driver_laps = self.clean_laps[
                (self.clean_laps["Driver"] == driver)
                & (self.clean_laps["LapNumber"] <= lap_number)
            ]
            total_time = float(driver_laps["LapTimeSeconds"].sum())

            state = DriverState(
                driver=driver,
                position=int(row["Position"]) if pd.notna(row["Position"]) else 99,
                compound=str(row["Compound"]),
                tyre_age=int(row["TyreLife"]) if pd.notna(row["TyreLife"]) else 1,
                base_pace=base_pace,
                deg_rate=max(0.0, deg_rate),
                gap_to_leader=0.0,
                total_time=total_time,
                laps_completed=lap_number,
                pit_laps=[],
            )
            driver_states.append(state)

        # Calculate gaps to leader
        if driver_states:
            leader_time = min(d.total_time for d in driver_states)
            for d in driver_states:
                d.gap_to_leader = round(d.total_time - leader_time, 3)

        race_state = RaceState(
            current_lap=lap_number,
            total_laps=self.total_laps,
            drivers=driver_states,
        )

        logger.success(
            f"Race state built: {len(driver_states)} drivers "
            f"at lap {lap_number}/{self.total_laps}"
        )
        return race_state

    def simulate_lap(
        self,
        state: RaceState,
        pit_decisions: dict = None,
    ) -> RaceState:
        """
        Simulate one lap forward from current state.

        For each driver:
        1. Calculate lap time = base_pace + (deg_rate × tyre_age) + noise
        2. Apply pit stop if scheduled (reset tyre age, add pit loss)
        3. Update gaps and positions

        Args:
            state: Current race state
            pit_decisions: Dict of {driver: new_compound} for drivers pitting

        Returns:
            RaceState: Updated state after one lap
        """
        if pit_decisions is None:
            pit_decisions = {}

        new_lap = state.current_lap + 1

        for driver_state in state.drivers:
            if driver_state.retired:
                continue

            driver = driver_state.driver

            # Calculate lap time with degradation and noise
            deg_contribution = driver_state.deg_rate * driver_state.tyre_age
            noise = np.random.normal(0, self.noise)
            lap_time = driver_state.base_pace + deg_contribution + noise
            lap_time = max(lap_time, driver_state.base_pace * 0.98)

            # Apply pit stop if scheduled
            if driver in pit_decisions:
                new_compound = pit_decisions[driver]
                lap_time += PIT_STOP_LOSS
                driver_state.compound = new_compound
                driver_state.tyre_age = 1
                driver_state.pit_laps.append(new_lap)
                logger.debug(f"Pit stop: {driver} → {new_compound} at lap {new_lap}")
            else:
                driver_state.tyre_age += 1

            # Update cumulative time
            driver_state.total_time += lap_time
            driver_state.laps_completed = new_lap

        # Recalculate gaps and positions
        active = [d for d in state.drivers if not d.retired]
        if active:
            leader_time = min(d.total_time for d in active)
            for d in active:
                d.gap_to_leader = round(d.total_time - leader_time, 3)

            # Sort by total time to get positions
            active_sorted = sorted(active, key=lambda d: d.total_time)
            for i, d in enumerate(active_sorted):
                d.position = i + 1

        state.current_lap = new_lap
        return state

    def simulate(
        self,
        initial_state: RaceState,
        pit_strategy: dict = None,
    ) -> SimulationResult:
        """
        Simulate full race from initial state to finish.

        Args:
            initial_state: Race state to simulate from
            pit_strategy: Dict of {driver: {lap: compound}} pit schedule

        Returns:
            SimulationResult with lap-by-lap data and final standings
        """
        if pit_strategy is None:
            pit_strategy = {}

        logger.info(
            f"Simulating {initial_state.laps_remaining} laps "
            f"from lap {initial_state.current_lap}"
        )

        state = initial_state
        lap_records = []
        pit_stops = {d.driver: [] for d in state.drivers}

        # Simulate lap by lap
        for lap in range(initial_state.current_lap, self.total_laps):

            # Get pit decisions for this lap
            pit_decisions = {}
            for driver, schedule in pit_strategy.items():
                if lap in schedule:
                    pit_decisions[driver] = schedule[lap]

            # Simulate one lap
            state = self.simulate_lap(state, pit_decisions)

            # Record state
            for d in state.drivers:
                lap_records.append(
                    {
                        "Lap": state.current_lap,
                        "Driver": d.driver,
                        "Position": d.position,
                        "Compound": d.compound,
                        "TyreAge": d.tyre_age,
                        "GapToLeader": d.gap_to_leader,
                        "TotalTime": round(d.total_time, 3),
                    }
                )

            # Track pit stops
            for d in state.drivers:
                if state.current_lap in d.pit_laps:
                    pit_stops[d.driver].append(state.current_lap)

        # Build results
        lap_by_lap = pd.DataFrame(lap_records)

        final_standings = (
            lap_by_lap[lap_by_lap["Lap"] == self.total_laps][
                ["Driver", "Position", "Compound", "TyreAge", "GapToLeader"]
            ]
            .sort_values("Position")
            .reset_index(drop=True)
        )

        logger.success(
            f"Simulation complete — Winner: " f"{final_standings['Driver'].iloc[0]}"
        )

        return SimulationResult(
            initial_lap=initial_state.current_lap,
            total_laps=self.total_laps,
            lap_by_lap=lap_by_lap,
            final_standings=final_standings,
            pit_stops=pit_stops,
        )
