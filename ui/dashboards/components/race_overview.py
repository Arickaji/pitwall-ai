"""
PitWall AI — Race Overview Dashboard Component
Lap times, positions, compounds, and race progression.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui.dashboards.theme import (
    COMPOUND_COLORS,
    PLOTLY_LAYOUT,
    format_lap_time,
)


def render_race_overview(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """
    Render full race overview dashboard.

    Args:
        laps: Full race lap DataFrame
        clean_laps: Filtered accurate laps
        year: Championship year
        gp: Grand Prix name
    """
    # ── Key Metrics Row ────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    total_laps = int(laps["LapNumber"].max())
    n_drivers = laps["Driver"].nunique()
    fastest_lap = clean_laps.loc[clean_laps["LapTimeSeconds"].idxmin()]
    compounds = clean_laps["Compound"].unique().tolist()

    with col1:
        st.metric("TOTAL LAPS", total_laps)
    with col2:
        st.metric("DRIVERS", n_drivers)
    with col3:
        st.metric(
            "FASTEST LAP",
            format_lap_time(fastest_lap["LapTimeSeconds"]),
            delta=fastest_lap["Driver"],
        )
    with col4:
        st.metric("COMPOUNDS USED", len(compounds))

    st.markdown("---")

    # ── Driver selector ────────────────────────────────────────────────────────
    all_drivers = sorted(laps["Driver"].unique().tolist())

    col_left, col_right = st.columns([2, 1])

    with col_left:
        selected_drivers = st.multiselect(
            "SELECT DRIVERS",
            options=all_drivers,
            default=all_drivers[:5],
            help="Select drivers to display on charts",
        )

    with col_right:
        chart_type = st.radio(
            "CHART MODE",
            options=["Lap Time", "Position"],
            horizontal=True,
        )

    if not selected_drivers:
        st.warning("Select at least one driver")
        return

    # ── Main Chart ─────────────────────────────────────────────────────────────
    if chart_type == "Lap Time":
        fig = _render_lap_time_chart(clean_laps, selected_drivers, year, gp)
    else:
        fig = _render_position_chart(laps, selected_drivers, year, gp)

    st.plotly_chart(fig, use_container_width=True)

    # ── Stint Strategy ─────────────────────────────────────────────────────────
    st.markdown("### 🏎️ STINT STRATEGY")
    fig_strategy = _render_strategy_chart(clean_laps, selected_drivers, year, gp)
    st.plotly_chart(fig_strategy, use_container_width=True)

    # ── Race Summary Table ─────────────────────────────────────────────────────
    st.markdown("### 📊 RACE SUMMARY")
    summary = _build_race_summary(clean_laps)
    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
    )


def _render_lap_time_chart(
    laps: pd.DataFrame,
    drivers: list,
    year: int,
    gp: str,
) -> go.Figure:
    """Lap time progression chart."""
    fig = go.Figure()

    colors = px.colors.qualitative.Set1

    for i, driver in enumerate(drivers):
        driver_laps = laps[laps["Driver"] == driver]
        color = colors[i % len(colors)]

        fig.add_trace(
            go.Scatter(
                x=driver_laps["LapNumber"],
                y=driver_laps["LapTimeSeconds"],
                mode="lines",
                name=driver,
                line={"width": 2, "color": color},
                hovertemplate=(
                    f"<b>{driver}</b><br>"
                    "Lap %{x}<br>"
                    "Time: %{y:.3f}s<br>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=f"{year} {gp} — Lap Time Progression",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        hovermode="x unified",
        height=450,
    )

    return fig


def _render_position_chart(
    laps: pd.DataFrame,
    drivers: list,
    year: int,
    gp: str,
) -> go.Figure:
    """Race position changes chart."""
    fig = go.Figure()

    colors = px.colors.qualitative.Set1

    for i, driver in enumerate(drivers):
        driver_laps = laps[(laps["Driver"] == driver) & laps["Position"].notna()]
        color = colors[i % len(colors)]

        fig.add_trace(
            go.Scatter(
                x=driver_laps["LapNumber"],
                y=driver_laps["Position"],
                mode="lines",
                name=driver,
                line={"width": 2, "color": color},
                hovertemplate=(
                    f"<b>{driver}</b><br>"
                    "Lap %{x}<br>"
                    "Position: P%{y}<br>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=f"{year} {gp} — Position Changes",
        xaxis_title="Lap Number",
        hovermode="x unified",
        height=450,
    )
    # Update yaxis separately to avoid conflict with PLOTLY_LAYOUT
    fig.update_yaxes(
        autorange="reversed",
        tickvals=list(range(1, 21)),
        gridcolor="#1E1E2E",
        title="Position",
    )

    return fig


def _render_strategy_chart(
    laps: pd.DataFrame,
    drivers: list,
    year: int,
    gp: str,
) -> go.Figure:
    """Horizontal bar chart showing stint strategy per driver."""
    fig = go.Figure()

    filtered = laps[laps["Driver"].isin(drivers)]

    for driver in drivers:
        driver_laps = filtered[filtered["Driver"] == driver]

        for _, stint_group in driver_laps.groupby("Stint"):
            compound = stint_group["Compound"].iloc[0]
            start_lap = int(stint_group["LapNumber"].min())
            end_lap = int(stint_group["LapNumber"].max())
            color = COMPOUND_COLORS.get(compound, "#888888")

            fig.add_trace(
                go.Bar(
                    name=compound,
                    y=[driver],
                    x=[end_lap - start_lap + 1],
                    base=start_lap - 1,
                    orientation="h",
                    marker_color=color,
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{driver}</b><br>"
                        f"Compound: {compound}<br>"
                        f"Laps: {start_lap}–{end_lap}<br>"
                        f"Stint length: {end_lap - start_lap + 1}<br>"
                        "<extra></extra>"
                    ),
                )
            )

    # Add compound legend manually
    for compound, color in COMPOUND_COLORS.items():
        if compound in laps["Compound"].values:
            fig.add_trace(
                go.Bar(
                    name=compound,
                    y=[None],
                    x=[None],
                    marker_color=color,
                    showlegend=True,
                )
            )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=f"{year} {gp} — Stint Strategy",
        xaxis_title="Lap Number",
        barmode="stack",
        height=max(300, len(drivers) * 40 + 100),
    )

    return fig


def _build_race_summary(laps: pd.DataFrame) -> pd.DataFrame:
    """Build race summary statistics table."""
    summary = (
        laps.groupby("Driver")
        .agg(
            MedianPace=("LapTimeSeconds", "median"),
            BestLap=("LapTimeSeconds", "min"),
            CleanLaps=("LapTimeSeconds", "count"),
            Stints=("Stint", "nunique"),
        )
        .round(3)
        .reset_index()
        .sort_values("MedianPace")
    )

    summary.index = range(1, len(summary) + 1)
    summary.index.name = "Pos"

    return summary
