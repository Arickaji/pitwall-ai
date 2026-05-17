"""
PitWall AI — F1 Design System
Dark theme inspired by F1 pit wall screens and timing towers.
"""

# ── Color Palette ──────────────────────────────────────────────────────────────

COLORS = {
    "background": "#0A0A0F",
    "surface": "#12121A",
    "border": "#1E1E2E",
    "primary": "#00D2BE",  # Mercedes teal — brand color
    "secondary": "#FF1E00",  # F1 red — alerts
    "accent": "#FFD700",  # Gold — podium/fastest lap
    "text_primary": "#FFFFFF",
    "text_secondary": "#8B8B9E",
    "success": "#00FF87",
    "warning": "#FFB800",
}

# ── Tyre Compound Colors ───────────────────────────────────────────────────────

COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFD700",
    "HARD": "#CCCCCC",
    "INTER": "#39B54A",
    "WET": "#0067FF",
    "UNKNOWN": "#888888",
}

# ── Driver Colors ──────────────────────────────────────────────────────────────

TEAM_COLORS = {
    "Red Bull Racing": "#1E41FF",
    "Mercedes": "#00D2BE",
    "Ferrari": "#DC0000",
    "McLaren": "#FF8000",
    "Aston Martin": "#006F62",
    "Alpine": "#0090FF",
    "Williams": "#005AFF",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD",
}

# ── Plotly Theme ───────────────────────────────────────────────────────────────

PLOTLY_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "#0A0A0F",
    "plot_bgcolor": "#12121A",
    "font": {"color": "#FFFFFF", "family": "monospace"},
    "xaxis": {"gridcolor": "#1E1E2E", "linecolor": "#1E1E2E"},
    "yaxis": {"gridcolor": "#1E1E2E", "linecolor": "#1E1E2E"},
    "legend": {"bgcolor": "#12121A", "bordercolor": "#1E1E2E"},
    "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
}

# ── Streamlit CSS ──────────────────────────────────────────────────────────────

STREAMLIT_CSS = """
<style>
    /* Main background */
    .stApp {
        background-color: #0A0A0F;
        color: #FFFFFF;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #12121A;
        border-right: 1px solid #1E1E2E;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #12121A;
        border: 1px solid #1E1E2E;
        border-radius: 8px;
        padding: 16px;
    }

    /* Headers */
    h1, h2, h3 {
        color: #00D2BE;
        font-family: monospace;
    }

    /* Selectbox */
    .stSelectbox > div > div {
        background-color: #12121A;
        border-color: #1E1E2E;
        color: #FFFFFF;
    }

    /* Buttons */
    .stButton > button {
        background-color: #00D2BE;
        color: #0A0A0F;
        border: none;
        font-weight: bold;
        font-family: monospace;
    }

    .stButton > button:hover {
        background-color: #00B5A3;
    }

    /* Divider */
    hr {
        border-color: #1E1E2E;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #12121A;
        border-bottom: 1px solid #1E1E2E;
    }

    .stTabs [data-baseweb="tab"] {
        color: #8B8B9E;
        font-family: monospace;
    }

    .stTabs [aria-selected="true"] {
        color: #00D2BE;
        border-bottom: 2px solid #00D2BE;
    }

    /* Dataframe */
    .dataframe {
        background-color: #12121A;
        color: #FFFFFF;
    }
</style>
"""


def apply_theme() -> None:
    """Inject F1 theme CSS into Streamlit app."""
    import streamlit as st

    st.markdown(STREAMLIT_CSS, unsafe_allow_html=True)


def format_lap_time(seconds: float) -> str:
    """
    Format lap time seconds to M:SS.mmm display format.

    Args:
        seconds: Lap time in seconds

    Returns:
        str: Formatted time e.g. '1:32.456'
    """
    if seconds is None or seconds != seconds:  # NaN check
        return "N/A"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"


def format_gap(seconds: float) -> str:
    """
    Format gap between drivers.

    Args:
        seconds: Gap in seconds

    Returns:
        str: Formatted gap e.g. '+5.234s' or 'LEADER'
    """
    if seconds == 0:
        return "LEADER"
    return f"+{seconds:.3f}s"
