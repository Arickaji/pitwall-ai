"""
PitWall AI — Weather Impact Simulation
Models how changing weather conditions affect race strategy.
Integrates with Monte Carlo simulation engine.
"""

from dataclasses import dataclass

import pandas as pd
from loguru import logger

from core.data.f1_loader import load_session

# ── Constants ──────────────────────────────────────────────────────────────────

RAIN_THRESHOLD = 0  # Rainfall > 0 = wet conditions
INTERMEDIATE_TEMP_MAX = 32.0  # Track temp above this = slicks viable
SLICK_TEMP_MIN = 18.0  # Track temp below this = intermediates better
HIGH_DEGRADATION_TEMP = 48.0  # Track temp above this = high deg warning
HUMIDITY_RAIN_THRESHOLD = 85.0  # Humidity above this = rain likely incoming


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class WeatherSnapshot:
    """
    Weather conditions at a specific lap.
    """

    lap: int
    rainfall: float  # mm
    track_temp: float  # °C
    air_temp: float  # °C
    humidity: float  # %
    wind_speed: float  # km/h
    is_wet: bool
    rain_risk: float  # 0-1 probability of rain incoming


@dataclass
class WeatherEvent:
    """
    A significant weather change during a race.
    """

    lap: int
    event_type: str  # 'rain_start', 'rain_stop', 'high_temp', 'rain_risk'
    description: str
    strategic_impact: str


@dataclass
class TyreRecommendation:
    """
    Tyre compound recommendation based on weather.
    """

    lap: int
    compound: str  # SOFT, MEDIUM, HARD, INTER, WET
    reasoning: str
    confidence: float  # 0-1


# ── Weather Data Loader ────────────────────────────────────────────────────────


def load_race_weather(
    year: int,
    gp_name: str,
    session_type: str = "R",
) -> pd.DataFrame:
    """
    Load weather data for a race session.

    FastF1 provides per-lap weather: Rainfall, TrackTemp,
    AirTemp, Humidity, WindSpeed, WindDirection.

    Args:
        year: Championship year
        gp_name: Grand Prix name
        session_type: Session identifier

    Returns:
        pd.DataFrame: Weather data per lap
    """
    logger.info(f"Loading weather data: {year} {gp_name} {session_type}")

    session = load_session(year, gp_name, session_type)
    weather = session.weather_data

    if weather is None or weather.empty:
        logger.warning("No weather data available for this session")
        return pd.DataFrame()

    # FastF1 weather is time-indexed — merge to lap numbers
    weather = weather.reset_index()
    weather.columns = weather.columns.str.strip()

    logger.success(
        f"Weather data loaded: {len(weather)} records | "
        f"Rainfall range: {weather.get('Rainfall', pd.Series([0])).min():.1f}"
        f"–{weather.get('Rainfall', pd.Series([0])).max():.1f}mm"
    )

    return weather


def build_lap_weather(
    year: int,
    gp_name: str,
    session_type: str = "R",
) -> pd.DataFrame:
    """
    Build per-lap weather summary from FastF1 weather data.
    """
    session = load_session(year, gp_name, session_type)
    laps = session.laps
    weather = session.weather_data

    if weather is None or weather.empty:
        logger.warning("No weather data — returning empty DataFrame")
        return pd.DataFrame()

    # Simpler approach — sample weather at equal intervals per lap
    unique_laps = sorted(laps["LapNumber"].dropna().unique())
    n_laps = len(unique_laps)
    n_weather = len(weather)

    weather_records = []

    for i, lap_num in enumerate(unique_laps):
        # Map lap to weather index proportionally
        weather_idx = min(int(i / n_laps * n_weather), n_weather - 1)
        w = weather.iloc[weather_idx]

        rainfall = float(w.get("Rainfall", 0))
        track_temp = float(w.get("TrackTemp", 25))
        air_temp = float(w.get("AirTemp", 20))
        humidity = float(w.get("Humidity", 50))
        wind_speed = float(w.get("WindSpeed", 0))
        is_wet = rainfall > RAIN_THRESHOLD
        rain_risk = min(1.0, humidity / 100 * 1.2) if not is_wet else 0.0

        weather_records.append(
            {
                "LapNumber": int(lap_num),
                "Rainfall": round(rainfall, 2),
                "TrackTemp": round(track_temp, 1),
                "AirTemp": round(air_temp, 1),
                "Humidity": round(humidity, 1),
                "WindSpeed": round(wind_speed, 1),
                "IsWet": is_wet,
                "RainRisk": round(rain_risk, 3),
            }
        )

    df = pd.DataFrame(weather_records).sort_values("LapNumber").reset_index(drop=True)
    logger.success(f"Lap weather built: {len(df)} laps")
    return df


# ── Weather Analysis ───────────────────────────────────────────────────────────


def detect_weather_events(lap_weather: pd.DataFrame) -> list[WeatherEvent]:
    """
    Detect significant weather changes across a race.

    Flags: rain start, rain stop, high track temp, incoming rain risk.

    Args:
        lap_weather: Per-lap weather DataFrame from build_lap_weather()

    Returns:
        List of WeatherEvent objects
    """
    events = []

    for i in range(1, len(lap_weather)):
        current = lap_weather.iloc[i]
        previous = lap_weather.iloc[i - 1]
        lap = int(current["LapNumber"])

        # Rain start
        if current["IsWet"] and not previous["IsWet"]:
            events.append(
                WeatherEvent(
                    lap=lap,
                    event_type="rain_start",
                    description=f"Rain started at lap {lap} ({current['Rainfall']:.1f}mm)",
                    strategic_impact="CRITICAL: Pit for intermediates immediately",
                )
            )

        # Rain stop
        elif not current["IsWet"] and previous["IsWet"]:
            events.append(
                WeatherEvent(
                    lap=lap,
                    event_type="rain_stop",
                    description=f"Rain stopped at lap {lap}",
                    strategic_impact=(
                        "Monitor track temp. Switch to slicks when "
                        f"track temp > {INTERMEDIATE_TEMP_MAX}°C"
                    ),
                )
            )

        # High track temperature warning
        if (
            current["TrackTemp"] > HIGH_DEGRADATION_TEMP
            and previous["TrackTemp"] <= HIGH_DEGRADATION_TEMP
        ):
            events.append(
                WeatherEvent(
                    lap=lap,
                    event_type="high_temp",
                    description=(
                        f"High track temp at lap {lap}: {current['TrackTemp']}°C"
                    ),
                    strategic_impact=(
                        "Soft tyre degradation will be higher than model predicts. "
                        "Consider earlier pit stop."
                    ),
                )
            )

        # Rain risk warning
        if current["RainRisk"] > 0.8 and previous["RainRisk"] <= 0.8:
            events.append(
                WeatherEvent(
                    lap=lap,
                    event_type="rain_risk",
                    description=(
                        f"High rain probability at lap {lap}: "
                        f"Humidity {current['Humidity']:.0f}%"
                    ),
                    strategic_impact=(
                        "Consider pitting for intermediates in next 5 laps. "
                        "Monitor cloud cover."
                    ),
                )
            )

    logger.info(f"Weather events detected: {len(events)}")
    return events


def recommend_tyre_for_conditions(
    track_temp: float,
    rainfall: float,
    humidity: float,
    tyre_age: int,
    laps_remaining: int,
) -> TyreRecommendation:
    """
    Recommend tyre compound based on current weather conditions.

    Decision tree:
    1. Rainfall > 0 → Intermediates
    2. Track temp < 18°C → Intermediates (slicks won't work)
    3. Track temp > 48°C → Hard (SOFT will overheat)
    4. Humidity > 85% + tyre age > 20 → Medium (rain risk + deg)
    5. Otherwise → optimize for laps remaining

    Args:
        track_temp: Current track temperature °C
        rainfall: Current rainfall mm
        humidity: Current humidity %
        tyre_age: Current tyre age in laps
        laps_remaining: Laps remaining in race

    Returns:
        TyreRecommendation dataclass
    """
    # Wet conditions
    if rainfall > RAIN_THRESHOLD:
        return TyreRecommendation(
            lap=0,
            compound="INTER",
            reasoning=f"Rain detected ({rainfall:.1f}mm). Intermediates required.",
            confidence=0.95,
        )

    # Too cold for slicks
    if track_temp < SLICK_TEMP_MIN:
        return TyreRecommendation(
            lap=0,
            compound="INTER",
            reasoning=(
                f"Track temp {track_temp}°C below {SLICK_TEMP_MIN}°C minimum. "
                f"Intermediates generate heat better."
            ),
            confidence=0.80,
        )

    # Very hot — hard tyre to avoid overheating
    if track_temp > HIGH_DEGRADATION_TEMP:
        return TyreRecommendation(
            lap=0,
            compound="HARD",
            reasoning=(
                f"Track temp {track_temp}°C exceeds {HIGH_DEGRADATION_TEMP}°C. "
                f"HARD tyre required to manage degradation."
            ),
            confidence=0.85,
        )

    # Rain risk — conservative choice
    if humidity > HUMIDITY_RAIN_THRESHOLD and tyre_age > 20:
        return TyreRecommendation(
            lap=0,
            compound="MEDIUM",
            reasoning=(
                f"High humidity ({humidity:.0f}%) suggests rain risk. "
                f"MEDIUM balances pace and wet transition flexibility."
            ),
            confidence=0.65,
        )

    # Optimize for laps remaining
    if laps_remaining > 25:
        compound = "HARD"
        reasoning = f"{laps_remaining} laps remaining — HARD for longevity."
        confidence = 0.75
    elif laps_remaining > 12:
        compound = "MEDIUM"
        reasoning = f"{laps_remaining} laps remaining — MEDIUM balances pace and life."
        confidence = 0.75
    else:
        compound = "SOFT"
        reasoning = f"Only {laps_remaining} laps remaining — SOFT for maximum pace."
        confidence = 0.80

    return TyreRecommendation(
        lap=0,
        compound=compound,
        reasoning=reasoning,
        confidence=confidence,
    )


def weather_adjusted_degradation(
    base_deg_rate: float,
    track_temp: float,
    rainfall: float,
) -> float:
    """
    Adjust tyre degradation rate based on weather conditions.

    High track temp increases degradation.
    Wet conditions reduce degradation on inters but increase on slicks.

    Args:
        base_deg_rate: Base degradation rate from Phase 3 model
        track_temp: Current track temperature °C
        rainfall: Current rainfall mm

    Returns:
        float: Adjusted degradation rate
    """
    adjusted = base_deg_rate

    # Temperature adjustment
    if track_temp > HIGH_DEGRADATION_TEMP:
        temp_factor = 1 + (track_temp - HIGH_DEGRADATION_TEMP) * 0.02
        adjusted *= temp_factor

    elif track_temp < SLICK_TEMP_MIN:
        # Cold track — tyres don't work as well
        adjusted *= 1.3

    # Rain adjustment — slicks degrade faster on wet track
    if rainfall > RAIN_THRESHOLD:
        adjusted *= 1.5

    return round(adjusted, 4)
