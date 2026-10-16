from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping


def _records(value: Any) -> list[dict]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _rooms(campus_data: Mapping[str, Any]) -> list[dict]:
    direct = _records(campus_data.get("rooms"))
    if direct:
        return direct
    result = []
    for building in _records(campus_data.get("buildings")):
        for floor in _records(building.get("floors")):
            for room in _records(floor.get("rooms")):
                result.append({"building_id": building.get("building_id"), **room})
    return result


def _first(record: Mapping[str, Any], *keys: str) -> Any:
    return next((record[key] for key in keys if record.get(key) is not None), None)


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except ValueError:
        return None


def _source(record: Mapping[str, Any]) -> str:
    description = " ".join(
        str(record.get(key, ""))
        for key in ("source", "data_source", "data_status", "detection_method", "verification_status")
    ).lower()
    if "synthetic" in description or "placeholder" in description:
        return "synthetic_demo_data"
    if "manual" in description:
        return "manual_input"
    if "image" in description or "opencv" in description or "hog" in description:
        return "image_inference"
    return str(_first(record, "source", "data_source") or "unknown")


def _recommendation_id(kind: str, room_id: str | None, simulation_id: str | None) -> str:
    identity = f"{kind}|{room_id or ''}|{simulation_id or ''}"
    suffix = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:10]
    return f"REC-{suffix}"


def _make_recommendation(
    *,
    kind: str,
    title: str,
    room_id: str | None,
    building_id: str | None,
    evidence: list[str],
    data_source: str,
    observed_at: str | None,
    limitations: list[str],
    constraints: list[str],
    next_step: str,
    simulation_id: str | None = None,
    simulation_impacts: dict | None = None,
    requires_verification: bool = True,
) -> dict:
    return {
        "recommendation_id": _recommendation_id(kind, room_id, simulation_id),
        "room_id": room_id,
        "building_id": building_id,
        "title": title,
        "evidence": evidence,
        "data_source": data_source,
        "observed_at": observed_at,
        "estimated_energy_impact": None,
        "estimated_cost_impact": None,
        "simulator_reported_impacts": simulation_impacts or {},
        "confidence_limitations": limitations,
        "operational_constraints": constraints,
        "suggested_next_step": next_step,
        "simulation_id": simulation_id,
        "requires_verification": requires_verification,
    }


def generate_recommendations(
    campus_data: Mapping[str, Any],
    simulation_results: Mapping[str, Any] | list[Mapping[str, Any]] | None = None,
    *,
    now: datetime | None = None,
    max_observation_age_hours: float = 4,
    low_utilization_threshold: float = 0.25,
) -> list[dict]:
    """Return cautious, evidence-linked recommendations from supplied records only."""
    if not isinstance(campus_data, Mapping):
        raise TypeError("campus_data must be a mapping")
    if max_observation_age_hours < 0:
        raise ValueError("max_observation_age_hours must be non-negative")
    if not 0 <= low_utilization_threshold <= 1:
        raise ValueError("low_utilization_threshold must be between 0 and 1")

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    observations_by_room: dict[str, list[dict]] = {}
    for observation in _records(campus_data.get("occupancy_observations")):
        room_id = _first(observation, "room_id")
        if room_id:
            observations_by_room.setdefault(str(room_id), []).append(observation)
    timetable_by_room: dict[str, list[dict]] = {}
    for entry in _records(campus_data.get("timetable")):
        room_id = _first(entry, "room_id")
        if room_id:
            timetable_by_room.setdefault(str(room_id), []).append(entry)
    equipment_by_room: dict[str, list[dict]] = {}
    for item in _records(campus_data.get("equipment_inventory")):
        room_id = _first(item, "room_id")
        if room_id:
            equipment_by_room.setdefault(str(room_id), []).append(item)

    recommendations = []
    for room in _rooms(campus_data):
        room_id = _first(room, "room_id")
        if not room_id:
            continue
        room_id = str(room_id)
        candidates = observations_by_room.get(room_id, [])
        observation = max(
            candidates,
            key=lambda item: _timestamp(_first(item, "observed_at", "observation_timestamp"))
            or datetime.min.replace(tzinfo=timezone.utc),
            default=None,
        )
        observation = observation or _first(room, "latest_occupancy")
        observation = observation if isinstance(observation, Mapping) else {}
        observed_at = _first(observation, "observed_at", "observation_timestamp", "timestamp")
        parsed_time = _timestamp(observed_at)
        is_stale = parsed_time is None or (current_time - parsed_time).total_seconds() > max_observation_age_hours * 3600
        data_source = _source(observation)
        synthetic = data_source == "synthetic_demo_data"

        if is_stale:
            reason = "No occupancy observation is available" if not observation else "Occupancy observation is stale"
            timestamp_note = "timestamp is unavailable or invalid" if parsed_time is None else f"observation at {observed_at}"
            recommendations.append(_make_recommendation(
                kind="occupancy_freshness",
                title=f"Verify current occupancy for {room_id}",
                room_id=room_id,
                building_id=_first(room, "building_id"),
                evidence=[f"{reason}; {timestamp_note}."],
                data_source=data_source,
                observed_at=observed_at,
                limitations=["Occupancy status cannot be inferred from missing or stale observations."],
                constraints=["Check the timetable and room access before taking operational action."],
                next_step="Capture a current, consent-compliant observation or record a verified manual count.",
            ))
            continue

        count = _first(observation, "detected_person_count", "observed_person_count", "estimated_occupancy")
        capacity = _first(room, "capacity_students", "capacity") or _first(observation, "room_capacity", "capacity")
        try:
            low_utilization = count is not None and capacity is not None and float(capacity) > 0 and float(count) / float(capacity) < low_utilization_threshold
        except (TypeError, ValueError):
            low_utilization = False
        if not low_utilization:
            continue

        equipment = equipment_by_room.get(room_id, []) + _records(room.get("equipment_inventory"))
        active_equipment = [
            item for item in equipment
            if _first(item, "is_operating", "operating", "is_active", "active", "power_state") is True
            or str(_first(item, "is_operating", "operating", "is_active", "active", "power_state") or "").lower()
            in {"on", "operating", "active", "true", "yes"}
        ]
        if active_equipment:
            equipment_source = _source(active_equipment[0])
            equipment_limitations = ["An equipment status is not independent metered-energy evidence."]
            if equipment_source == "synthetic_demo_data":
                equipment_limitations.append("The equipment status is synthetic demonstration data and must be verified on site.")
            labels = [str(_first(item, "equipment_type", "name", "equipment_id") or "equipment") for item in active_equipment]
            recommendations.append(_make_recommendation(
                kind="equipment_state_review",
                title=f"Verify equipment operation during low occupancy in {room_id}",
                room_id=room_id,
                building_id=_first(room, "building_id"),
                evidence=[f"Occupancy count {count} was observed while supplied equipment status reported operating: {', '.join(labels)}."],
                data_source=equipment_source,
                observed_at=observed_at,
                limitations=equipment_limitations,
                constraints=["Confirm the actual operating state and scheduled use; no energy consumption or waste is inferred."],
                next_step="Ask authorized facilities staff to verify the equipment controls and operating schedule.",
            ))

        entries = timetable_by_room.get(room_id, [])
        if entries:
            constraints = [f"{len(entries)} timetable entr{'y' if len(entries) == 1 else 'ies'} reference this room; verify the applicable day and period."]
        else:
            constraints = ["Timetable availability was not supplied; check scheduling before any room change."]
        limitations = ["A single low count does not establish that a room is unused."]
        if synthetic:
            limitations.append("The occupancy observation is synthetic demonstration data and is not verified evidence.")
        recommendations.append(_make_recommendation(
            kind="low_utilization_review",
            title=f"Review observed utilization for {room_id}",
            room_id=room_id,
            building_id=_first(room, "building_id"),
            evidence=[f"Observed count {count} against supplied capacity {capacity} ({observed_at})."],
            data_source=data_source,
            observed_at=observed_at,
            limitations=limitations,
            constraints=constraints,
            next_step="Compare repeated observations with the timetable, then run a validated relocation simulation if appropriate.",
        ))

    if simulation_results is not None:
        for result in _records(simulation_results):
            simulation_id = _first(result, "simulation_id", "scenario_id")
            feasible = _first(result, "feasible", "is_feasible")
            errors = _first(result, "validation_errors", "errors") or []
            if feasible is None and not errors:
                continue
            if not isinstance(errors, list):
                errors = [errors]
            impacts = {
                key: result[key]
                for key in (
                    "baseline_energy_kwh_day", "proposed_energy_kwh_day", "energy_saved_kwh_day",
                    "energy_change_kwh", "cost_saved_inr_day", "cost_change_inr",
                    "baseline_walk_m_day", "proposed_walk_m_day", "walking_distance_change_m_day",
                )
                if key in result
            }
            if feasible is True:
                title = "Review feasible relocation results"
                next_step = "Have the scheduling owner review validation and confirm operational constraints before approval."
            elif feasible is False:
                title = "Revise rejected relocation proposal"
                next_step = "Resolve each simulator validation error and rerun the scenario before considering the move."
            else:
                title = "Review relocation validation"
                next_step = "Confirm the simulator feasibility status and resolve any reported validation errors before review."
            source = _source(result)
            limitations = ["Simulator-reported impacts are passed through as supplied; this module does not recalculate them."]
            if source == "synthetic_demo_data":
                limitations.append("The simulator result is synthetic demonstration data and is not a verified campus outcome.")
            recommendations.append(_make_recommendation(
                kind="simulation_review",
                title=title,
                room_id=_first(result, "source_room_id", "room_id"),
                building_id=_first(result, "building_id"),
                evidence=[f"Simulator feasibility: {feasible!r}."] + [str(error) for error in errors],
                data_source=source if source != "unknown" else "simulator_result; provenance not specified",
                observed_at=_first(result, "observed_at", "created_at"),
                limitations=limitations,
                constraints=[str(error) for error in errors],
                next_step=next_step,
                simulation_id=str(simulation_id) if simulation_id is not None else None,
                simulation_impacts=impacts,
            ))

    return recommendations