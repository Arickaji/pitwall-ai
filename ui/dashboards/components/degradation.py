"""
PitWall AI — Tire Degradation Dashboard Component
Degradation curves, ML predictions, compound comparison.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.analytics.degradation import analyze_race_degradation
from ui.dashboards.theme import COMPOUND_COLORS, PLOTLY_LAYOUT


def render_degradation(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """
    Render tire degradation dashboard.

    Args:
        laps: Full race lap DataFrame
        clean_laps: Filtered accurate laps
        year: Championship year
        gp: Grand Prix name
    """
    st.markdown("### 🏎️ TYRE DEGRADATION ANALYSIS")

    tab1, tab2, tab3 = st.tabs(
        [
            "DEGRADATION CURVES",
            "COMPOUND COMPARISON",
            "ML PREDICTION",
        ]
    )

    with tab1:
        _render_degradation_curves(laps, clean_laps, year, gp)

    with tab2:
        _render_compound_comparison(clean_laps, year, gp)

    with tab3:
        _render_ml_prediction(clean_laps, year, gp)


def _render_degradation_curves(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Degradation curves per driver per stint."""

    st.markdown("#### Lap Time vs Tyre Life")

    drivers = sorted(clean_laps["Driver"].unique().tolist())
    selected = st.multiselect(
        "Select Drivers",
        options=drivers,
        default=drivers[:3],
        key="deg_drivers",
    )

    if not selected:
        st.warning("Select at least one driver")
        return

    # Get degradation models
    degradation = analyze_race_degradation(laps)

    fig = go.Figure()
    colors = px.colors.qualitative.Set1

    for i, driver in enumerate(selected):
        driver_laps = clean_laps[clean_laps["Driver"] == driver]
        color = colors[i % len(colors)]

        for stint_num, stint_laps in driver_laps.groupby("Stint"):
            compound = stint_laps["Compound"].iloc[0]

            # Actual lap times
            fig.add_trace(
                go.Scatter(
                    x=stint_laps["TyreLife"],
                    y=stint_laps["LapTimeSeconds"],
                    mode="markers",
                    name=f"{driver} S{int(stint_num)} ({compound})",
                    marker={
                        "size": 6,
                        "color": color,
                        "symbol": "circle",
                    },
                    hovertemplate=(
                        f"<b>{driver} Stint {int(stint_num)}</b><br>"
                        "Tyre Life: %{x} laps<br>"
                        "Lap Time: %{y:.3f}s<br>"
                        f"Compound: {compound}<br>"
                        "<extra></extra>"
                    ),
                )
            )

            # Regression line from degradation model
            driver_deg = degradation[
                (degradation["Driver"] == driver)
                & (degradation["Stint"] == float(stint_num))
            ]

            if not driver_deg.empty:
                deg_rate = float(driver_deg["DegradationRate"].iloc[0])
                base_pace = float(driver_deg["BasePace"].iloc[0])
                cliff_lap = driver_deg["CliffLap"].iloc[0]

                x_range = np.linspace(
                    stint_laps["TyreLife"].min(),
                    stint_laps["TyreLife"].max(),
                    50,
                )
                y_pred = base_pace + deg_rate * x_range

                fig.add_trace(
                    go.Scatter(
                        x=x_range,
                        y=y_pred,
                        mode="lines",
                        name=f"{driver} S{int(stint_num)} trend",
                        line={"width": 1.5, "color": color, "dash": "dash"},
                        showlegend=False,
                        hovertemplate=(
                            f"<b>{driver} Trend</b><br>"
                            f"Rate: {deg_rate:.4f}s/lap<br>"
                            "<extra></extra>"
                        ),
                    )
                )

                # Cliff marker
                if pd.notna(cliff_lap):
                    cliff_time = base_pace + deg_rate * float(cliff_lap)
                    fig.add_trace(
                        go.Scatter(
                            x=[cliff_lap],
                            y=[cliff_time],
                            mode="markers",
                            marker={
                                "size": 12,
                                "color": "#FF1E00",
                                "symbol": "x",
                            },
                            name=f"{driver} cliff",
                            showlegend=False,
                            hovertemplate=(
                                f"<b>⚠️ CLIFF: {driver}</b><br>"
                                f"Tyre Life: {cliff_lap} laps<br>"
                                "<extra></extra>"
                            ),
                        )
                    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=f"{year} {gp} — Tyre Degradation Curves",
        xaxis_title="Tyre Life (laps)",
        yaxis_title="Lap Time (seconds)",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Degradation table
    st.markdown("#### Degradation Rates")
    deg_filtered = degradation[degradation["Driver"].isin(selected)][
        [
            "Driver",
            "Stint",
            "Compound",
            "Laps",
            "DegradationRate",
            "RSquared",
            "CliffLap",
        ]
    ]

    st.dataframe(
        deg_filtered.round(4),
        use_container_width=True,
        hide_index=True,
    )


def _render_compound_comparison(
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Lap time distribution by compound."""

    st.markdown("#### Compound Performance Comparison")

    col1, col2 = st.columns(2)

    with col1:
        # Box plot
        fig_box = px.box(
            clean_laps,
            x="Compound",
            y="LapTimeSeconds",
            color="Compound",
            color_discrete_map=COMPOUND_COLORS,
            title="Lap Time Distribution by Compound",
            template="plotly_dark",
            height=400,
        )
        fig_box.update_layout(**PLOTLY_LAYOUT)
        fig_box.update_layout(showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    with col2:
        # Compound summary stats
        compound_stats = (
            clean_laps.groupby("Compound")["LapTimeSeconds"]
            .agg(
                MedianPace="median",
                BestPace="min",
                Consistency="std",
                Laps="count",
            )
            .round(3)
            .reset_index()
            .sort_values("MedianPace")
        )

        st.markdown("##### Compound Statistics")
        st.dataframe(
            compound_stats,
            use_container_width=True,
            hide_index=True,
        )

        # Tyre life vs lap time scatter
        fig_scatter = px.scatter(
            clean_laps,
            x="TyreLife",
            y="LapTimeSeconds",
            color="Compound",
            color_discrete_map=COMPOUND_COLORS,
            title="Tyre Age vs Lap Time",
            template="plotly_dark",
            height=300,
            opacity=0.6,
        )
        fig_scatter.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_scatter, use_container_width=True)


def _render_ml_prediction(
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """ML degradation model predictions."""

    st.markdown("#### ML Tyre Degradation Predictor")

    col1, col2 = st.columns(2)

    with col1:
        tyre_life = st.slider("Tyre Age (laps)", 1, 50, 20, key="ml_tyre_life")
        compound = st.selectbox(
            "Compound",
            options=["SOFT", "MEDIUM", "HARD"],
            key="ml_compound",
        )
        stint = st.slider("Stint Number", 1, 3, 2, key="ml_stint")

    with col2:
        laps_remaining = st.slider("Laps Remaining", 1, 60, 20, key="ml_laps_remaining")
        deg_rate = st.slider(
            "Degradation Rate (s/lap)",
            0.01,
            0.20,
            0.065,
            step=0.005,
            key="ml_deg_rate",
        )

    if st.button("🤖 PREDICT DEGRADATION", use_container_width=True):
        try:
            from core.ml.degradation_model import predict_lap_delta

            result = predict_lap_delta(
                tyre_life=tyre_life,
                compound=compound,
                stint=stint,
                laps_remaining=laps_remaining,
                deg_rate=deg_rate,
            )

            delta = result["predicted_delta"]
            interpretation = result["interpretation"]

            color = (
                "#00FF87"
                if delta < 0.5
                else (
                    "#FFB800"
                    if delta < 1.5
                    else "#FF8C00" if delta < 3.0 else "#FF1E00"
                )
            )

            st.markdown(
                f"""
            <div style='background: #12121A; border: 1px solid {color};
                        border-radius: 8px; padding: 20px; text-align: center;
                        margin-top: 16px;'>
                <h2 style='color: {color}; font-family: monospace; margin: 0;'>
                    +{delta:.3f}s
                </h2>
                <p style='color: #8B8B9E; margin: 8px 0 0 0;
                           font-family: monospace;'>
                    ABOVE FRESH TYRE PACE
                </p>
                <p style='color: {color}; margin: 8px 0 0 0;'>
                    {interpretation}
                </p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Show degradation curve for next 20 laps
            future_laps = list(range(tyre_life, min(tyre_life + 20, 60)))
            future_deltas = []

            for fl in future_laps:
                r = predict_lap_delta(
                    tyre_life=fl,
                    compound=compound,
                    stint=stint,
                    laps_remaining=max(1, laps_remaining - (fl - tyre_life)),
                    deg_rate=deg_rate,
                )
                future_deltas.append(r["predicted_delta"])

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=future_laps,
                    y=future_deltas,
                    mode="lines+markers",
                    line={"color": color, "width": 2},
                    marker={"size": 4},
                    name="Predicted Delta",
                )
            )

            fig.add_vline(
                x=tyre_life,
                line_dash="dash",
                line_color="#00D2BE",
                annotation_text="NOW",
                annotation_font_color="#00D2BE",
            )

            fig.update_layout(
                **PLOTLY_LAYOUT,
                title="Predicted Degradation — Next 20 Laps",
                xaxis_title="Tyre Life (laps)",
                yaxis_title="Delta from Fresh Pace (s)",
                height=300,
            )

            st.plotly_chart(fig, use_container_width=True)

        except FileNotFoundError:
            st.warning(
                "ML model not trained yet. "
                'Run `python -c "from core.ml.degradation_model import '
                'train_degradation_model; train_degradation_model()"`'
            )
        except Exception as e:
            st.error(f"Prediction failed: {e}")
