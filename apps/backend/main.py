"""
PitWall AI — FastAPI Application Entry Point
F1 Race Strategy Intelligence Platform API
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

# ── Routers ────────────────────────────────────────────────────────────────────
from apps.backend.api.v1.routers import analytics, data, predictions, simulation
from apps.backend.config import settings

# ── Application ────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## PitWall AI — F1 Race Strategy Intelligence API

    Real-world Formula 1 race strategy intelligence platform.

    ### Features
    - **Race Data** — Load F1 sessions, lap data, telemetry
    - **Analytics** — Degradation modeling, pace comparison, stint analysis
    - **Simulation** — Monte Carlo race simulation, pit optimization
    - **ML Predictions** — Pit stop probability, position forecasting

    ### Data Source
    FastF1 — Official F1 timing data (2018–2024)
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error Handlers ─────────────────────────────────────────────────────────────


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid input", "detail": str(exc)},
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    logger.warning(f"FileNotFoundError: {exc}")
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "detail": str(exc)},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    logger.error(f"RuntimeError: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ── Health Check ───────────────────────────────────────────────────────────────


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns API status and version.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "name": settings.app_name,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_prefix,
    }


app.include_router(data.router, prefix=settings.api_prefix, tags=["Race Data"])
app.include_router(analytics.router, prefix=settings.api_prefix, tags=["Analytics"])
app.include_router(simulation.router, prefix=settings.api_prefix, tags=["Simulation"])
app.include_router(
    predictions.router, prefix=settings.api_prefix, tags=["ML Predictions"]
)


# ── Startup ────────────────────────────────────────────────────────────────────


@app.on_event("startup")
async def startup_event():
    logger.info(f"PitWall AI API starting — v{settings.app_version}")
    logger.info("Docs available at: http://localhost:8000/docs")
