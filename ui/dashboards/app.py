"""
PitWall AI — Main Dashboard Application
F1 Race Strategy Intelligence Platform
"""

import streamlit as st

from core.analytics.pace import get_clean_race_laps
from core.data.f1_loader import load_laps
from ui.dashboards.theme import apply_theme

# ── Page Config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PitWall AI",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

# ── Header ─────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style='text-align: center; padding: 20px 0 10px 0;'>
        <h1 style='color: #00D2BE; font-family: monospace; font-size: 2.5rem;
                   letter-spacing: 4px; margin: 0;'>
            🏎️ PITWALL AI
        </h1>
        <p style='color: #8B8B9E; font-family: monospace; font-size: 0.9rem;
                  letter-spacing: 2px; margin: 4px 0 0 0;'>
            F1 RACE STRATEGY INTELLIGENCE PLATFORM
        </p>
    </div>
    <hr style='border-color: #1E1E2E; margin: 10px 0 20px 0;'>
""",
    unsafe_allow_html=True,
)

# ── Sidebar — Session Selector ─────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🎯 SESSION SELECT")
    st.markdown("---")

    year = st.selectbox(
        "Season",
        options=[2024, 2023, 2022],
        index=0,
    )

    # GP options — 2024 calendar
    GP_OPTIONS = [
        "Bahrain Grand Prix",
        "Saudi Arabian Grand Prix",
        "Australian Grand Prix",
        "Japanese Grand Prix",
        "Chinese Grand Prix",
        "Miami Grand Prix",
        "Emilia Romagna Grand Prix",
        "Monaco Grand Prix",
        "Canadian Grand Prix",
        "Spanish Grand Prix",
        "Austrian Grand Prix",
        "British Grand Prix",
        "Hungarian Grand Prix",
        "Belgian Grand Prix",
        "Dutch Grand Prix",
        "Italian Grand Prix",
        "Azerbaijan Grand Prix",
        "Singapore Grand Prix",
        "United States Grand Prix",
        "Mexico City Grand Prix",
        "São Paulo Grand Prix",
        "Las Vegas Grand Prix",
        "Qatar Grand Prix",
        "Abu Dhabi Grand Prix",
    ]

    gp = st.selectbox("Grand Prix", options=GP_OPTIONS, index=0)

    session_type = st.selectbox(
        "Session",
        options=["R", "Q", "FP1", "FP2", "FP3"],
        format_func=lambda x: {
            "R": "Race",
            "Q": "Qualifying",
            "FP1": "Practice 1",
            "FP2": "Practice 2",
            "FP3": "Practice 3",
        }[x],
        index=0,
    )

    st.markdown("---")
    load_btn = st.button("🔄 LOAD SESSION", use_container_width=True)

    if load_btn:
        with st.spinner(f"Loading {year} {gp}..."):
            try:
                laps = load_laps(year, gp, session_type)
                clean = get_clean_race_laps(laps)
                st.session_state["laps"] = laps
                st.session_state["clean_laps"] = clean
                st.session_state["year"] = year
                st.session_state["gp"] = gp
                st.session_state["session_type"] = session_type
                st.session_state["loaded"] = True
                st.success(f"✓ {len(laps)} laps loaded")
            except Exception as e:
                st.error(f"Failed to load: {e}")
                st.session_state["loaded"] = False

    st.markdown("---")
    st.markdown(
        "<p style='color: #8B8B9E; font-size: 0.75rem; font-family: monospace;"
        "text-align: center;'>PITWALL AI v0.1.0<br>Phase 6 — Visualization</p>",
        unsafe_allow_html=True,
    )

# ── Main Content ───────────────────────────────────────────────────────────────

if not st.session_state.get("loaded"):
    # Landing state
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
        <div style='background: #12121A; border: 1px solid #1E1E2E;
                    border-radius: 8px; padding: 20px; text-align: center;'>
            <h3 style='color: #00D2BE;'>📊 ANALYTICS</h3>
            <p style='color: #8B8B9E; font-size: 0.85rem;'>
                Lap time progression, pace comparison,
                stint analysis, undercut modeling
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div style='background: #12121A; border: 1px solid #1E1E2E;
                    border-radius: 8px; padding: 20px; text-align: center;'>
            <h3 style='color: #00D2BE;'>🎮 SIMULATION</h3>
            <p style='color: #8B8B9E; font-size: 0.85rem;'>
                Monte Carlo race simulation,
                pit optimization, SC modeling
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        <div style='background: #12121A; border: 1px solid #1E1E2E;
                    border-radius: 8px; padding: 20px; text-align: center;'>
            <h3 style='color: #00D2BE;'>🤖 ML PREDICTIONS</h3>
            <p style='color: #8B8B9E; font-size: 0.85rem;'>
                Pit stop probability, tyre degradation,
                position forecasting
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
    <div style='text-align: center; margin-top: 60px; color: #8B8B9E;
                font-family: monospace;'>
        <p>← Select a session in the sidebar and click LOAD SESSION</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

else:
    # Session loaded — show dashboard tabs
    from ui.dashboards.components.race_overview import render_race_overview

    laps = st.session_state["laps"]
    clean_laps = st.session_state["clean_laps"]
    year = st.session_state["year"]
    gp = st.session_state["gp"]

    # Session info bar
    st.markdown(
        f"""
    <div style='background: #12121A; border: 1px solid #00D2BE;
                border-radius: 6px; padding: 10px 20px; margin-bottom: 20px;
                font-family: monospace;'>
        <span style='color: #00D2BE;'>● LIVE</span>
        <span style='color: #8B8B9E; margin-left: 20px;'>
            {year} {gp} — {st.session_state["session_type"]}
        </span>
        <span style='color: #8B8B9E; margin-left: 20px;'>
            {len(laps)} LAPS | {laps["Driver"].nunique()} DRIVERS
        </span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "🏁 RACE OVERVIEW",
            "🎯 STRATEGY",
            "🏎️ DEGRADATION",
            "🎮 SIMULATION",
            "📡 TELEMETRY",
        ]
    )

    with tab1:
        render_race_overview(laps, clean_laps, year, gp)

    with tab2:
        from ui.dashboards.components.strategy import render_strategy

        render_strategy(laps, clean_laps, year, gp)

    with tab3:
        st.info("Degradation dashboard — coming soon")

    with tab4:
        st.info("Simulation dashboard — coming soon")

    with tab5:
        st.info("Telemetry dashboard — coming soon")
