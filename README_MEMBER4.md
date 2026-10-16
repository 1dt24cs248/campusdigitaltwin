# Member 4: Vision and AI modules

## Scope and status

This package provides image-based occupancy estimation, evidence-linked sustainability recommendations, and deterministic explanations for simulator results. It is independent of the React app and does not add a second API, database, or simulator. The current workspace has no shared FastAPI backend or Member 3 simulator package, so end-to-end API integration and simulator regression tests are not available here.

The canonical CSV package is explicitly synthetic/illustrative. Recommendations preserve that provenance and do not treat its occupancy, energy, tariff, or timetable values as verified campus measurements. A repository search found no classroom or people image and no external LLM credentials. The shared FastAPI routes/database and Member 3 simulator are also absent from this workspace.

## Files

- `backend/vision/detector.py`: OpenCV HOG image inference and result schema.
- `backend/vision/occupancy.py`: compatibility import for occupancy callers.
- `backend/ai/recommendations.py`: data-driven recommendations.
- `backend/ai/explanations.py`: deterministic simulator explanation.
- `tests/test_vision.py`, `tests/test_recommendations.py`, `tests/test_explanations.py`, `tests/test_member4_integration.py`: focused unit, inference smoke, and Member 4 composition tests.
- `requirements.txt`, `requirements-dev.txt`: Python dependencies.

## Install and test (Windows PowerShell)

From the `campusdigitaltwin` directory:

```powershell
winget install --id Python.Python.3.12 --exact --scope user
$python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
& $python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m pytest -q
```

Python 3.10+ is required. The commands above use the standard per-user Python 3.12 installation path and do not depend on the optional `py` launcher. `opencv-python-headless` is constrained to OpenCV 4 because OpenCV 5 removed the HOG API used here. If Python is already installed elsewhere, set `$python` to that executable before creating `.venv`.

## Occupancy inference

```python
from backend.vision.detector import detect_occupancy

result = detect_occupancy(
    r"C:\data\room-frame.jpg",
    room_id="A-G03",
    valid_room_ids={"A-G03", "A-G04"},
)
```

`detect_occupancy(image, room_id, valid_room_ids=None)` accepts a path or OpenCV-compatible NumPy frame. If supplied, `valid_room_ids` enforces membership in the caller's room catalog. The returned dictionary has `room_id`, `estimated_occupancy`, `source="image_inference"`, `status="estimated"`, UTC `observed_at`, `model`, and `limitations`. It returns no confidence score because HOG scores are not calibrated probabilities. Missing/corrupt input raises `FileNotFoundError`/`ValueError`; model failures raise `RuntimeError` and are never returned as successful estimates.

The detector uses OpenCV's pretrained default HOG pedestrian SVM, not a classroom-trained model. Tests run actual inference on generated blank images to verify the code path; there is no real classroom image in the workspace, so classroom accuracy has not been validated. Occlusion, seating, camera angle, lighting, and posture can reduce detections. A snapshot is not continuous occupancy evidence.

Image results use `image_inference`; caller-entered counts should use `manual_input`; demo records should use `synthetic_demo_data`; absent provenance should remain `unknown`. Keep these sources and historical observations separate.

## Recommendations

```python
from backend.ai.recommendations import generate_recommendations

recommendations = generate_recommendations(
    campus_data=campus_data,  # records loaded from the agreed backend/database schema
    simulation_results=simulation_results,  # actual simulator output, or None
)
```

`generate_recommendations(campus_data, simulation_results=None, *, now=None, max_observation_age_hours=4, low_utilization_threshold=0.25)` accepts canonical-style room/observation/timetable/equipment lists and the React demo's nested `buildings[].floors[].rooms[]` shape. It returns records with a stable `recommendation_id`, room/building IDs, title, evidence, data source/time, impact fields, limitations, operational constraints, next step, simulation ID, and `requires_verification`. Impacts are `None` unless a separate simulator integration supplies reported values; simulator figures are preserved under `simulator_reported_impacts`, not recalculated. A single low count prompts review only. Timetable entries constrain room changes. Equipment review requires an explicit operating state and never asserts energy waste. Missing/stale observations prompt a new verified observation.

## Deterministic explanation

```python
from backend.ai.explanations import generate_explanation

payload = generate_explanation(
    simulation_result=actual_simulator_result,
    campus_context=campus_context,
)
```

`generate_explanation(simulation_result, campus_context=None)` returns `source="deterministic_fallback"`, simulator feasibility/errors/metrics as supplied, affected entities, a readable `explanation`, and a verification `next_step`. Missing metrics are reported unavailable; signed values and validation errors are not changed. Optional caller context keys include `context_notes`, `operational_constraints`, `timetable_constraints`, `capacity_constraints`, `assumptions`, and `missing_information`. No external LLM is configured or used.

## Integration Contract (Proposed)

There is no FastAPI application, route, database model, or Member 3 simulator in this repository. The contracts below are the existing Python functions' inputs/outputs; route paths, HTTP envelopes, database schema, and simulator field names must be agreed by the team. No HTTP request/response JSON is shown because no HTTP interface exists to support it.

### Member 1: Backend and database

Import the existing callables:

```python
from backend.vision import detect_occupancy
from backend.ai import generate_recommendations, generate_explanation
```

For an authorized image upload, resolve `room_id` from the authoritative room table, decode the uploaded image to a file path or OpenCV/NumPy frame, and call `detect_occupancy(image, room_id, valid_room_ids=None)`. It returns `room_id`, integer `estimated_occupancy`, `source="image_inference"`, `status="estimated"`, UTC `observed_at`, `model`, and `limitations`. Persist the observation without changing its source. Keep manual and synthetic observations distinct. Invalid room/image input raises `ValueError` or `FileNotFoundError`; inference failures raise `RuntimeError`.

Call `generate_recommendations(campus_data, simulation_results=None, *, now=None, max_observation_age_hours=4, low_utilization_threshold=0.25)`. `campus_data` must be a mapping containing `rooms` (a list, or nested `buildings[].floors[].rooms[]`), plus optional `occupancy_observations`, `timetable`, and `equipment_inventory` lists. Each room needs `room_id` and preferably `capacity` or `capacity_students`. Observations need `room_id`, a count field (`detected_person_count`, `observed_person_count`, or `estimated_occupancy`), timestamp (`observed_at` or `observation_timestamp`), and provenance (`source`, `data_source`, or recognizable `data_status`). Timetable records need `room_id`. Equipment review only recognizes an explicit operating field (`is_operating`, `operating`, `is_active`, `active`, or `power_state`). Energy records are not consumed by this function. Optional `simulation_results` is one mapping or a list of mappings; include `simulation_id`/`scenario_id`, boolean `feasible`/`is_feasible`, `validation_errors`/`errors`, and any of these top-level metric keys: `baseline_energy_kwh_day`, `proposed_energy_kwh_day`, `energy_saved_kwh_day`, `energy_change_kwh`, `cost_saved_inr_day`, `cost_change_inr`, `baseline_walk_m_day`, `proposed_walk_m_day`, `walking_distance_change_m_day`. It returns a list of records with `recommendation_id`, room/building IDs, title, evidence, `data_source`, `observed_at`, nullable `estimated_energy_impact` and `estimated_cost_impact`, `simulator_reported_impacts`, confidence limitations, operational constraints, next step, `simulation_id`, and `requires_verification`. Simulator metrics are passed through, not calculated; unsupported savings remain null.

Call `generate_explanation(simulation_result, campus_context=None)` with the actual simulator mapping. Pass through `simulation_id`, `feasible`/`is_feasible`/`is_valid`, `validation_errors`/`errors`, affected room/class IDs, assumptions, and available metrics. Supported metric aliases are defined in `backend/ai/explanations.py`; values may be top-level or nested in `metrics`, `energy`, `cost`, or `walking`. It returns `source="deterministic_fallback"`, `simulation_id`, feasibility, validation errors, affected entities, `simulator_metrics`, selected `campus_context`, explanation text, and `next_step`. Missing metrics are reported unavailable. Do not alter feasibility, errors, signs, units, or values. These functions do not perform database I/O.

Member 1 must map the agreed database rows to these function inputs, authorize image access, store observations, and expose agreed routes. Do not create a second FastAPI app or simulator for this integration.

### Member 2: Frontend and room IDs

`src/App.jsx` currently reads the static `src/campusData.js` fixture and does not call an API; its simulation button is not wired to a handler. Fixture IDs such as `A-101` do not match canonical CSV IDs such as `A-G03`. The canonical CSVs are synthetic and are not an authoritative mapping. Member 1 and Member 2 must select one authoritative room ID from the backend room catalog and maintain an explicit, approved ID mapping if the UI must retain separate IDs. Do not match by room name or treat fixture counts as image results.

After route paths and envelopes are agreed, Member 2 should send the image plus the selected authoritative `room_id`, render the detector result fields, send backend-loaded campus records and actual simulator output to the recommendation/explanation routes, and render their returned fields. Preserve `source`, `feasible`, validation errors, and metric signs. No frontend or backend HTTP integration is present yet.

## Verified results (2026-10-16)

- `python -m pytest -q`: **17 passed** in the project `.venv`, including a composition test across vision, recommendations, and explanations. This does not exercise absent FastAPI routes or the absent Member 3 simulator.
- `python -m compileall -q backend tests`: passed.
- The documented dependency install was checked; OpenCV 4.14.0.94 and pytest 9.1.1 are installed.
- Public imports and signatures were checked. A real OpenCV HOG inference call on a generated blank frame returned `estimated_occupancy=0`, `source="image_inference"`, `status="estimated"`. Invalid dictionary image input was rejected. This verifies inference execution only, not people-count accuracy.
- Recommendation checks retained `manual_input` provenance and left energy/cost impacts null. The simulator explanation check retained `feasible=False`, the supplied validation error, and energy/cost values of `-16` and `-136`, with `source="deterministic_fallback"`.
- Canonical CSV integration check read 128 rooms and 59 synthetic occupancy observations; outputs did not claim energy/cost impacts from those rows.
- No classroom/people image exists in the repository, so no real-person image was tested. No FastAPI routes, database models, or Member 3 simulator were found; team integration and simulator regression tests remain blocked until those components are supplied.

## Not implemented or verified

- No classroom-specific accuracy validation: no real campus image was present.
- No shared FastAPI/database integration or simulator tests: those modules are absent from this workspace.
- No live generative LLM API; deterministic fallback is used.
- Attendance is intentionally not implemented; person detection does not establish identity.
- Recommendations cannot establish equipment energy consumption without measured data, and no savings, tariff, or carbon impact is invented.