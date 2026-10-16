# EcoTwin AI Backend API Contracts

Base URL for local development: `http://127.0.0.1:8000`

All campus records currently imported from the canonical dataset are synthetic or illustrative. `data_status` is returned with records and must be shown as provenance, not interpreted as a claim that data is measured or live.

## Local setup

From the repository root, create and use a Python 3.11 environment:

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Starting the backend creates any missing database tables but does not import CSV data. SQLite defaults to `backend\ecotwin.db`; set `ECOTWIN_DATABASE_URL` to use a different database.

Run tests with:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

### Optional: initialize a disposable demo database

Dataset import is a separate, explicit setup operation, not part of normal application startup. Use a new disposable database path, or make and verify a backup before importing into a database that contains records. Do not point the command at a database whose data must be preserved.

The importer reads `data/raw/ecotwin_dataset/`. It imports buildings, rooms, timetable entries, equipment, energy estimates, occupancy observations, room distances, and sustainability actions. It validates required columns and row values, checks room/building references, then reports source, inserted, updated, skipped, and rejected counts. Existing IDs are updated if imported values differ; unchanged rows are skipped. It commits changes and does not delete existing rows. `ECOTWIN_DATABASE_URL` selects the database for the import and backend; setting it is configuration, not an automatic isolation or backup mechanism. Replace the example path with a new location you have verified is not an existing database:

```powershell
$env:ECOTWIN_DATABASE_URL = "sqlite:///C:/path/to/disposable-ecotwin-demo.db"
backend\.venv\Scripts\python.exe -m backend.seed_data
```

Keep the same `ECOTWIN_DATABASE_URL` value when starting the backend to use the imported demo database. `ECOTWIN_CORS_ORIGINS` accepts comma-separated origins; by default it allows the deployed frontend origin `https://campusdigitaltwin.vercel.app` plus `http://localhost:5173` and `http://127.0.0.1:5173`. Set it to an explicit comma-separated origin allowlist for deployment; do not use a wildcard.

For production, deploy the FastAPI backend separately from Vercel, configure a persistent database, and set the Vercel build-time variable `VITE_API_BASE_URL` to the backend's public HTTPS base ending in `/api`. The frontend requires this explicit value in production and reports a configuration error instead of silently requesting the static frontend's `/api` path. See the production deployment steps in the root README.

## Health

### `GET /api/health`

Returns `200` when the database can execute a connectivity query:

```json
{"status": "ok", "database": "connected"}
```

Returns `503` with `{"detail":{"status":"unavailable","database":"disconnected"}}` when unavailable. Internal exception details are not returned.

## Buildings

### `GET /api/buildings`

Returns all buildings in identifier order.

### `GET /api/buildings/{building_id}`

Returns one building or `404` if it does not exist. Example: `GET /api/buildings/A`.

Building fields: `building_id`, `building_name`, `data_status`.

## Rooms

### `GET /api/rooms`

Returns rooms ordered by ID. Optional exact-match/range query parameters:

* `building_id`, `floor_number`, `facility_type`
* `min_capacity`, `max_capacity` (nonnegative; minimum cannot exceed maximum)
* `timetable_eligible` (`true` or `false`)
* `offset` (default `0`), `limit` (default `100`, maximum `500`)

Example: `GET /api/rooms?building_id=A&floor_number=1&timetable_eligible=true&min_capacity=20`.

### `GET /api/rooms/{room_id}`

Returns room metadata or `404`. Example: `GET /api/rooms/A-F1-04`.

### `GET /api/rooms/{room_id}/timetable`

Returns timetable entries assigned to the room. Optional `semester` and `day_of_week` filters. Returns `404` for an unknown room. Example: `GET /api/rooms/A-F1-04/timetable?semester=1`.

Room fields include floor, facility, department, capacity (students), estimated connected load (kW), timetable eligibility, notes, and `data_status`. Room capacity is not an observed headcount.

## Timetables

### `GET /api/timetables`

Optional filters: `semester`, `section`, `department`, `day_of_week`, `room_id`, `subject_code`, `offset`, and `limit` (default `100`, maximum `500`).

Example: `GET /api/timetables?semester=1&section=A&day_of_week=Monday&subject_code=CSE101` returns the matching synthetic entry `TT0001`. No semester is assumed when the parameter is omitted. Schedule comparisons across semesters must not be treated as simultaneous.

Timetable responses include the entry ID, semester/section, day, start/end times, subject, room, faculty identifier, session type, and `data_status`.

## Equipment and energy

### `GET /api/equipment`

Returns equipment inventory, optionally filtered by exact `room_id`, with `offset` and `limit` pagination. Returned estimates and assumptions retain their `data_status`.

### `GET /api/energy`

Returns room-level energy estimates, optionally filtered by exact `room_id`, with `offset` and `limit` pagination. These daily/weekly values are source records, not measured live consumption or per-class estimates.

## Occupancy

### `GET /api/occupancy`

Returns available observations, optionally filtered by `room_id`, with `offset` and `limit` pagination. Imported synthetic examples are returned as examples, not live camera output.

### `POST /api/occupancy`

Accepts an occupancy estimate/observation. Room existence, nonnegative person count, timestamp, and optional confidence (`0` through `1`) are validated. `data_status` and `detection_method` are required provenance fields.

Example body using a real room identifier:

```json
{
  "room_id": "A-G03",
  "detected_person_count": 20,
  "observed_at": "2026-10-15T10:15:00+05:30",
  "detection_method": "SYNTHETIC placeholder, not webcam detection",
  "confidence_score": null,
  "verified_by_human": false,
  "data_status": "SYNTHETIC observation"
}
```

The example values reproduce the supplied synthetic observation `OBS0001`; posting it creates a new record and does not claim that a vision model ran. The response includes the submitted source, timestamp, count, confidence, verification flag, and status. Capacity and occupancy percentage remain `null` unless supplied by a future supported integration. The API does not equate occupancy with attendance.

### `POST /api/occupancy/infer`

Accepts a canonical `room_id`, an `image_format` of `png` or `jpeg`, and a base64-encoded image (`image_base64`). The base64-decoded image file bytes are limited to 5 MiB, and decoded image dimensions are limited to 16,777,216 pixels. PNG/JPEG dimensions are checked from the image header before decoding the pixel buffer. Room IDs must match the database exactly; the API does not map aliases such as `A101` to canonical room IDs.

When OpenCV and NumPy are installed, the route calls Member 4's `detect_occupancy` function and returns its estimate, the room's database capacity, and `persisted: false`. The image must be at least 64 pixels wide and 128 pixels tall for the HOG detector; smaller images return `422`. Excessive dimensions, invalid base64, empty/oversized images, or undecodable images return `422`; unknown rooms return `404`. The estimate is an image-based snapshot of visible-person detections, is not a verified count, is not stored in the occupancy table, and does not identify students or establish attendance or enrollment. The general HOG detector is not calibrated for classroom seating and has no established real-world accuracy. If OpenCV or NumPy is unavailable, the route returns `503` and does not claim an estimate.

Image inference is optional. From the repository root, install its dependencies into the backend environment with:

```powershell
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-vision.txt
```

This command is not run automatically; without these optional dependencies, image inference remains unavailable.

## AI recommendations and explanations

### `GET /api/ai/recommendations`

Builds recommendations from the current database's rooms, occupancy observations, timetable entries, and equipment inventory, then calls Member 4's `generate_recommendations`. The route does not load `simulation_scenarios.csv` or fabricate simulator results. Recommendations preserve source/provenance and limitations; estimated energy and cost impacts remain `null` unless supplied by a real simulator result. Synthetic and stale occupancy observations are handled according to the recommendation module's rules.

### `POST /api/ai/explanations`

Explains the supplied `simulation_result` object and optional `campus_context`. Because this endpoint does not re-run the simulation, it labels the payload as caller-supplied and unverified. With `ECOTWIN_LLM_API_KEY` configured, the backend makes an OpenAI-compatible chat completions request and returns `source: "language_model"` on success. The deterministic simulator's `feasible` field remains authoritative. Without a key or when the provider is unavailable, a deterministic fallback is returned.

### `POST /api/ai/chat`

Accepts `{ "question": "..." }` (1–2,000 characters). The backend builds context from database rooms, timetable entries, and recent occupancy observations, then calls the configured language model. The model is instructed to use only this context and not invent unavailable values. Successful model responses are tagged `source: "language_model"`; if credentials are missing or provider errors occur, the response is tagged `deterministic_fallback` and identifies that the live explanation is unavailable. No credentials are returned to the frontend.

Configure the optional model in `.env` or the backend process environment using `ECOTWIN_LLM_API_KEY`, `ECOTWIN_LLM_BASE_URL` (defaults to `https://api.openai.com/v1`), `ECOTWIN_LLM_MODEL` (defaults to `gpt-4o-mini`), and `ECOTWIN_LLM_TIMEOUT_SECONDS` (defaults to 20). The backend loads `.env` at startup. See `.env.example`. Tests mock the completion transport; a live provider call has not been verified unless configured separately.

## Simulations

### `POST /api/simulations`

Requires a valid timetable entry, exact source and destination room IDs, and accepts class counts only when known:

```json
{
  "timetable_entry_id": "TT0001",
  "source_room_id": "A-F1-04",
  "target_room_id": "A-G03",
  "student_count": 30,
  "affected_student_counts": {
    "TT0031": 25
  }
}
```

The endpoint uses the records in the current database, not scenario CSV examples. It validates that the selected entry and both rooms exist, that source and destination differ, and that the source matches the selected entry. It preserves every moved entry's semester, section, day, and time. A destination must be timetable-eligible; the selected entry's capacity is checked only when `student_count` is supplied.

**Overlap and resource constraints:** time intervals overlap when `start_a < end_b` and `start_b < end_a`; consecutive entries that meet at an endpoint do not overlap. Comparisons are limited to the same semester and day, consistent with the independent semester schedules in this dataset. The evaluator checks same-room overlaps and checks overlapping affected entries against other entries for a shared non-empty `faculty_id` or a shared `(department, section)` identity. A failed faculty or section check makes the proposal infeasible; missing identifiers on overlapping entries make the result incomplete. The check is limited to conflicts involving entries moved by the proposal; it is not a validation of every pre-existing timetable conflict.

A ripple is an additional timetable entry that must be assigned a different room because it overlaps a moved entry in the same room. The evaluator checks destination-room overlaps, including conflicts created by cascading assignments. It uses deterministic depth-first backtracking, tries eligible rooms by smallest sufficient capacity and then room ID, prevents repeated assignment states, and stops after eight additional moved entries or 2,000 explored states. Faculty and section conflicts are evaluated after all proposed cascade assignments; moving an entry to a different room does not resolve those conflicts.

`affected_student_counts` is an optional mapping from displaced timetable-entry IDs to known nonnegative enrollment counts. A cascading move is considered capacity-valid only if its count is provided. Missing counts or reaching the search bound returns `status: "incomplete"` rather than assuming a class size. If all capacity-valid assignments fail, the result is `infeasible`. Unknown entry/room IDs return `404`; inconsistent source selection, invalid count mappings, and schema errors return `422`. Infeasible or incomplete scenario evaluations return structured results with HTTP `200`; inspect `status`, `feasible`, and `checks`, not just the HTTP code.

The response includes `effects`, `affected_entries`, `affected_entities`, `unresolved_conflicts`, `checks`, `baseline`, `proposed`, and `projected_metrics`. `checks` includes `capacity`, `destination_eligibility`, `destination_schedule`, `cascade_reassignment`, `faculty_schedule`, `section_schedule`, and `room_suitability`. Check statuses are `pass`, `fail`, `unknown`, and, for unsupported facility/equipment compatibility, `not_checked`. `unresolved_conflicts` identifies the involved timetable entries and the detected constraint types. Room `timetable_eligible` is checked, but no rules map `session_type` to a required `facility_type` or equipment set; `room_suitability` therefore remains `not_checked`, not a pass or a failure. A top-level `feasible` result means the evaluated constraints passed; it does not mean unchecked suitability or real-world feasibility is established. Per-entry capacity utilization is known class size divided by room capacity; it is not observed occupancy or time-based room utilization. All moved room IDs and corresponding per-entry before/after capacity ratios are returned when available.

An optional `occupancy_scenario` may carry an image-based observation with `room_id`, `estimated_visible_person_count`, `observed_at`, `source: "image_inference"`, and detector name. It must match either the selected entry's source room or the proposed destination. The observation is retained as scenario context only: it does not supply `student_count`, does not satisfy a missing enrollment value, and is never used for capacity checks. The frontend requires an explicit opt-in before sending this context and preserves it independently from enrollment.

Energy, cost, and walking impacts are explicitly `unavailable`: room-level daily energy estimates do not establish per-class deltas, and the dataset does not provide the affected cohorts' origins or validated route changes. The evaluator never uses `simulation_scenarios.csv` as calculated output, never persists or applies a proposed schedule, and labels synthetic/illustrative records. This bounded timetable reassignment is not a complete campus-wide ripple model or an operational approval.
## Sustainability

### `GET /api/sustainability/actions`

Returns the four supplied suggested actions, including trigger, recommendation, human-approval requirement, and `data_status`. These are suggestions only; the API does not control campus equipment.

## Error handling and scope

* `404`: referenced building, room, or timetable entry does not exist.
* `422`: invalid query/request fields or inconsistent simulation room selection.
* `503`: database unavailable or image inference dependency unavailable.
* Responses do not expose internal stack traces.
* Attendance endpoints are not implemented. Schedule mutation and a full campus-wide Ripple Effect Simulator are not integrated. Live model inference requires provider credentials and network access.
