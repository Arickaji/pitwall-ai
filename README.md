# 🏎️ PitWall AI — Formula 1 Race Strategy Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-green?logo=fastapi)
![FastF1](https://img.shields.io/badge/FastF1-data-red)
![Status](https://img.shields.io/badge/Status-Phase%201%20In%20Progress-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> A real-world Formula 1 race strategy intelligence platform simulating the type of software used by F1 teams during race weekends — built for engineering quality, analytical depth, and startup potential.

---

## 🎯 Vision

PitWall AI is designed to help race engineers make data-driven decisions around:

- Pit stop timing and strategy
- Tire degradation modeling
- Lap pace analysis
- Undercut / overcut opportunities
- Safety car predictions
- Driver comparison
- Weather impact simulation
- Race outcome forecasting

---

## 🏗️ Architecture
pitwall-ai/
├── apps/
│   ├── backend/          # FastAPI services (Phase 7)
│   └── frontend/         # React dashboard (Phase 6)
├── core/
│   ├── data/             # Data loaders, FastF1 integration
│   ├── analytics/        # Lap analysis, tire, pace, stint
│   ├── simulation/       # Race strategy simulator
│   ├── ml/               # Machine learning models
│   └── strategy/         # Strategy decision engine
├── pipelines/
│   └── ingestion/        # Data ingestion pipelines
├── ui/
│   └── dashboards/       # Streamlit dashboards
├── tests/                # Unit and integration tests
├── docs/                 # Architecture and schema docs
├── data/
│   ├── raw/              # Raw race data (gitignored)
│   ├── processed/        # Processed datasets (gitignored)
│   └── cache/            # FastF1 cache (gitignored)
└── notebooks/            # Jupyter exploration notebooks

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Data | FastF1, Pandas, NumPy |
| Machine Learning | Scikit-learn, XGBoost |
| Visualization | Plotly, Streamlit → React |
| Backend | FastAPI |
| Database | PostgreSQL |
| Infrastructure | Conda, Docker (later) |
| Version Control | Git, GitHub |

---

## 🗺️ Roadmap

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Data Foundation — FastF1 integration, race loader, lap analysis | ✅ Complete  |
| Phase 2 | Data Engineering — Scalable pipelines, telemetry schema, PostgreSQL | ✅ Complete |
| Phase 3 | Advanced Analytics — Tire modeling, pace comparison, stint analysis | ✅ Complete |
| Phase 4 | Simulation Engine — Race simulator, Monte Carlo, safety car | ✅ Complete  |
| Phase 5 | Machine Learning — Pit stop, tire, position prediction models | ✅ Complete  |
| Phase 6 | Visualization Platform — Premium F1-style dashboards | ⏳ Planned |
| Phase 7 | Backend Platform — FastAPI simulation and prediction endpoints | ⏳ Planned |
| Phase 8 | Deployment — Public platform on Railway/Render + Docker | ⏳ Planned |

---

## ⚙️ Setup

### Prerequisites
- Python 3.11
- Conda

### Installation

```bash
# Clone the repository
git clone https://github.com/Arickaji/pitwall-ai.git
cd pitwall-ai

# Create conda environment
conda env create -f environment.yml
conda activate pitwall-ai

# Verify installation
python -c "import fastf1; print('FastF1 ready')"
```

---

## 📁 Git Workflow
feature/* → staging → main

- `main` — production-ready code only
- `staging` — integration and testing
- `feature/*` — all active development

---

## 📄 License

MIT License — see `LICENSE` for details.

---

<p align="center">Built with engineering rigour. Inspired by F1 strategy rooms.</p>
