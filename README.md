# EcoTwin AI — AI-Powered Sustainable Campus

## Project Overview

EcoTwin AI is a smart-campus demonstration combining an interactive schematic digital twin, classroom image occupancy estimation, grounded generative AI explanations, and a bounded timetable relocation simulator.

The current deterministic simulator proposes one timetable-entry move and can reassign overlapping entries into eligible rooms when the caller supplies the affected class sizes. It is bounded to eight additional assignments and 2,000 search states. It does not apply schedule changes or calculate energy, cost, or walking impacts, so it is not a full campus-wide operational simulator.

## Technology Stack

* Frontend: React and Vite
* Backend: Python and FastAPI
* Database: SQLite
* Computer Vision: OpenCV HOG pretrained pedestrian detector (optional runtime dependency)
* Generative AI: Optional OpenAI-compatible chat completions provider; backend-only API key

## Main Modules

1. Campus dashboard and Digital Twin
2. Campus data management and APIs
3. Campus Ripple Effect Simulator
4. Occupancy vision workflow
5. Sustainability recommendations and AI explanations

## Data Policy

Sample data and simulated results will be explicitly labelled.

Estimated savings must not be presented as measured or guaranteed savings.

## Development Status

Implemented: SQLite-backed FastAPI data endpoints, campus recommendations, optional image occupancy inference, a deterministic bounded schedule-relocation evaluator with cascading room assignments, and configurable generative AI endpoints. All bundled records are synthetic or illustrative. Image inference requires the optional OpenCV package listed in `backend\requirements-vision.txt`.

## Backend quick start

From the repository root, use Python 3.11:

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Starting the backend creates any missing database tables but does not import CSV data. The default database is `backend\ecotwin.db`; set `ECOTWIN_DATABASE_URL` to use a different database. If that database already has records, normal startup does not seed or replace them.

Run backend tests with:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

Start the frontend in a second terminal:

```powershell
npm run dev
```

The Vite development server proxies `/api` requests to `http://127.0.0.1:8000`. For another backend URL, set `VITE_API_BASE_URL` to its `/api` base before starting or building the frontend.

## Production deployment

Vercel hosts the static frontend; it does not host the FastAPI application. The integration branch frontend requires the backend API and intentionally does not substitute local or fabricated data when those requests fail.

1. Deploy the backend from this repository using a Python 3.11 host. Install dependencies with `python -m pip install -r backend/requirements.txt`; use `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` as the start command. Set `ECOTWIN_DATABASE_URL` to a database location that persists across restarts. Do not rely on SQLite stored on an ephemeral filesystem. The checked-in dependencies support SQLite; if using another database engine, add its SQLAlchemy driver before deployment. The backend creates missing tables at startup but does not import the demo dataset.
2. Provision a new, empty, persistent demo database for this deployment. If the demonstration requires the bundled campus records, run `python -m backend.seed_data` once as an explicit setup/release task with `ECOTWIN_DATABASE_URL` pointing to that new database. Do not run it against an existing database that must be preserved. Confirm the backend and the import task use the same database URL. The bundled dataset is synthetic or illustrative.
3. Set the backend environment variable `ECOTWIN_CORS_ORIGINS` to a comma-separated allowlist of exact origins, including `https://campusdigitaltwin.vercel.app`. Do not use `*`. Add any required Vercel preview origin explicitly only if those previews need API access.
4. In the Vercel project, deploy the `integration/ecotwin-full-project` branch with the repository root as the project root, `npm run build` as the build command, and `dist` as the output directory. Set the build-time variable `VITE_API_BASE_URL` to the real deployed backend's public HTTPS API base ending in `/api` (for example, `https://<your-backend-host>/api`) for the Production environment, then redeploy. Do not set it to localhost or put private credentials in a `VITE_` variable.
5. Verify `GET <backend-base>/api/health` and `GET <backend-base>/api/buildings` over HTTPS. The health endpoint should report a connected database; the buildings endpoint should return the initialized demo rows. Then use the deployed frontend to test building navigation, a valid and invalid simulation, and Insights.

No backend URL is configured or inferable from this repository or the current deployment, so the Vercel environment variable cannot be completed until the backend has been deployed.

### Optional: initialize a disposable demo database

Dataset import is a separate, explicit setup operation; it is not part of normal application startup. The importer reads CSVs from `data/raw/ecotwin_dataset/`. For a demo, use a new disposable database path, or make and verify a backup before importing into a database that contains records. Do not point this command at a database whose data must be preserved.

The importer inserts new IDs and updates existing records when imported values differ, then commits the changes. It does not delete records absent from the CSVs. `ECOTWIN_DATABASE_URL` selects the database for both the seed command and backend startup; setting it is configuration, not an automatic isolation or backup mechanism. Replace the example path below with a new location that you have verified is not an existing database:

```powershell
$env:ECOTWIN_DATABASE_URL = "sqlite:///C:/path/to/disposable-ecotwin-demo.db"
backend\.venv\Scripts\python.exe -m backend.seed_data
```

Keep that same `ECOTWIN_DATABASE_URL` value in the backend terminal when starting the server to use the imported demo database. The frontend reads campus records from the API; it does not use the separate CSV copy as a fallback. See [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) for endpoint behavior, simulator limitations, provenance, and request/response examples.

To enable image inference in the existing backend environment, install the optional wheel without recreating the environment:

```powershell
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-vision.txt
```

## Language model configuration

Campus browsing, image analysis, recommendations, and deterministic simulation work without a language model key. To enable live AI answers and simulation explanations, create `.env` from `.env.example` if it does not already exist, then set `ECOTWIN_LLM_API_KEY`. The backend loads `.env` at startup. It supports an OpenAI-compatible chat completions endpoint; configure `ECOTWIN_LLM_BASE_URL` and `ECOTWIN_LLM_MODEL` for your provider. Keep the key in the backend environment only. Restart the backend after setting values. Provider failures, timeouts, rate limits, and malformed responses fall back to an explicitly labelled unavailable explanation. Automated tests mock the model call; no live provider credentials are included in this repository.

## Demonstration flow

1. Start the backend and frontend as above, then open the Vite URL.
2. Open **Buildings**, choose a building, floor, and room, and review the room details and schedule.
3. Open **Occupancy vision**, choose the classroom image and room, and run the estimate. Select a JPEG or PNG up to 5 MiB and 16,777,216 pixels total (at least 64 pixels wide by 128 pixels tall) for the HOG detector. Changing the image or room clears the previous estimate and its scenario opt-in. The image is held temporarily for inference and is not saved.
4. In **Simulation**, enter the known class enrollment separately, then select the timetable entry and destination. You may explicitly include the image observation as context when it matches the source or destination room; it never fills enrollment or participates in capacity checks. Additional class sizes use one `timetable-entry-id=count` line each.
5. Review the baseline and proposed rooms, constraint results, affected entries, and AI explanation. The proposed schedule is never applied to the timetable.
6. Open **AI assistant** to ask questions grounded in the campus records. Live model responses require the optional provider configuration above.

The included campus records are illustrative demo data. The optional detector is OpenCV's general HOG pedestrian detector, not a classroom-calibrated model. Its image estimate and bounding boxes have not been validated for real-world occupancy accuracy. A single image is not a live sensor feed or attendance record. The relocation search is bounded to eight cascading moves and 2,000 search states; energy, cost, and walking changes remain unavailable from the current inputs.

## Implemented scope

- **Digital twin:** interactive schematic building/floor/room browser backed by the campus API, including capacity, room records, occupancy observations, equipment, and timetable.
- **Computer vision:** optional JPEG/PNG image inference through OpenCV HOG, with visible detections and a non-persisted estimate. Model-reported HOG scores are detector scores, not calibrated probabilities.
- **Generative AI:** optional OpenAI-compatible backend model call for campus questions and explanations of the deterministic simulation output. Without credentials, the UI remains usable and the service returns a transparent fallback.
- **Simulation:** deterministic, bounded schedule reassignment proposal with capacity and overlap checks. It does not mutate the operational timetable and is not a complete campus-wide operational twin.

See [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) for detailed request shapes, limits, and response behavior.
