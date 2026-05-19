# PitWall AI — Streamlit Cloud Entry Point
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Execute the main dashboard directly
exec(open("ui/dashboards/app.py").read())
