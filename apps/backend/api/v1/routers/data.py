"""
PitWall AI — Race Data API Endpoints
Load F1 sessions, lap data, telemetry and calendar.
"""

import math

from fastapi import APIRouter, HTTPException, Query

from apps.backend.api.v1.schemas.data_schemas import (
    CalendarResponse,
    LapDataResponse,
    LapRecord,
    Meta,
    RaceEvent,
    SessionInfo,
    SessionResponse,
    TelemetryRecord,
    TelemetryResponse,
)
from apps.backend.dependencies import get_cached_laps

router = APIRouter()


# ── Calendar ───────────────────────────────────────────────────────────────────


@router.get("/calendar/{year}", response_model=CalendarResponse)
async def get_calendar(year: int):
    """
    Get the full race calendar for a season.

    Returns list of all Grand Prix events with round numbers.
    """
    try:
        import logging

        import fastf1

        logging.getLogger("fastf1").setLevel(logging.WARNING)

        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races = [
            RaceEvent(round=int(row["RoundNumber"]), gp_name=row["EventName"])
            for _, row in schedule.iterrows()
            if row["EventFormat"] != "testing"
        ]

        return CalendarResponse(
            data=races,
            meta=Meta(year=year, total_rows=len(races)),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Session Info ───────────────────────────────────────────────────────────────


@router.get("/sessions/{year}/{gp}/{session_type}", response_model=SessionResponse)
async def get_session_info(year: int, gp: str, session_type: str):
    """
    Get session metadata for a specific race weekend session.

    Returns total laps, drivers, compounds used.
    """
    try:
        laps = get_cached_laps(year, gp, session_type)

        info = SessionInfo(
            year=year,
            gp=gp,
            session_type=session_type,
            total_laps=int(laps["LapNumber"].max()),
            drivers=sorted(laps["Driver"].unique().tolist()),
            compounds=laps["Compound"].dropna().unique().tolist(),
        )

        return SessionResponse(
            data=info,
            meta=Meta(year=year, gp=gp, session_type=session_type),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


# ── Lap Data ───────────────────────────────────────────────────────────────────


@router.get("/laps/{year}/{gp}/{session_type}", response_model=LapDataResponse)
async def get_laps(
    year: int,
    gp: str,
    session_type: str,
    driver: str | None = Query(None, description="Filter by driver code e.g. VER"),
    accurate_only: bool = Query(True, description="Return only accurate laps"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Results per page"),
):
    """
    Get lap data for a session with pagination.

    Supports filtering by driver and accuracy flag.
    Returns 50 laps per page by default.
    """
    try:
        from apps.backend.dependencies import get_cached_laps

        laps = get_cached_laps(year, gp, session_type)
        if driver:
            laps = laps[laps["Driver"] == driver.upper()]

        # Convert timedelta to seconds
        laps = laps.copy()
        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

        # Filter accurate laps
        if accurate_only:
            laps = laps[laps["IsAccurate"]]

        total_rows = len(laps)
        total_pages = math.ceil(total_rows / page_size)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        page_laps = laps.iloc[start:end]

        # Build response
        records = [
            LapRecord(
                driver=row["Driver"],
                lap_number=row.get("LapNumber"),
                lap_time_seconds=row.get("LapTimeSeconds"),
                compound=row.get("Compound"),
                tyre_life=row.get("TyreLife"),
                stint=row.get("Stint"),
                position=row.get("Position"),
                is_accurate=row.get("IsAccurate"),
                team=row.get("Team"),
                speed_fl=row.get("SpeedFL"),
            )
            for _, row in page_laps.iterrows()
        ]

        return LapDataResponse(
            data=records,
            meta=Meta(
                year=year,
                gp=gp,
                session_type=session_type,
                total_rows=total_rows,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


# ── Telemetry ──────────────────────────────────────────────────────────────────


@router.get(
    "/telemetry/{year}/{gp}/{session_type}/{driver}",
    response_model=TelemetryResponse,
)
async def get_telemetry(
    year: int,
    gp: str,
    session_type: str,
    driver: str,
    lap_number: int | None = Query(None, description="Specific lap. None=fastest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=1000),
):
    """
    Get telemetry data for a driver's lap.

    Returns speed, throttle, brake, gear, DRS and track position.
    Defaults to fastest lap if no lap number specified.
    """
    try:
        from core.data.f1_loader import load_telemetry

        tel = load_telemetry(year, gp, session_type, driver, lap_number)

        total_rows = len(tel)
        total_pages = math.ceil(total_rows / page_size)
        start = (page - 1) * page_size
        end = start + page_size
        page_tel = tel.iloc[start:end]

        records = [
            TelemetryRecord(
                distance=row.get("Distance"),
                speed=row.get("Speed"),
                throttle=row.get("Throttle"),
                brake=row.get("Brake"),
                rpm=row.get("RPM"),
                gear=row.get("nGear"),
                drs=row.get("DRS"),
                x=row.get("X"),
                y=row.get("Y"),
            )
            for _, row in page_tel.iterrows()
        ]

        return TelemetryResponse(
            data=records,
            meta=Meta(
                year=year,
                gp=gp,
                session_type=session_type,
                total_rows=total_rows,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
