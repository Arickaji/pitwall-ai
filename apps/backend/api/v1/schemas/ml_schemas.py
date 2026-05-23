"""
PitWall AI — ML Prediction API Schemas
Pydantic models for ML prediction endpoints.
"""

from pydantic import BaseModel, Field

# ── Pit Stop Prediction ────────────────────────────────────────────────────────


class PitPredictionRequest(BaseModel):
    tyre_life: int = Field(..., ge=1, le=60, example=25)
    compound: str = Field(..., example="SOFT")
    position: int = Field(..., ge=1, le=20, example=3)
    gap_ahead: float = Field(..., example=8.5)
    gap_behind: float = Field(..., example=5.2)
    laps_remaining: int = Field(..., ge=1, example=20)
    lap_time: float = Field(..., example=97.5)
    lap_time_trend: float = Field(0.0, example=0.12)
    deg_rate: float = Field(0.05, example=0.065)
    stint: int = Field(1, example=2)
    lap_number: int = Field(20, example=30)
    circuit: str = Field("Bahrain", example="Bahrain")
    speed_fl: float = Field(210.0, example=276.0)


class PitPredictionResponse(BaseModel):
    status: str = "success"
    pit_probability: float
    recommend_pit: bool
    confidence: str
    threshold: float
    meta: dict


# ── Degradation Prediction ─────────────────────────────────────────────────────


class DegradationPredictionRequest(BaseModel):
    tyre_life: int = Field(..., ge=1, le=60, example=20)
    compound: str = Field(..., example="HARD")
    stint: int = Field(1, example=2)
    lap_number: int = Field(20, example=30)
    laps_remaining: int = Field(30, example=20)
    deg_rate: float = Field(0.05, example=0.065)
    position: int = Field(5, example=3)
    speed_fl: float = Field(210.0, example=276.0)


class DegradationPredictionResponse(BaseModel):
    status: str = "success"
    predicted_delta: float
    tyre_life: int
    compound: str
    interpretation: str
    meta: dict


# ── Position Prediction ────────────────────────────────────────────────────────


class PositionPredictionRequest(BaseModel):
    current_position: int = Field(..., ge=1, le=20, example=1)
    laps_remaining: int = Field(..., ge=1, example=20)
    tyre_life: int = Field(..., ge=1, example=15)
    compound: str = Field(..., example="HARD")
    gap_ahead: float = Field(..., example=0.0)
    gap_behind: float = Field(..., example=12.0)
    lap_time: float = Field(..., example=95.5)
    lap_time_trend: float = Field(0.0, example=0.05)
    deg_rate: float = Field(0.05, example=0.06)
    stint: int = Field(2, example=2)


class PositionResult(BaseModel):
    position: int
    probability: float


class PositionPredictionResponse(BaseModel):
    status: str = "success"
    most_likely_position: int
    top5_positions: list[PositionResult]
    current_position: int
    laps_remaining: int
    meta: dict
