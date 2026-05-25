"""
PitWall AI — Data API Schemas
Pydantic models for race data request/response validation.
"""

from pydantic import BaseModel

# ── Response Wrapper ───────────────────────────────────────────────────────────


class Meta(BaseModel):
    year: int | None = None
    gp: str | None = None
    session_type: str | None = None
    total_rows: int | None = None
    page: int | None = None
    page_size: int | None = None
    total_pages: int | None = None


class APIResponse(BaseModel):
    status: str = "success"
    data: object
    meta: Meta | None = None


# ── Lap Data Schemas ───────────────────────────────────────────────────────────


class LapRecord(BaseModel):
    driver: str
    lap_number: float | None
    lap_time_seconds: float | None
    compound: str | None
    tyre_life: float | None
    stint: float | None
    position: float | None
    is_accurate: bool | None
    team: str | None
    speed_fl: float | None


class LapDataResponse(BaseModel):
    status: str = "success"
    data: list[LapRecord]
    meta: Meta


# ── Session Schema ─────────────────────────────────────────────────────────────


class SessionInfo(BaseModel):
    year: int
    gp: str
    session_type: str
    total_laps: int
    drivers: list[str]
    compounds: list[str]


class SessionResponse(BaseModel):
    status: str = "success"
    data: SessionInfo
    meta: Meta


# ── Calendar Schema ────────────────────────────────────────────────────────────


class RaceEvent(BaseModel):
    round: int
    gp_name: str


class CalendarResponse(BaseModel):
    status: str = "success"
    data: list[RaceEvent]
    meta: Meta


# ── Telemetry Schema ───────────────────────────────────────────────────────────


class TelemetryRecord(BaseModel):
    distance: float | None
    speed: float | None
    throttle: float | None
    brake: float | None
    rpm: float | None
    gear: int | None
    drs: int | None
    x: float | None
    y: float | None


class TelemetryResponse(BaseModel):
    status: str = "success"
    data: list[TelemetryRecord]
    meta: Meta
