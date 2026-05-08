# PitWall AI — Data Schema

## Overview

Three core tables following a one-to-many relationship chain:
sessions (1) ──→ (many) laps (1) ──→ (many) telemetry

---

## Table: sessions

Metadata about each F1 race weekend session.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary key |
| `year` | `INTEGER` | No | Championship year |
| `gp_name` | `VARCHAR(100)` | No | Grand Prix name e.g. Bahrain |
| `session_type` | `VARCHAR(10)` | No | R, Q, FP1, FP2, FP3, S, SS |
| `circuit` | `VARCHAR(100)` | Yes | Circuit name |
| `date` | `DATE` | Yes | Session date |
| `total_laps` | `INTEGER` | Yes | Total race laps |
| `created_at` | `TIMESTAMP` | No | Record creation time |

---

## Table: laps

One row per driver per lap per session.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary key |
| `session_id` | `UUID` | No | Foreign key → sessions.id |
| `driver` | `VARCHAR(3)` | No | Driver code e.g. VER |
| `team` | `VARCHAR(100)` | Yes | Constructor name |
| `lap_number` | `INTEGER` | No | Lap number in race |
| `lap_time_seconds` | `FLOAT` | Yes | Lap time in seconds |
| `stint` | `INTEGER` | Yes | Stint number |
| `compound` | `VARCHAR(10)` | Yes | SOFT, MEDIUM, HARD, INTER, WET |
| `tyre_life` | `INTEGER` | Yes | Laps on current tyre set |
| `fresh_tyre` | `BOOLEAN` | Yes | New tyre set |
| `position` | `INTEGER` | Yes | Track position at lap end |
| `sector1_seconds` | `FLOAT` | Yes | Sector 1 time |
| `sector2_seconds` | `FLOAT` | Yes | Sector 2 time |
| `sector3_seconds` | `FLOAT` | Yes | Sector 3 time |
| `speed_i1` | `FLOAT` | Yes | Speed at intermediate 1 |
| `speed_i2` | `FLOAT` | Yes | Speed at intermediate 2 |
| `speed_fl` | `FLOAT` | Yes | Speed at finish line |
| `speed_st` | `FLOAT` | Yes | Speed at speed trap |
| `is_accurate` | `BOOLEAN` | Yes | FastF1 accuracy flag |
| `is_personal_best` | `BOOLEAN` | Yes | Personal best lap flag |
| `created_at` | `TIMESTAMP` | No | Record creation time |

---

## Table: telemetry

High frequency car data — one row per telemetry sample per lap.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary key |
| `lap_id` | `UUID` | No | Foreign key → laps.id |
| `driver` | `VARCHAR(3)` | No | Driver code (denormalized for query speed) |
| `distance` | `FLOAT` | No | Distance from lap start in metres |
| `speed` | `FLOAT` | Yes | Car speed km/h |
| `rpm` | `INTEGER` | Yes | Engine RPM |
| `gear` | `INTEGER` | Yes | Current gear (1-8) |
| `throttle` | `FLOAT` | Yes | Throttle application 0-100% |
| `brake` | `FLOAT` | Yes | Brake pressure 0-100% |
| `drs` | `INTEGER` | Yes | DRS status (0=closed, 10/12=open) |
| `x` | `FLOAT` | Yes | Track X coordinate |
| `y` | `FLOAT` | Yes | Track Y coordinate |
| `z` | `FLOAT` | Yes | Track Z coordinate (elevation) |
| `created_at` | `TIMESTAMP` | No | Record creation time |

---

## Design Decisions

**UUID primary keys** — better than integer sequences for distributed systems
and avoids exposing record counts to API consumers.

**Denormalized driver in telemetry** — querying telemetry by driver without
joining laps table every time. Trade off: slight data duplication for
significant query performance gain.

**Lap times in seconds** — stored as FLOAT not INTERVAL for easier
mathematical operations in analytics and ML models.

**Sector times nullable** — not all laps have complete sector data
(pit laps, red flag laps).

**Telemetry is append-only** — once written, telemetry is never updated.
This makes it suitable for time-series optimized storage in later phases.
