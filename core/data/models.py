"""
PitWall AI — Database Models
SQLAlchemy ORM models for sessions, laps, and telemetry tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


# ── Sessions Table ─────────────────────────────────────────────────────────────


class Session(Base):
    """
    One row per F1 session (Race, Qualifying, Practice etc.)
    This is the top of our data hierarchy.
    """

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year = Column(Integer, nullable=False)
    gp_name = Column(String(100), nullable=False)
    session_type = Column(String(10), nullable=False)
    circuit = Column(String(100), nullable=True)
    date = Column(Date, nullable=True)
    total_laps = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship — one session has many laps
    laps = relationship("Lap", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session {self.year} {self.gp_name} {self.session_type}>"


# ── Laps Table ─────────────────────────────────────────────────────────────────


class Lap(Base):
    """
    One row per driver per lap per session.
    Core fact table for all analytics and ML models.
    """

    __tablename__ = "laps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    driver = Column(String(3), nullable=False)
    team = Column(String(100), nullable=True)
    lap_number = Column(Integer, nullable=False)
    lap_time_seconds = Column(Float, nullable=True)
    stint = Column(Integer, nullable=True)
    compound = Column(String(10), nullable=True)
    tyre_life = Column(Integer, nullable=True)
    fresh_tyre = Column(Boolean, nullable=True)
    position = Column(Integer, nullable=True)
    sector1_seconds = Column(Float, nullable=True)
    sector2_seconds = Column(Float, nullable=True)
    sector3_seconds = Column(Float, nullable=True)
    speed_i1 = Column(Float, nullable=True)
    speed_i2 = Column(Float, nullable=True)
    speed_fl = Column(Float, nullable=True)
    speed_st = Column(Float, nullable=True)
    is_accurate = Column(Boolean, nullable=True)
    is_personal_best = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="laps")

    def __repr__(self):
        return f"<Lap {self.driver} L{self.lap_number} {self.lap_time_seconds}s>"


# ── Telemetry Table ────────────────────────────────────────────────────────────


class Telemetry(Base):
    """
    High frequency car data — one row per telemetry sample.
    Append-only — never updated after write.
    """

    __tablename__ = "telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lap_id = Column(UUID(as_uuid=True), ForeignKey("laps.id"), nullable=False)
    driver = Column(String(3), nullable=False)
    distance = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)
    rpm = Column(Integer, nullable=True)
    gear = Column(Integer, nullable=True)
    throttle = Column(Float, nullable=True)
    brake = Column(Float, nullable=True)
    drs = Column(Integer, nullable=True)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    z = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Telemetry {self.driver} d={self.distance}m s={self.speed}km/h>"


# ── Database Connection ────────────────────────────────────────────────────────


def get_engine(database_url: str):
    """
    Create SQLAlchemy engine from database URL.

    Args:
        database_url: PostgreSQL connection string

    Returns:
        SQLAlchemy engine
    """
    return create_engine(database_url, echo=False)


def create_tables(engine):
    """
    Create all tables in the database.
    Safe to run multiple times — won't recreate existing tables.
    """
    Base.metadata.create_all(engine)
