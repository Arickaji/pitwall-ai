"""
PitWall AI — Visualization Functions
Reusable Plotly chart functions for F1 race analysis.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFD700",
    "HARD": "#CCCCCC",
    "INTER": "#39B54A",
    "WET": "#0067FF",
    "UNKNOWN": "#888888",
}


def plot_lap_times(
    laps: pd.DataFrame,
    drivers: list | None = None,
    title: str | None = None,
    height: int = 500,
) -> go.Figure:
    """
    Plot lap time progression for selected drivers across a race.
    """
    # If no drivers specified, default to top 5 finishers
    if drivers is None:
        drivers = (
            laps.groupby("Driver")["Position"]
            .min()
            .sort_values()
            .head(5)
            .index.tolist()
        )

    # Auto-generate title if not provided
    if title is None:
        title = "Lap Time Progression"

    # Build figure
    fig = go.Figure()

    for driver in drivers:
        driver_laps = laps[laps["Driver"] == driver]

        fig.add_trace(
            go.Scatter(
                x=driver_laps["LapNumber"],
                y=driver_laps["LapTimeSeconds"],
                mode="lines+markers",
                name=driver,
                line={"width": 2},
                marker={"size": 4},
            )
        )

    # Apply layout
    fig.update_layout(
        title=title,
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        template="plotly_dark",
        hovermode="x unified",
        height=height,
    )

    return fig


def plot_compound_distribution(
    laps: pd.DataFrame,
    title: str | None = None,
    height: int = 450,
) -> go.Figure:
    """
    Box plot of lap time distribution by tire compound.

    Box plots are better than bar charts here because they show:
    - Median pace per compound
    - Spread/consistency of each compound
    - Outliers (safety car laps that slipped through)
    """
    if title is None:
        title = "Lap Time Distribution by Compound"

    fig = px.box(
        laps,
        x="Compound",
        y="LapTimeSeconds",
        color="Compound",
        color_discrete_map=COMPOUND_COLORS,
        title=title,
        template="plotly_dark",
        height=height,
    )
    fig.update_layout(showlegend=False)

    return fig


def plot_fastest_laps(
    laps: pd.DataFrame,
    title: str | None = None,
    height: int = 450,
) -> go.Figure:
    """
    Bar chart of each driver's fastest lap time.

    We use idxmin() to find the row with minimum LapTimeSeconds
    per driver — this preserves compound info for that specific lap,
    which a simple .min() aggregation would lose.
    """
    if title is None:
        title = "Fastest Lap per Driver"

    fastest = (
        laps.groupby("Driver")
        .apply(lambda x: x.loc[x["LapTimeSeconds"].idxmin()])
        .reset_index(drop=True)[
            ["Driver", "LapTimeSeconds", "Compound", "LapNumber", "TyreLife"]
        ]
        .sort_values("LapTimeSeconds")
    )

    fig = px.bar(
        fastest,
        x="Driver",
        y="LapTimeSeconds",
        color="Compound",
        color_discrete_map=COMPOUND_COLORS,
        title=title,
        template="plotly_dark",
        height=height,
        text="LapTimeSeconds",
    )
    fig.update_traces(texttemplate="%{text:.2f}s", textposition="outside")
    fig.update_layout(
        yaxis_range=[
            fastest["LapTimeSeconds"].min() - 2,
            fastest["LapTimeSeconds"].max() + 2,
        ]
    )

    return fig


def plot_pace_comparison(
    laps: pd.DataFrame,
    title: str | None = None,
    height: int = 450,
) -> go.Figure:
    """
    Median race pace comparison across all drivers.

    Key analytical decision: we use MEDIAN not MEAN.
    Why? Because mean is sensitive to outliers — one safety car
    lap or slow out-lap massively distorts a driver's average pace.
    Median gives us the true representative lap time for each driver.

    The error bar shows std deviation — this represents consistency.
    A low std = consistent driver/car. High std = lots of variation
    (could mean tire deg, traffic, or aggressive strategy).
    """
    if title is None:
        title = "Median Race Pace by Driver"

    pace = (
        laps.groupby("Driver")["LapTimeSeconds"]
        .agg(["median", "std"])
        .round(3)
        .rename(columns={"median": "MedianPace", "std": "Consistency"})
        .sort_values("MedianPace")
        .reset_index()
    )

    fig = px.bar(
        pace,
        x="Driver",
        y="MedianPace",
        error_y="Consistency",
        title=title,
        labels={"MedianPace": "Median Lap Time (s)"},
        template="plotly_dark",
        height=height,
    )

    return fig
