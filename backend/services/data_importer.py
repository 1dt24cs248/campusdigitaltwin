import math
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from sqlalchemy.orm import Session

from backend.models import (
    Building,
    EnergyRecord,
    Equipment,
    OccupancyObservation,
    Room,
    RoomDistance,
    SustainabilityAction,
    TimetableEntry,
)


class DatasetImportError(ValueError):
    pass


@dataclass(frozen=True)
class RowIssue:
    file: str
    row: int
    message: str


@dataclass
class DatasetImportResult:
    source_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    rejected: int = 0


@dataclass
class ImportReport:
    datasets: dict[str, DatasetImportResult] = field(default_factory=dict)
    issues: list[RowIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "datasets": {name: asdict(result) for name, result in self.datasets.items()},
            "issues": [asdict(issue) for issue in self.issues],
        }

    @property
    def rejected_rows(self) -> int:
        return sum(result.rejected for result in self.datasets.values())


@dataclass(frozen=True)
class DatasetSpec:
    filename: str
    model: type
    primary_key: str
    columns: tuple[str, ...]
    convert: Callable[[dict[str, str]], dict[str, Any]]


def _text(row: dict[str, str], name: str, *, allow_blank: bool = False) -> str:
    value = row[name].strip()
    if not value and not allow_blank:
        raise ValueError(f"{name} is required")
    return value


def _integer(
    row: dict[str, str],
    name: str,
    *,
    minimum: int | None = None,
    optional: bool = False,
) -> int | None:
    raw = row[name].strip()
    if optional and not raw:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _number(
    row: dict[str, str],
    name: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    optional: bool = False,
) -> float | None:
    raw = row[name].strip()
    if optional and not raw:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return value


def _boolean(row: dict[str, str], name: str) -> bool:
    value = row[name].strip().casefold()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _date(row: dict[str, str], name: str) -> date:
    try:
        return date.fromisoformat(row[name].strip())
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD format") from exc


def _time(row: dict[str, str], name: str) -> time:
    try:
        return time.fromisoformat(row[name].strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid time") from exc


def _building(row: dict[str, str]) -> dict[str, Any]:
    return {
        "building_id": _text(row, "building_id"),
        "building_name": _text(row, "building_name"),
        "data_status": _text(row, "data_status"),
    }


def _room(row: dict[str, str]) -> dict[str, Any]:
    return {
        "room_id": _text(row, "room_id"),
        "building_id": _text(row, "building_id"),
        "building_name": _text(row, "building_name"),
        "floor_number": _integer(row, "floor_number"),
        "floor_name": _text(row, "floor_name"),
        "room_name": _text(row, "room_name"),
        "facility_type": _text(row, "facility_type"),
        "department": _text(row, "department"),
        "capacity_students": _integer(row, "capacity_students", minimum=0),
        "estimated_connected_load_kw": _number(row, "estimated_connected_load_kw", minimum=0),
        "timetable_eligible": _boolean(row, "timetable_eligible"),
        "data_status": _text(row, "data_status"),
        "notes": _text(row, "notes", allow_blank=True),
    }


def _timetable(row: dict[str, str]) -> dict[str, Any]:
    start_time = _time(row, "start_time")
    end_time = _time(row, "end_time")
    if start_time >= end_time:
        raise ValueError("start_time must be earlier than end_time")
    return {
        "timetable_entry_id": _text(row, "timetable_entry_id"),
        "semester": _integer(row, "semester", minimum=1),
        "section": _text(row, "section"),
        "department": _text(row, "department"),
        "day_of_week": _text(row, "day_of_week"),
        "period_number": _integer(row, "period_number", minimum=1),
        "start_time": start_time,
        "end_time": end_time,
        "subject_code": _text(row, "subject_code"),
        "subject_name": _text(row, "subject_name"),
        "room_id": _text(row, "room_id"),
        "faculty_id": _text(row, "faculty_id"),
        "session_type": _text(row, "session_type"),
        "data_status": _text(row, "data_status"),
    }


def _equipment(row: dict[str, str]) -> dict[str, Any]:
    return {
        "equipment_id": _text(row, "equipment_id"),
        "room_id": _text(row, "room_id"),
        "equipment_type": _text(row, "equipment_type"),
        "quantity": _integer(row, "quantity", minimum=0),
        "unit_power_watts": _number(row, "unit_power_watts", minimum=0),
        "total_power_watts": _number(row, "total_power_watts", minimum=0),
        "assumed_daily_hours": _number(row, "assumed_daily_hours", minimum=0, maximum=24),
        "assumed_days_per_week": _integer(row, "assumed_days_per_week", minimum=0),
        "data_status": _text(row, "data_status"),
        "notes": _text(row, "notes", allow_blank=True),
    }


def _energy(row: dict[str, str]) -> dict[str, Any]:
    return {
        "energy_record_id": _text(row, "energy_record_id"),
        "room_id": _text(row, "room_id"),
        "record_date": _date(row, "record_date"),
        "estimated_energy_kwh_per_day": _number(row, "estimated_energy_kwh_per_day", minimum=0),
        "estimated_energy_kwh_per_week": _number(row, "estimated_energy_kwh_per_week", minimum=0),
        "electricity_tariff_inr_per_kwh": _number(row, "electricity_tariff_inr_per_kwh", minimum=0),
        "estimated_cost_inr_per_week": _number(row, "estimated_cost_inr_per_week", minimum=0),
        "calculation_method": _text(row, "calculation_method"),
        "data_status": _text(row, "data_status"),
        "notes": _text(row, "notes", allow_blank=True),
    }


def _occupancy(row: dict[str, str]) -> dict[str, Any]:
    observed_at = _text(row, "observed_at")
    try:
        datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be an ISO 8601 timestamp") from exc
    return {
        "observation_id": _text(row, "observation_id"),
        "room_id": _text(row, "room_id"),
        "observed_at": observed_at,
        "detected_person_count": _integer(row, "detected_person_count", minimum=0),
        "room_capacity": _integer(row, "room_capacity", minimum=0, optional=True),
        "occupancy_percent": _number(row, "occupancy_percent", minimum=0, optional=True),
        "detection_method": _text(row, "detection_method"),
        "confidence_score": _number(row, "confidence_score", minimum=0, maximum=1, optional=True),
        "verified_by_human": _boolean(row, "verified_by_human"),
        "data_status": _text(row, "data_status"),
    }


def _distance(row: dict[str, str]) -> dict[str, Any]:
    return {
        "distance_id": _text(row, "distance_id"),
        "from_room_id": _text(row, "from_room_id"),
        "to_room_id": _text(row, "to_room_id"),
        "estimated_walking_distance_m": _number(row, "estimated_walking_distance_m", minimum=0),
        "distance_method": _text(row, "distance_method"),
        "data_status": _text(row, "data_status"),
    }


def _action(row: dict[str, str]) -> dict[str, Any]:
    return {
        "action_id": _text(row, "action_id"),
        "action_name": _text(row, "action_name"),
        "category": _text(row, "category"),
        "priority": _text(row, "priority"),
        "trigger_condition": _text(row, "trigger_condition"),
        "suggested_action": _text(row, "suggested_action"),
        "requires_human_approval": _boolean(row, "requires_human_approval"),
        "data_status": _text(row, "data_status"),
    }


_DATASETS = (
    DatasetSpec("buildings.csv", Building, "building_id", (
        "building_id", "building_name", "data_status",
    ), _building),
    DatasetSpec("rooms.csv", Room, "room_id", (
        "room_id", "building_id", "building_name", "floor_number", "floor_name", "room_name",
        "facility_type", "department", "capacity_students", "estimated_connected_load_kw",
        "timetable_eligible", "data_status", "notes",
    ), _room),
    DatasetSpec("timetable.csv", TimetableEntry, "timetable_entry_id", (
        "timetable_entry_id", "semester", "section", "department", "day_of_week", "period_number",
        "start_time", "end_time", "subject_code", "subject_name", "room_id", "faculty_id",
        "session_type", "data_status",
    ), _timetable),
    DatasetSpec("equipment_inventory.csv", Equipment, "equipment_id", (
        "equipment_id", "room_id", "equipment_type", "quantity", "unit_power_watts",
        "total_power_watts", "assumed_daily_hours", "assumed_days_per_week", "data_status", "notes",
    ), _equipment),
    DatasetSpec("energy_records.csv", EnergyRecord, "energy_record_id", (
        "energy_record_id", "room_id", "record_date", "estimated_energy_kwh_per_day",
        "estimated_energy_kwh_per_week", "electricity_tariff_inr_per_kwh",
        "estimated_cost_inr_per_week", "calculation_method", "data_status", "notes",
    ), _energy),
    DatasetSpec("occupancy_observations.csv", OccupancyObservation, "observation_id", (
        "observation_id", "room_id", "observed_at", "detected_person_count", "room_capacity",
        "occupancy_percent", "detection_method", "confidence_score", "verified_by_human", "data_status",
    ), _occupancy),
    DatasetSpec("room_distances.csv", RoomDistance, "distance_id", (
        "distance_id", "from_room_id", "to_room_id", "estimated_walking_distance_m",
        "distance_method", "data_status",
    ), _distance),
    DatasetSpec("sustainability_actions.csv", SustainabilityAction, "action_id", (
        "action_id", "action_name", "category", "priority", "trigger_condition", "suggested_action",
        "requires_human_approval", "data_status",
    ), _action),
)


def _load_files(data_dir: Path) -> dict[str, list[dict[str, str]]]:
    loaded: dict[str, list[dict[str, str]]] = {}
    for spec in _DATASETS:
        path = data_dir / spec.filename
        if not path.is_file():
            raise DatasetImportError(f"Required dataset is missing: {path}")
        try:
            frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        except (OSError, pd.errors.ParserError, UnicodeError) as exc:
            raise DatasetImportError(f"Could not read {path}: {exc}") from exc
        missing = [column for column in spec.columns if column not in frame.columns]
        if missing:
            raise DatasetImportError(
                f"Unexpected schema in {path}; missing required columns: {', '.join(missing)}"
            )
        loaded[spec.filename] = frame.to_dict(orient="records")
    return loaded


def _validate_foreign_keys(session: Session, filename: str, values: dict[str, Any]) -> None:
    if filename == "rooms.csv" and session.get(Building, values["building_id"]) is None:
        raise ValueError(f"unknown building_id {values['building_id']}")
    if filename in {
        "timetable.csv", "equipment_inventory.csv", "energy_records.csv", "occupancy_observations.csv",
    } and session.get(Room, values["room_id"]) is None:
        raise ValueError(f"unknown room_id {values['room_id']}")
    if filename == "room_distances.csv":
        for field_name in ("from_room_id", "to_room_id"):
            room_id = values[field_name]
            if session.get(Room, room_id) is None:
                raise ValueError(f"unknown {field_name} {room_id}")


def import_datasets(data_dir: Path, session: Session) -> ImportReport:
    """Import supported CSVs, updating changed IDs and skipping unchanged rows."""
    loaded = _load_files(Path(data_dir))
    report = ImportReport()

    for spec in _DATASETS:
        source_rows = loaded[spec.filename]
        result = DatasetImportResult(source_rows=len(source_rows))
        report.datasets[spec.filename] = result

        for row_number, row in enumerate(source_rows, start=2):
            try:
                values = spec.convert(row)
                _validate_foreign_keys(session, spec.filename, values)
            except (KeyError, TypeError, ValueError) as exc:
                result.rejected += 1
                report.issues.append(RowIssue(spec.filename, row_number, str(exc)))
                continue

            record_id = values[spec.primary_key]
            existing = session.get(spec.model, record_id)
            if existing is None:
                session.add(spec.model(**values))
                result.inserted += 1
                continue

            changed = False
            for field_name, value in values.items():
                if getattr(existing, field_name) != value:
                    setattr(existing, field_name, value)
                    changed = True
            if changed:
                result.updated += 1
            else:
                result.skipped += 1

        session.flush()

    session.commit()
    return report
