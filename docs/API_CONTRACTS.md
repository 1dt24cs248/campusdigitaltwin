# EcoTwin AI Backend API Contracts

Base URL for local development: `http://127.0.0.1:8000`

All campus records currently imported from the canonical dataset are synthetic or illustrative. `data_status` is returned with records and must be shown as provenance, not interpreted as a claim that data is measured or live.

## Local setup

From the repository root, create and use a Python 3.11 environment:

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python.exe -m backend.seed_data
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run tests with:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

The importer reads `data/raw/ecotwin_dataset/`. It imports buildings, rooms, timetable entries, equipment, energy estimates, occupancy observations, room distances, and sustainability actions. It validates required columns and row values, checks room/building references, then reports source, inserted, updated, skipped, and rejected counts. Existing IDs are updated only if values differ; unchanged rows are skipped. The import is repeatable and does not delete existing rows or recreate the database.

SQLite defaults to `backend/ecotwin.db`. Set `ECOTWIN_DATABASE_URL` to override it. `ECOTWIN_CORS_ORIGINS` accepts comma-separated origins; by default only `http://localhost:5173` and `http://127.0.0.1:5173` are enabled.

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

## Simulations

### `POST /api/simulations`

Requires a valid timetable entry, source and target room IDs, and accepts optional `student_count` only when known:

```json
{
  "timetable_entry_id": "TT0001",
  "source_room_id": "A-F1-04",
  "target_room_id": "A-F2-01"
}
```

The endpoint validates that the entry and rooms exist, that source and target differ, and that the source matches the selected entry. No simulator implementation is present in this workspace, so a valid request currently returns `503`:

```json
{
  "detail": {
    "status": "integration_pending",
    "message": "No simulator module is available; no simulation was calculated."
  }
}
```

It does not return sample scenario values as if calculated, persist a result, or estimate savings. The backend is ready to call a teammate simulator once its interface is available; no compatible module contract has been supplied yet.

Expected teammate adapter boundary (contract only; not implemented): `evaluate_relocation(request) -> result`. The request contains `timetable_entry_id`, `source_room_id`, `target_room_id`, and optional `student_count`; missing student counts must remain unknown. The result should include `feasible`, validation findings, capacity and timetable checks, affected timetable entries/rooms, energy/cost/walking-distance changes with units, assumptions, warnings, and data provenance/status. Define each change as **proposed minus baseline**: a negative energy or cost value means an estimated reduction, and a negative walking-distance value means an estimated shorter walk. The API adapter must validate the returned structure before serializing it. Reference rows in `simulation_scenarios.csv` are examples only and are not valid results for new requests.

## Sustainability

### `GET /api/sustainability/actions`

Returns the four supplied suggested actions, including trigger, recommendation, human-approval requirement, and `data_status`. These are suggestions only; the API does not control campus equipment.

## Error handling and scope

* `404`: referenced building, room, or timetable entry does not exist.
* `422`: invalid query/request fields or inconsistent simulation room selection.
* `503`: database unavailable or simulator integration pending.
* Responses do not expose internal stack traces.
* Attendance endpoints and AI-generated explanations are not implemented in this milestone.
