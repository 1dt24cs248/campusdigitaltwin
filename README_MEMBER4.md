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
    campus_data={
        "rooms": [{"room_id": "A-G03", "building_id": "A", "capacity_students": 40}],
        "occupancy_observations": [{
            "room_id": "A-G03", "detected_person_count": 3,
            "observed_at": "2026-10-16T09:15:00Z", "source": "manual_input",
        }],
        "timetable": [{"room_id": "A-G03", "day_of_week": "Monday", "period_number": 1}],
        "equipment_inventory": [],
    },
    simulation_results=None,
)
```

`generate_recommendations(campus_data, simulation_results=None, *, now=None, max_observation_age_hours=4, low_utilization_threshold=0.25)` accepts canonical-style room/observation/timetable/equipment lists and the React demo's nested `buildings[].floors[].rooms[]` shape. It returns records with a stable `recommendation_id`, room/building IDs, title, evidence, data source/time, impact fields, limitations, operational constraints, next step, simulation ID, and `requires_verification`. Impacts are `None` unless a separate simulator integration supplies reported values; simulator figures are preserved under `simulator_reported_impacts`, not recalculated. A single low count prompts review only. Timetable entries constrain room changes. Equipment review requires an explicit operating state and never asserts energy waste. Missing/stale observations prompt a new verified observation.

## Deterministic explanation

```python
from backend.ai.explanations import generate_explanation

payload = generate_explanation(
    simulation_result={
        "simulation_id": "SIM004",
        "feasible": False,
        "validation_errors": ["Capacity exceeded"],
        "baseline_energy_kwh_day": 520,
        "proposed_energy_kwh_day": 536,
        "energy_saved_kwh_day": -16,
        "cost_saved_inr_day": -136,
    },
    campus_context={"timetable_constraints": ["Faculty availability not checked"]},
)
```

`generate_explanation(simulation_result, campus_context=None)` returns `source="deterministic_fallback"`, simulator feasibility/errors/metrics as supplied, affected entities, a readable `explanation`, and a verification `next_step`. Missing metrics are reported unavailable; signed values and validation errors are not changed. Optional caller context keys include `context_notes`, `operational_constraints`, `timetable_constraints`, `capacity_constraints`, `assumptions`, and `missing_information`. No external LLM is configured or used.

## Backend integration contract

Member 1 can import:

```python
from backend.vision import detect_occupancy
from backend.ai import generate_recommendations, generate_explanation
```

No integration was performed because the shared service and simulator do not exist in this workspace. The following is a proposed contract, not a description of existing routes.

Member 1 should:

1. Add an authorized image-upload route that resolves `room_id` against the existing room table, accepts an image file, calls `detect_occupancy(image_path_or_frame, room_id, valid_room_ids)`, and stores the returned observation without changing `source`. Its response fields are `room_id`, `estimated_occupancy`, `source`, `status`, `observed_at`, `model`, and `limitations`. Preserve `source="image_inference"`; keep manual and synthetic rows distinct.
2. For recommendations, load `rooms` (each with `room_id` and `capacity` or `capacity_students`), `occupancy_observations` (with `room_id`, a supported count field, timestamp, and provenance), `timetable` (at least `room_id`), and optional `equipment_inventory` (with an explicit operating-state field). Pass these as `campus_data` and the actual simulator result(s) as `simulation_results` to `generate_recommendations`. Return its list unchanged, including `recommendation_id`, evidence, provenance, nullable impacts, constraints, next step, and `requires_verification`.
3. For an explanation request, pass the actual simulator result mapping to `generate_explanation(simulation_result, campus_context)`. Include boolean `feasible`, `validation_errors`, stable `simulation_id`, affected room/class IDs, and any available simulator-reported energy, cost, and walking metrics with units. Return `source="deterministic_fallback"`, `feasible`, `validation_errors`, `simulator_metrics`, `explanation`, and `next_step`; do not recalculate or override simulator values.

These functions do not write to the database. Member 2 can display returned fields directly. No new route names or database schema are prescribed here; Member 1 should map these payloads to the project's agreed API/schema when that code is available.

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