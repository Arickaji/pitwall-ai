"""
PitWall AI — Analytics & Simulation API Schemas
Pydantic models for analytics and simulation endpoints.
"""

from pydantic import BaseModel, Field

# ── Analytics Request Schemas ──────────────────────────────────────────────────


class DegradationRequest(BaseModel):
    year: int = Field(..., example=2024)
    gp: str = Field(..., example="Bahrain Grand Prix")
    session_type: str = Field("R", example="R")
    driver: str | None = Field(None, example="VER")


class PaceRequest(BaseModel):
    year: int = Field(..., example=2024)
    gp: str = Field(..., example="Bahrain Grand Prix")
    session_type: str = Field("R", example="R")
    reference_driver: str | None = Field(None, example="VER")
    compound: str | None = Field(None, example="SOFT")


class UndercutRequest(BaseModel):
    year: int = Field(..., example=2024)
    gp: str = Field(..., example="Bahrain Grand Prix")
    session_type: str = Field("R", example="R")
    lap_number: int = Field(..., example=20)
    laps_remaining: int = Field(..., example=37)


# ── Simulation Request Schemas ─────────────────────────────────────────────────


class MonteCarloRequest(BaseModel):
    year: int = Field(..., example=2024)
    gp: str = Field(..., example="Bahrain Grand Prix")
    session_type: str = Field("R", example="R")
    from_lap: int = Field(..., example=20)
    n_simulations: int = Field(500, ge=100, le=2000, example=500)


class PitOptimizerRequest(BaseModel):
    year: int = Field(..., example=2024)
    gp: str = Field(..., example="Bahrain Grand Prix")
    session_type: str = Field("R", example="R")
    driver: str = Field(..., example="SAI")
    from_lap: int = Field(..., example=20)
    new_compound: str = Field(..., example="SOFT")
    earliest_pit: int | None = Field(None, example=22)
    latest_pit: int | None = Field(None, example=40)


class RaceSimRequest(BaseModel):
    year: int = Field(..., example=2024)
    gp: str = Field(..., example="Bahrain Grand Prix")
    session_type: str = Field("R", example="R")
    from_lap: int = Field(..., example=20)


# ── Response Schemas ───────────────────────────────────────────────────────────


class DegradationRecord(BaseModel):
    driver: str
    compound: str
    stint: float
    laps: int
    degradation_rate: float
    base_pace: float
    r_squared: float
    cliff_lap: float | None


class DegradationResponse(BaseModel):
    status: str = "success"
    data: list[DegradationRecord]
    meta: dict


class PaceRecord(BaseModel):
    driver: str
    median_pace: float
    best_pace: float
    consistency: float
    clean_laps: int
    gap_to_fastest: float


class PaceResponse(BaseModel):
    status: str = "success"
    data: list[PaceRecord]
    meta: dict


class UndercutRecord(BaseModel):
    driver: str
    rival: str
    gap: float
    pace_delta: float
    laps_to_complete: float
    gap_after_stop: float


class UndercutResponse(BaseModel):
    status: str = "success"
    data: list[UndercutRecord]
    meta: dict


class WinProbability(BaseModel):
    driver: str
    win_probability: float
    wins: int


class MonteCarloResponse(BaseModel):
    status: str = "success"
    win_probabilities: list[WinProbability]
    n_simulations: int
    meta: dict


class PitOption(BaseModel):
    pit_lap: int
    projected_position: int
    gap_to_ahead: float
    gap_to_behind: float
    compound: str
    score: float


class PitOptimizerResponse(BaseModel):
    status: str = "success"
    optimal_lap: int
    recommendation: str
    all_options: list[PitOption]
    meta: dict


class FinalStanding(BaseModel):
    driver: str
    position: int
    compound: str
    tyre_age: int
    gap_to_leader: float


class RaceSimResponse(BaseModel):
    status: str = "success"
    winner: str
    final_standings: list[FinalStanding]
    meta: dict
