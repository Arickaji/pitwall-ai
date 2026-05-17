"""
PitWall AI — Telemetry Dashboard Component
Speed, throttle, brake traces and racing line visualization.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from ui.dashboards.theme import PLOTLY_LAYOUT


def render_telemetry(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """
    Render telemetry comparison dashboard.

    Args:
        laps: Full race lap DataFrame
        clean_laps: Filtered accurate laps
        year: Championship year
        gp: Grand Prix name
    """
    st.markdown("### 📡 TELEMETRY ANALYSIS")

    tab1, tab2 = st.tabs(
        [
            "DRIVER COMPARISON",
            "RACING LINE",
        ]
    )

    with tab1:
        _render_telemetry_comparison(laps, year, gp)

    with tab2:
        _render_racing_line(laps, year, gp)


def _render_telemetry_comparison(
    laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Speed, throttle, brake trace comparison."""

    st.markdown("#### Driver Telemetry Comparison")

    drivers = sorted(laps["Driver"].unique().tolist())

    col1, col2, col3 = st.columns(3)

    with col1:
        driver1 = st.selectbox(
            "Driver 1",
            options=drivers,
            index=0,
            key="tel_driver1",
        )
        color1 = "#00D2BE"

    with col2:
        driver2 = st.selectbox(
            "Driver 2",
            options=drivers,
            index=1,
            key="tel_driver2",
        )
        color2 = "#FF1E00"

    with col3:
        lap_option = st.radio(
            "Lap Selection",
            options=["Fastest Lap", "Specific Lap"],
            key="tel_lap_option",
        )
        if lap_option == "Specific Lap":
            lap_number = st.number_input(
                "Lap Number",
                min_value=1,
                max_value=int(laps["LapNumber"].max()),
                value=20,
                key="tel_lap_number",
            )
        else:
            lap_number = None

    if st.button("📡 LOAD TELEMETRY", use_container_width=True):
        with st.spinner("Loading telemetry data..."):
            try:
                from core.data.f1_loader import load_telemetry

                year_val = st.session_state.get("year", year)
                gp_val = st.session_state.get("gp", gp)
                session = st.session_state.get("session_type", "R")

                tel1 = load_telemetry(year_val, gp_val, session, driver1, lap_number)
                tel2 = load_telemetry(year_val, gp_val, session, driver2, lap_number)

                st.session_state["tel1"] = tel1
                st.session_state["tel2"] = tel2
                st.session_state["tel_d1"] = driver1
                st.session_state["tel_d2"] = driver2
                st.session_state["tel_color1"] = color1
                st.session_state["tel_color2"] = color2

            except Exception as e:
                st.error(f"Failed to load telemetry: {e}")

    if "tel1" in st.session_state and "tel2" in st.session_state:
        tel1 = st.session_state["tel1"]
        tel2 = st.session_state["tel2"]
        d1 = st.session_state["tel_d1"]
        d2 = st.session_state["tel_d2"]
        c1 = st.session_state["tel_color1"]
        c2 = st.session_state["tel_color2"]

        # Key metrics comparison
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                f"{d1} Max Speed",
                f"{tel1['Speed'].max():.1f} km/h",
            )
        with col2:
            st.metric(
                f"{d2} Max Speed",
                f"{tel2['Speed'].max():.1f} km/h",
                delta=f"{tel2['Speed'].max() - tel1['Speed'].max():.1f}",
            )
        with col3:
            st.metric(
                f"{d1} Full Throttle",
                f"{(tel1['Throttle'] > 95).mean():.1%}",
            )
        with col4:
            st.metric(
                f"{d2} Full Throttle",
                f"{(tel2['Throttle'] > 95).mean():.1%}",
            )

        # Multi-channel chart
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            subplot_titles=["Speed (km/h)", "Throttle (%)", "Brake (%)"],
            vertical_spacing=0.08,
        )

        channels = [
            ("Speed", 1),
            ("Throttle", 2),
            ("Brake", 3),
        ]

        for channel, row in channels:
            fig.add_trace(
                go.Scatter(
                    x=tel1["Distance"],
                    y=tel1[channel],
                    mode="lines",
                    name=d1,
                    line={"width": 2, "color": c1},
                    showlegend=(row == 1),
                    hovertemplate=(
                        f"<b>{d1}</b><br>"
                        "Distance: %{x:.0f}m<br>"
                        f"{channel}: %{{y:.1f}}<br>"
                        "<extra></extra>"
                    ),
                ),
                row=row,
                col=1,
            )

            fig.add_trace(
                go.Scatter(
                    x=tel2["Distance"],
                    y=tel2[channel],
                    mode="lines",
                    name=d2,
                    line={"width": 2, "color": c2},
                    showlegend=(row == 1),
                    hovertemplate=(
                        f"<b>{d2}</b><br>"
                        "Distance: %{x:.0f}m<br>"
                        f"{channel}: %{{y:.1f}}<br>"
                        "<extra></extra>"
                    ),
                ),
                row=row,
                col=1,
            )

        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=f"{year} {gp} — Telemetry: {d1} vs {d2}",
            hovermode="x unified",
            height=700,
        )

        fig.update_xaxes(
            title_text="Distance (m)",
            row=3,
            col=1,
            gridcolor="#1E1E2E",
        )

        st.plotly_chart(fig, use_container_width=True)


def _render_racing_line(
    laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Racing line X/Y visualization."""

    st.markdown("#### Racing Line Comparison")

    if "tel1" not in st.session_state:
        st.info("Load telemetry data from the Driver Comparison tab first.")
        return

    tel1 = st.session_state["tel1"]
    tel2 = st.session_state["tel2"]
    d1 = st.session_state["tel_d1"]
    d2 = st.session_state["tel_d2"]
    c1 = st.session_state["tel_color1"]
    c2 = st.session_state["tel_color2"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=tel1["X"],
            y=tel1["Y"],
            mode="lines",
            name=d1,
            line={"width": 3, "color": c1},
            hovertemplate=(
                f"<b>{d1}</b><br>" "X: %{x}<br>" "Y: %{y}<br>" "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=tel2["X"],
            y=tel2["Y"],
            mode="lines",
            name=d2,
            line={"width": 3, "color": c2},
            hovertemplate=(
                f"<b>{d2}</b><br>" "X: %{x}<br>" "Y: %{y}<br>" "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=f"{year} {gp} — Racing Line: {d1} vs {d2}",
        height=600,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)

    st.plotly_chart(fig, use_container_width=True)

    # Speed colored racing line for driver 1
    st.markdown(f"#### {d1} — Speed Map")

    fig2 = go.Figure()

    fig2.add_trace(
        go.Scatter(
            x=tel1["X"],
            y=tel1["Y"],
            mode="markers",
            marker={
                "size": 4,
                "color": tel1["Speed"],
                "colorscale": "RdYlGn",
                "showscale": True,
                "colorbar": {"title": "Speed km/h"},
            },
            hovertemplate=(
                f"<b>{d1}</b><br>"
                "Speed: %{marker.color:.1f} km/h<br>"
                "<extra></extra>"
            ),
        )
    )

    fig2.update_layout(
        **PLOTLY_LAYOUT,
        title=f"{d1} — Speed Map",
        height=500,
    )
    fig2.update_yaxes(scaleanchor="x", scaleratio=1)

    st.plotly_chart(fig2, use_container_width=True)
