"""
PitWall AI — Simulation Dashboard Component
Monte Carlo win probabilities, pit optimization, race simulator.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui.dashboards.theme import PLOTLY_LAYOUT


def render_simulation(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """
    Render simulation dashboard.

    Args:
        laps: Full race lap DataFrame
        clean_laps: Filtered accurate laps
        year: Championship year
        gp: Grand Prix name
    """
    st.markdown("### 🎮 RACE SIMULATION ENGINE")

    tab1, tab2, tab3 = st.tabs(
        [
            "MONTE CARLO",
            "PIT OPTIMIZER",
            "RACE SIMULATOR",
        ]
    )

    with tab1:
        _render_monte_carlo(laps, clean_laps, year, gp)

    with tab2:
        _render_pit_optimizer(laps, clean_laps, year, gp)

    with tab3:
        _render_race_simulator(laps, clean_laps, year, gp)


def _render_monte_carlo(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Monte Carlo win probability simulation."""

    st.markdown("#### Monte Carlo Race Simulation")

    col1, col2 = st.columns(2)

    with col1:
        from_lap = st.slider(
            "Simulate from Lap",
            min_value=1,
            max_value=int(laps["LapNumber"].max()) - 5,
            value=20,
            key="mc_from_lap",
        )
        n_sims = st.select_slider(
            "Number of Simulations",
            options=[100, 250, 500, 1000],
            value=250,
            key="mc_n_sims",
        )

    with col2:
        total_laps = int(laps["LapNumber"].max())
        st.metric("Total Race Laps", total_laps)
        st.metric("Laps to Simulate", total_laps - from_lap)
        st.metric("Drivers", laps["Driver"].nunique())

    if st.button("🎲 RUN MONTE CARLO", use_container_width=True):
        with st.spinner(f"Running {n_sims} simulations..."):
            try:
                from core.simulation.monte_carlo import MonteCarloSimulator
                from core.simulation.race_simulator import RaceSimulator

                sim = RaceSimulator(laps, total_laps=total_laps)
                mc = MonteCarloSimulator(sim)

                state = sim.build_state_from_lap(from_lap)
                result = mc.run(state, n_simulations=n_sims, seed=42)

                st.session_state["mc_result"] = result

            except Exception as e:
                st.error(f"Simulation failed: {e}")

    if "mc_result" in st.session_state:
        result = st.session_state["mc_result"]
        win_df = result.win_probabilities

        # Filter to drivers with any wins
        win_df_filtered = win_df[win_df["WinProbability"] > 0]

        col1, col2 = st.columns([2, 1])

        with col1:
            # Win probability bar chart
            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=win_df_filtered["Driver"],
                    y=win_df_filtered["WinProbability"],
                    marker_color="#00D2BE",
                    text=win_df_filtered["WinProbability"].apply(lambda x: f"{x:.1f}%"),
                    textposition="outside",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Win Probability: %{y:.1f}%<br>"
                        "<extra></extra>"
                    ),
                )
            )

            fig.update_layout(
                **PLOTLY_LAYOUT,
                title=f"Win Probability — {result.n_simulations} Simulations",
                xaxis_title="Driver",
                yaxis_title="Win Probability (%)",
                yaxis_range=[0, 100],
                height=400,
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("##### 🏆 STANDINGS")
            top5 = win_df_filtered.head(5)
            for _, row in top5.iterrows():
                color = (
                    "#FFD700"
                    if row["WinProbability"] > 50
                    else "#00D2BE" if row["WinProbability"] > 20 else "#8B8B9E"
                )
                st.markdown(
                    f"""
                <div style='background: #12121A; border-left: 3px solid {color};
                            padding: 8px 12px; margin: 4px 0; border-radius: 4px;'>
                    <span style='color: {color}; font-family: monospace;
                                 font-weight: bold;'>
                        {row["Driver"]}
                    </span>
                    <span style='color: #8B8B9E; float: right;
                                 font-family: monospace;'>
                        {row["WinProbability"]:.1f}%
                    </span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        # Average gaps
        st.markdown("##### Average Finishing Gaps")
        gaps_df = result.avg_gaps.head(8)
        st.dataframe(gaps_df, use_container_width=True, hide_index=True)


def _render_pit_optimizer(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Pit stop optimization."""

    st.markdown("#### Pit Stop Optimizer")

    drivers = sorted(laps["Driver"].unique().tolist())
    total_laps = int(laps["LapNumber"].max())

    col1, col2, col3 = st.columns(3)

    with col1:
        driver = st.selectbox(
            "Driver to Optimize",
            options=drivers,
            key="opt_driver",
        )
        from_lap = st.slider(
            "Current Lap",
            min_value=5,
            max_value=total_laps - 10,
            value=20,
            key="opt_from_lap",
        )

    with col2:
        new_compound = st.selectbox(
            "New Compound",
            options=["SOFT", "MEDIUM", "HARD"],
            key="opt_compound",
        )
        earliest_pit = st.number_input(
            "Earliest Pit Lap",
            min_value=from_lap + 1,
            max_value=total_laps - 5,
            value=from_lap + 2,
            key="opt_earliest",
        )

    with col3:
        latest_pit = st.number_input(
            "Latest Pit Lap",
            min_value=from_lap + 2,
            max_value=total_laps - 3,
            value=min(from_lap + 20, total_laps - 3),
            key="opt_latest",
        )

    if st.button("⚡ OPTIMIZE PIT STOP", use_container_width=True):
        with st.spinner(f"Optimizing pit strategy for {driver}..."):
            try:
                from core.simulation.pit_optimizer import PitOptimizer
                from core.simulation.race_simulator import RaceSimulator

                sim = RaceSimulator(laps, total_laps=total_laps)
                opt = PitOptimizer(sim)
                state = sim.build_state_from_lap(from_lap)

                result = opt.optimize(
                    state=state,
                    driver=driver,
                    new_compound=new_compound,
                    earliest_pit=int(earliest_pit),
                    latest_pit=int(latest_pit),
                )

                st.session_state["opt_result"] = result

            except Exception as e:
                st.error(f"Optimization failed: {e}")

    if "opt_result" in st.session_state:
        result = st.session_state["opt_result"]

        # Recommendation callout
        st.markdown(
            f"""
        <div style='background: #12121A; border: 2px solid #00D2BE;
                    border-radius: 8px; padding: 20px; margin: 16px 0;'>
            <h3 style='color: #00D2BE; font-family: monospace; margin: 0;'>
                ⚡ OPTIMAL PIT: LAP {result.optimal_lap}
            </h3>
            <p style='color: #FFFFFF; margin: 8px 0 0 0;'>
                {result.recommendation}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # All options chart
        options = result.all_options.head(15)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=options["PitLap"],
                y=options["Score"],
                marker_color=[
                    "#FFD700" if lap == result.optimal_lap else "#00D2BE"
                    for lap in options["PitLap"]
                ],
                hovertemplate=(
                    "Pit Lap: %{x}<br>" "Score: %{y:.2f}<br>" "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=f"{driver} — Pit Stop Options (Lower Score = Better)",
            xaxis_title="Pit Lap",
            yaxis_title="Strategy Score",
            height=350,
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(options, use_container_width=True, hide_index=True)


def _render_race_simulator(
    laps: pd.DataFrame,
    clean_laps: pd.DataFrame,
    year: int,
    gp: str,
) -> None:
    """Race simulator visualization."""

    st.markdown("#### Race Simulator")

    total_laps = int(laps["LapNumber"].max())

    col1, col2 = st.columns(2)

    with col1:
        from_lap = st.slider(
            "Simulate from Lap",
            min_value=1,
            max_value=total_laps - 5,
            value=20,
            key="sim_from_lap",
        )

    with col2:
        drivers = sorted(laps["Driver"].unique().tolist())
        track_drivers = st.multiselect(
            "Track Drivers",
            options=drivers,
            default=drivers[:5],
            key="sim_drivers",
        )

    if st.button("▶️ RUN SIMULATION", use_container_width=True):
        with st.spinner("Simulating race..."):
            try:
                from core.simulation.race_simulator import RaceSimulator

                sim = RaceSimulator(laps, total_laps=total_laps)
                state = sim.build_state_from_lap(from_lap)
                result = sim.simulate(state)

                st.session_state["sim_result"] = result

            except Exception as e:
                st.error(f"Simulation failed: {e}")

    if "sim_result" in st.session_state:
        result = st.session_state["sim_result"]

        st.markdown("##### 🏁 FINAL STANDINGS")
        st.dataframe(
            result.final_standings,
            use_container_width=True,
            hide_index=True,
        )

        # Position evolution chart
        lap_data = result.lap_by_lap

        if track_drivers:
            filtered = lap_data[lap_data["Driver"].isin(track_drivers)]

            fig = go.Figure()
            colors = px.colors.qualitative.Set1

            for i, driver in enumerate(track_drivers):
                d_laps = filtered[filtered["Driver"] == driver]
                fig.add_trace(
                    go.Scatter(
                        x=d_laps["Lap"],
                        y=d_laps["Position"],
                        mode="lines",
                        name=driver,
                        line={"width": 2, "color": colors[i % len(colors)]},
                    )
                )

            fig.update_layout(
                **PLOTLY_LAYOUT,
                title="Simulated Position Evolution",
                xaxis_title="Lap",
                yaxis_title="Position",
                height=400,
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
