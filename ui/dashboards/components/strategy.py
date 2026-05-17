"""
PitWall AI — Strategy Dashboard Component
Undercut opportunities, pit windows, gap evolution.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.analytics.stint import analyze_stints, compare_stint_strategies
from core.analytics.strategy import scan_undercut_opportunities
from core.analytics.trends import calculate_gap_evolution
from ui.dashboards.theme import COMPOUND_COLORS, PLOTLY_LAYOUT


def render_strategy(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """
    Render strategy analysis dashboard.

    Args:
        laps: Full race lap DataFrame
        clean_laps: Filtered accurate laps
        year: Championship year
        gp: Grand Prix name
    """
    st.markdown("### 🎯 STRATEGY ANALYSIS")

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(
        [
            "GAP EVOLUTION",
            "STINT STRATEGY",
            "UNDERCUT SCANNER",
        ]
    )

    with tab1:
        _render_gap_evolution(laps, clean_laps, year, gp)

    with tab2:
        _render_stint_strategy(laps, clean_laps, year, gp)

    with tab3:
        _render_undercut_scanner(laps, clean_laps, year, gp)


def _render_gap_evolution(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Gap evolution between two selected drivers."""

    st.markdown("#### Gap Evolution Between Drivers")

    drivers = sorted(laps["Driver"].unique().tolist())

    col1, col2 = st.columns(2)
    with col1:
        driver_ahead = st.selectbox(
            "Driver Ahead",
            options=drivers,
            index=0,
            key="gap_ahead",
        )
    with col2:
        driver_behind = st.selectbox(
            "Driver Behind",
            options=drivers,
            index=1,
            key="gap_behind",
        )

    if driver_ahead == driver_behind:
        st.warning("Select two different drivers")
        return

    try:
        gaps = calculate_gap_evolution(laps, driver_ahead, driver_behind)

        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Final Gap",
                f"{gaps['CumulativeGap'].iloc[-1]:.3f}s",
            )
        with col2:
            st.metric(
                "Max Gap",
                f"{gaps['CumulativeGap'].max():.3f}s",
            )
        with col3:
            trend = gaps["LapDelta"].tail(5).mean()
            st.metric(
                "Recent Trend",
                f"{trend:+.3f}s/lap",
                delta="closing" if trend < 0 else "opening",
            )

        # Gap chart
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=gaps["LapNumber"],
                y=gaps["CumulativeGap"],
                mode="lines",
                name="Cumulative Gap",
                line={"width": 2, "color": "#00D2BE"},
                fill="tozeroy",
                fillcolor="rgba(0, 210, 190, 0.1)",
                hovertemplate=("Lap %{x}<br>" "Gap: %{y:.3f}s<br>" "<extra></extra>"),
            )
        )

        # Zero line
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="#FF1E00",
            annotation_text="OVERTAKE LINE",
            annotation_font_color="#FF1E00",
        )

        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=f"{driver_ahead} vs {driver_behind} — Gap Evolution",
            xaxis_title="Lap Number",
            yaxis_title="Gap (seconds)",
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Could not calculate gap evolution: {e}")


def _render_stint_strategy(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Stint strategy comparison table and chart."""

    st.markdown("#### Stint Strategy Comparison")

    try:
        strategies = compare_stint_strategies(laps)
        stints = analyze_stints(laps)

        # Strategy table
        st.dataframe(
            strategies,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Degradation Rate by Stint")

        # Top drivers selector
        drivers = sorted(laps["Driver"].unique().tolist())
        selected = st.multiselect(
            "Select Drivers",
            options=drivers,
            default=drivers[:5],
            key="stint_drivers",
        )

        if selected:
            filtered_stints = stints[stints["Driver"].isin(selected)]

            fig = px.bar(
                filtered_stints,
                x="Driver",
                y="DegradationRate",
                color="Compound",
                color_discrete_map=COMPOUND_COLORS,
                barmode="group",
                title="Degradation Rate by Driver and Compound",
                template="plotly_dark",
                height=400,
            )
            fig.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Could not analyze stints: {e}")


def _render_undercut_scanner(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Undercut opportunity scanner at selected lap."""

    st.markdown("#### Undercut Opportunity Scanner")

    total_laps = int(laps["LapNumber"].max())
    scan_lap = st.slider(
        "Scan at Lap",
        min_value=5,
        max_value=total_laps - 5,
        value=total_laps // 2,
        key="undercut_lap",
    )

    laps_remaining = total_laps - scan_lap

    if st.button("🔍 SCAN FOR OPPORTUNITIES", use_container_width=True):
        with st.spinner("Scanning field for undercut opportunities..."):
            try:
                opportunities = scan_undercut_opportunities(
                    laps,
                    lap_number=scan_lap,
                    laps_remaining=laps_remaining,
                )

                if opportunities.empty:
                    st.info(f"No undercut opportunities at lap {scan_lap}")
                else:
                    st.success(
                        f"Found {len(opportunities)} undercut opportunities "
                        f"at lap {scan_lap}"
                    )

                    # Color code by laps to complete
                    st.dataframe(
                        opportunities.style.background_gradient(
                            subset=["LapsToComplete"],
                            cmap="RdYlGn_r",
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Best opportunity callout
                    best = opportunities.iloc[0]
                    st.markdown(
                        f"""
                    <div style='background: #12121A; border: 1px solid #00D2BE;
                                border-radius: 8px; padding: 16px; margin-top: 16px;'>
                        <h4 style='color: #00D2BE; margin: 0;'>
                            🏆 BEST OPPORTUNITY
                        </h4>
                        <p style='color: #FFFFFF; margin: 8px 0 0 0;'>
                            <b>{best["Driver"]}</b> can undercut
                            <b>{best["Rival"]}</b> —
                            needs <b>{best["LapsToComplete"]:.1f} laps</b>
                            to complete.
                            Projected gap after stop:
                            <b style='color: #00FF87;'>
                                +{best["GapAfterStop"]:.1f}s ahead
                            </b>
                        </p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            except Exception as e:
                st.error(f"Scan failed: {e}")
