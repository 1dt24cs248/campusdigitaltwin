# Member 4: Vision, Occupancy, and AI

## Status and Scope

The workspace has standalone Python modules and synthetic CSVs, but no shared
FastAPI application, database models, frontend, real campus data, or classroom
image. The modules below are callable and tested independently. They are not
HTTP/API-integrated.

Member 4 files:

- `occupancy.py`: OpenCV HOG image/frame inference, manual-input observations,
  provenance labels, validation, and inference errors.
- `sustainability.py`: configurable evidence-based recommendations using room,
  occupancy, equipment, timetable, energy, action, and optional simulator data.
- `explanations.py`: deterministic fallback explanations grounded in simulator
  response fields.
- `scripts/generate_demo_data.py`: reproducible campus CSV generator.
- `test_member4.py`: isolated generator, inference, recommendation, and
  explanation tests.
- `data/`: generated synthetic demo CSVs. See [data/README.md](data/README.md).
- `requirements-vision.txt`: optional image-inference dependency.

This project retains its existing root-level module structure; no duplicate
backend or database was created.

## Runtime and Installation

Tested with Python 3.14.7 and `opencv-python-headless` 4.14.0.94. NumPy is
installed as OpenCV's dependency. Standard-library modules and tests require no
other package. FastAPI, Pydantic, pytest, and LLM client packages are not
installed in this workspace.

From the workspace parent in Windows PowerShell:

```powershell
python -m pip install -r campusdigitaltwin/requirements-vision.txt
python campusdigitaltwin/scripts/generate_demo_data.py
python -m unittest discover -s campusdigitaltwin -p "test_*.py" -v
```

The generator accepts `--seed`, `--tariff`, and `--output-dir`. Its default
seed is fixed; the default INR 8.50/kWh tariff is illustrative and unverified.

## Occupancy Inference

The image API is:

```python
from occupancy import estimate_from_image

result = estimate_from_image(
    image_path=r"C:\campus-demo\room-frame.jpg",
    room_id="A101",
    capacity_students=40,
    known_room_ids={"A101", "A102"},  # Load from the shared room table.
)
```

`estimate_from_frame(frame, room_id, capacity_students, known_room_ids=None)`
accepts a decoded OpenCV-compatible array. `estimate_from_manual_input(...)`
records a separate user-entered count. `estimate_from_detection_count(...)` is a
validation helper and labels a bare count `unknown`; it cannot claim that the
count came from image inference.

Successful image result shape:

```json
{
  "room_id": "A101",
  "estimated_occupancy": 0,
  "capacity_students": 40,
  "occupancy_ratio": 0.0,
  "source": "image_inference",
  "status": "estimated",
  "observed_at": "UTC ISO-8601 timestamp",
  "model": "opencv_hog_default_people_detector",
  "data_label": "image_inference",
  "confidence": null,
  "detector_scores": [],
  "limitations": ["..."],
  "image_retained": false
}
```

The example count above describes the blank-image smoke test only; it is not a
campus observation. Actual returned counts come from the detector. HOG scores
are not calibrated confidence probabilities. A bare count has source
`unknown`; a manual entry uses `manual_input`; generated CSV observations use
`synthetic_demo_data`. Do not change a source label to make observations look
live.

Pass `known_room_ids` (or perform equivalent database validation before the
call) to reject unknown room IDs. Missing files raise `FileNotFoundError`;
unsupported/corrupt images and invalid metadata raise `OccupancyInputError`;
detector failures raise `OccupancyInferenceError`. No success-shaped estimate
is returned after a failure.

The detector is OpenCV's built-in default HOG pedestrian model, not a
classroom-trained model. HOG commonly misses seated, occluded, small, and
overhead-view people; lighting, camera angle, resolution, and false positives
also matter. One image is one snapshot, not continuous occupancy or attendance.
No real classroom image was present in the workspace. The actual inference path
was smoke-tested on a temporary blank PNG; that verifies the call path, not
person-detection accuracy. No student identity or attendance is inferred.

## Recommendations

Callable interface:

```python
from sustainability import build_recommendations

result = build_recommendations(
    rooms=room_rows,
    occupancy_observations=observation_rows,
    energy_records=energy_rows,
    sustainability_actions=action_rows,
    timetable=timetable_rows,
    equipment_inventory=equipment_rows,
    simulation_results=simulation_response_or_list,
    low_occupancy_threshold=0.25,
    high_connected_load_kw=0.8,
    max_observation_age_hours=24,
    timetable_timezone=campus_timezone,  # Set when schedule timezone is known.
)
```

All input rows are ordinary dictionaries, including CSV `DictReader` rows.
Recommendations can flag missing/stale observations, low snapshot counts,
connected load, unverified tariffs, and feasible simulator proposals. They
include room/building IDs, data source/timestamp, supporting evidence,
limitations, operational constraints, and next steps. A low count is only a
review prompt; timetable context is checked when its timezone can be aligned.
For UTC observations, pass the campus `timetable_timezone`; without it, the
module does not claim that no class was scheduled.

Simulator energy, cost, and walking impacts are copied from a feasible
simulator response, not independently recalculated. Infeasible or incomplete
simulator results do not produce relocation recommendations. Equipment
inventory and assumed runtime do not prove that equipment was operating at the
observation time. Recommendations never turn equipment off or close rooms.
Priority ordering is a transparent rule, not a scientifically validated score.

## Explanations

```python
from explanations import build_simulation_explanation

explanation = build_simulation_explanation(
    simulator_response,
    campus_context={"building_name": "Block A", "room_type": "classroom"},
)
```

The structured result has `mode: "deterministic_fallback"`, `status`,
`simulation_id`, `text`, and `limitations`. `explain_simulation(result)` is a
backward-compatible text helper. Explanations preserve simulator feasibility,
validation errors, units, signed savings, assumptions, and unavailable fields.
The simulator remains authoritative for numbers; the explanation module does
not recalculate them.

No LLM client or API key is configured, and no external LLM call was made. The
deterministic fallback works without credentials and is not described as live
generative AI.

## Integration Contract

Member 1 can import these functions from the project root:

```python
from occupancy import estimate_from_image, estimate_from_frame, estimate_from_manual_input
from sustainability import build_recommendations
from explanations import build_simulation_explanation
```

For a future route, validate `room_id` against the shared database, obtain room
capacity and known room IDs there, call `estimate_from_image`, then persist its
returned observation without replacing prior observations. Handle the
documented exceptions as client errors or inference failures; do not convert an
exception into an occupancy value. Pass current rows and the exact Member 3
simulation response to the recommendation and explanation functions. Persist
the returned recommendation/explanation only through the shared data layer.

An API response can wrap the occupancy dictionary as-is. Member 2 can display
`estimated_occupancy`, `capacity_students`, `status`, `source`, `observed_at`,
`limitations`, and `warning`; do not display detector scores as a confidence
percentage. Recommendations expose `recommendations` and `warnings`; each
recommendation has evidence, limitations, next step, and optional simulator
impact fields. Explanation responses expose `mode` and `text`.

No backend route was added because the shared backend does not exist in this
workspace. No frontend, database, persistence, API-key setup, or attendance
workflow is implemented. Attendance remains intentionally out of scope because
person detection does not identify students.

## Verification

Run from the workspace parent:

```powershell
python campusdigitaltwin/scripts/generate_demo_data.py
python -m unittest discover -s campusdigitaltwin -p "test_*.py" -v
```

The suite covers the existing Member 3 simulator and Member 4 generation,
inference errors/provenance, schedule-aware recommendations, simulator result
pass-through, and deterministic explanations. It does not validate HOG accuracy
on real people or classroom imagery.
