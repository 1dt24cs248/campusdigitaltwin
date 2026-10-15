# EcoTwin AI — AI-Powered Sustainable Campus

## Project Overview

EcoTwin AI is a proposed smart-campus platform combining an interactive 2D Digital Twin, classroom occupancy estimation, sustainability recommendations and a Campus Ripple Effect Simulator.

The simulator evaluates proposed classroom-allocation changes by checking room capacity, timetable conflicts, estimated energy consumption, estimated electricity cost and walking-distance trade-offs.

## Planned Technology Stack

* Frontend: React and Vite
* Backend: Python and FastAPI
* Database: SQLite
* Computer Vision: Pretrained person-detection model
* AI: Result-grounded explanations with a deterministic fallback

## Main Modules

1. Campus dashboard and Digital Twin
2. Campus data management and APIs
3. Campus Ripple Effect Simulator
4. Occupancy estimation and attendance workflow
5. Sustainability recommendations and AI explanations

## Data Policy

Sample data and simulated results will be explicitly labelled.

Estimated savings must not be presented as measured or guaranteed savings.

## Development Status

Backend milestone implemented: SQLite-backed FastAPI health, building, room, timetable, occupancy, simulator-pending, and sustainability endpoints, plus a repeatable synthetic CSV importer. Run the documented tests before treating any behavior as complete.

## Backend quick start

From the repository root, use Python 3.11:

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python.exe -m backend.seed_data
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run backend tests with:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

The backend imports CSVs from `data/raw/ecotwin_dataset/` into `backend/ecotwin.db`. All supplied records are synthetic or illustrative. The simulator endpoint reports integration pending until a real simulator module is available; it does not fabricate simulation results. See [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) for endpoints, filters, provenance, and request/response examples.
