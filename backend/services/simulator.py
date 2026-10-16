import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Room, TimetableEntry
from backend.schemas import SimulationRequest

_MAX_CASCADE_ENTRIES = 8
_MAX_SEARCH_STATES = 2_000


class SimulationNotFoundError(LookupError):
    pass


class SimulationInputError(ValueError):
    pass


def _overlaps(first: TimetableEntry, second: TimetableEntry) -> bool:
    return first.start_time < second.end_time and second.start_time < first.end_time


def _room_metrics(room: Room, student_count: int | None) -> dict[str, Any]:
    utilization = None
    if student_count is not None and room.capacity_students > 0:
        utilization = round(student_count / room.capacity_students * 100, 2)
    return {
        "room_id": room.room_id,
        "capacity_students": room.capacity_students,
        "allocated_students": student_count,
        "allocation_utilization_percent": utilization,
        "data_status": room.data_status,
    }


def _schedule_conflicts(
    entries: list[TimetableEntry],
    assignments: dict[str, str],
) -> list[tuple[TimetableEntry, TimetableEntry]]:
    by_id = {entry.timetable_entry_id: entry for entry in entries}
    affected_ids = {
        entry_id for entry_id, room_id in assignments.items()
        if room_id != by_id[entry_id].room_id
    }
    pairs: dict[tuple[str, str], tuple[TimetableEntry, TimetableEntry]] = {}
    for entry_id in sorted(affected_ids):
        entry = by_id[entry_id]
        room_id = assignments[entry_id]
        for other in entries:
            if other.timetable_entry_id == entry_id:
                continue
            other_room_id = assignments.get(other.timetable_entry_id, other.room_id)
            if (
                other_room_id == room_id
                and other.semester == entry.semester
                and other.day_of_week == entry.day_of_week
                and _overlaps(entry, other)
            ):
                key = tuple(sorted((entry_id, other.timetable_entry_id)))
                pairs[key] = (by_id[key[0]], by_id[key[1]])
    return [pairs[key] for key in sorted(pairs)]


def _resource_schedule_conflicts(
    entries: list[TimetableEntry],
    assignments: dict[str, str],
) -> tuple[dict[str, set[tuple[str, str]]], dict[str, set[str]]]:
    by_id = {entry.timetable_entry_id: entry for entry in entries}
    affected_ids = {
        entry_id for entry_id, room_id in assignments.items()
        if room_id != by_id[entry_id].room_id
    }
    conflicts = {"faculty": set(), "section": set()}
    unknown_entries = {"faculty": set(), "section": set()}
    compared_pairs: set[tuple[str, str]] = set()

    for entry_id in sorted(affected_ids):
        entry = by_id[entry_id]
        for other in entries:
            if (
                other.timetable_entry_id == entry_id
                or other.semester != entry.semester
                or other.day_of_week != entry.day_of_week
                or not _overlaps(entry, other)
            ):
                continue
            pair = tuple(sorted((entry_id, other.timetable_entry_id)))
            if pair in compared_pairs:
                continue
            compared_pairs.add(pair)

            faculty_id = entry.faculty_id.strip()
            other_faculty_id = other.faculty_id.strip()
            if not faculty_id or not other_faculty_id:
                unknown_entries["faculty"].update(
                    current.timetable_entry_id
                    for current in (entry, other)
                    if not current.faculty_id.strip()
                )
            elif faculty_id == other_faculty_id:
                conflicts["faculty"].add(pair)

            section_key = (entry.department.strip(), entry.section.strip())
            other_section_key = (other.department.strip(), other.section.strip())
            if not all(section_key) or not all(other_section_key):
                unknown_entries["section"].update(
                    current.timetable_entry_id
                    for current in (entry, other)
                    if not current.department.strip() or not current.section.strip()
                )
            elif section_key == other_section_key:
                conflicts["section"].add(pair)

    return conflicts, unknown_entries


def _resource_check(
    name: str,
    conflicts: set[tuple[str, str]],
    unknown_entries: set[str],
) -> dict[str, str]:
    messages = []
    if conflicts:
        message = "; ".join(f"{first} and {second}" for first, second in sorted(conflicts))
        messages.append(f"Overlapping timetable entries share {name}: {message}.")
    if unknown_entries:
        messages.append(
            f"Could not check {name} for entries with missing identifiers: "
            + ", ".join(sorted(unknown_entries))
            + "."
        )
    if conflicts:
        status = "fail"
    elif unknown_entries:
        status = "unknown"
    else:
        status = "pass"
        messages.append(f"No overlapping entries share {name}.")
    return {"status": status, "message": " ".join(messages)}


def _find_cascade_assignments(
    *,
    entries: list[TimetableEntry],
    rooms: list[Room],
    initial_entry_id: str,
    initial_target_room_id: str,
    student_counts: dict[str, int],
) -> tuple[dict[str, str] | None, set[str], bool, int]:
    by_id = {entry.timetable_entry_id: entry for entry in entries}
    eligible_rooms = [room for room in rooms if room.timetable_eligible]
    visited: set[tuple[tuple[str, str], ...]] = set()
    unknown_size_entries: set[str] = set()
    explored = 0
    search_limit_reached = False

    def solve(assignments: dict[str, str]) -> dict[str, str] | None:
        nonlocal explored, search_limit_reached
        signature = tuple(sorted(assignments.items()))
        if signature in visited:
            return None
        visited.add(signature)
        explored += 1
        if explored > _MAX_SEARCH_STATES:
            search_limit_reached = True
            return None

        conflicts = _schedule_conflicts(entries, assignments)
        if not conflicts:
            return assignments

        first, second = conflicts[0]
        pair = (first, second)
        moved = [entry for entry in pair if entry.timetable_entry_id in assignments]
        unmoved = [entry for entry in pair if entry.timetable_entry_id not in assignments]
        move_options = [*unmoved, *[entry for entry in moved if entry.timetable_entry_id != initial_entry_id]]
        move_options.sort(
            key=lambda entry: (
                entry.timetable_entry_id in assignments,
                entry.timetable_entry_id,
            )
        )

        for entry in move_options:
            entry_id = entry.timetable_entry_id
            if len(assignments) - 1 >= _MAX_CASCADE_ENTRIES:
                search_limit_reached = True
                return None
            student_count = student_counts.get(entry_id)
            if student_count is None:
                unknown_size_entries.add(entry_id)
                continue

            current_room_id = assignments.get(entry_id, entry.room_id)
            candidates = sorted(
                (
                    room for room in eligible_rooms
                    if room.room_id != current_room_id
                    and room.capacity_students >= student_count
                ),
                key=lambda room: (room.capacity_students, room.room_id),
            )
            for room in candidates:
                next_assignments = dict(assignments)
                next_assignments[entry_id] = room.room_id
                result = solve(next_assignments)
                if result is not None:
                    return result
                if search_limit_reached:
                    return None
        return None

    result = solve({initial_entry_id: initial_target_room_id})
    return result, unknown_size_entries, search_limit_reached, explored


def evaluate_relocation(request: SimulationRequest, db: Session) -> dict[str, Any]:
    entry = db.get(TimetableEntry, request.timetable_entry_id)
    if entry is None:
        raise SimulationNotFoundError("Timetable entry not found")

    source = db.get(Room, request.source_room_id)
    if source is None:
        raise SimulationNotFoundError("Source room not found")
    target = db.get(Room, request.target_room_id)
    if target is None:
        raise SimulationNotFoundError("Target room not found")
    if request.source_room_id == request.target_room_id:
        raise SimulationInputError("Source and target rooms must differ")
    if entry.room_id != request.source_room_id:
        raise SimulationInputError("source_room_id does not match the selected timetable entry")
    if request.occupancy_scenario and request.occupancy_scenario.room_id not in {
        source.room_id, target.room_id,
    }:
        raise SimulationInputError(
            "Occupancy context must belong to the selected source or destination room"
        )

    entries = list(db.scalars(
        select(TimetableEntry).order_by(
            TimetableEntry.semester,
            TimetableEntry.day_of_week,
            TimetableEntry.start_time,
            TimetableEntry.timetable_entry_id,
        )
    ))
    rooms = list(db.scalars(select(Room).order_by(Room.room_id)))
    entries_by_id = {candidate.timetable_entry_id: candidate for candidate in entries}
    unknown_size_ids = set(request.affected_student_counts) - set(entries_by_id)
    if unknown_size_ids:
        raise SimulationInputError(
            "affected_student_counts contains unknown timetable entry IDs: "
            + ", ".join(sorted(unknown_size_ids))
        )
    if entry.timetable_entry_id in request.affected_student_counts:
        raise SimulationInputError(
            "Use student_count for the selected timetable entry, not affected_student_counts"
        )

    student_counts = dict(request.affected_student_counts)
    if request.student_count is not None:
        student_counts[entry.timetable_entry_id] = request.student_count

    if request.student_count is None:
        capacity_check = {
            "status": "unknown",
            "message": "Student count was not supplied; destination capacity cannot be verified.",
        }
    elif request.student_count > target.capacity_students:
        capacity_check = {
            "status": "fail",
            "message": (
                f"Destination capacity {target.capacity_students} is below the requested "
                f"student count {request.student_count}."
            ),
        }
    else:
        capacity_check = {
            "status": "pass",
            "message": f"Destination capacity {target.capacity_students} accommodates {request.student_count} students.",
        }

    eligibility_check = {
        "status": "pass" if target.timetable_eligible else "fail",
        "message": (
            "Destination is marked timetable-eligible."
            if target.timetable_eligible
            else "Destination is not marked timetable-eligible."
        ),
    }

    failed_initial_checks = [
        check for check in (capacity_check, eligibility_check) if check["status"] == "fail"
    ]
    assignments: dict[str, str] | None = None
    unknown_size_entries: set[str] = set()
    search_limit_reached = False
    explored_states = 0
    if not failed_initial_checks:
        assignments, unknown_size_entries, search_limit_reached, explored_states = _find_cascade_assignments(
            entries=entries,
            rooms=rooms,
            initial_entry_id=entry.timetable_entry_id,
            initial_target_room_id=target.room_id,
            student_counts=student_counts,
        )

    resolved_assignments = assignments or {entry.timetable_entry_id: target.room_id}
    unresolved_conflicts = _schedule_conflicts(entries, resolved_assignments)
    if assignments is not None:
        schedule_check = {
            "status": "pass",
            "message": "No overlaps remain among the proposed relocation and its affected entries.",
        }
        cascade_check = {
            "status": "pass",
            "message": f"Resolved all overlaps using {max(0, len(assignments) - 1)} cascading reassignment(s).",
        }
    elif failed_initial_checks:
        direct_conflicts = _schedule_conflicts(entries, {entry.timetable_entry_id: target.room_id})
        schedule_check = {
            "status": "fail" if direct_conflicts else "pass",
            "message": (
                f"The proposed destination overlaps {len(direct_conflicts)} timetable entr"
                f"{'y' if len(direct_conflicts) == 1 else 'ies'}; no cascade search ran because "
                "the destination failed an initial validation check."
                if direct_conflicts
                else "No direct destination overlap was found; no cascade search ran because the destination failed an initial validation check."
            ),
        }
        cascade_check = {
            "status": "not_evaluated",
            "message": "Cascading reassignment was not evaluated because an initial destination check failed.",
        }
    elif unknown_size_entries or search_limit_reached:
        reasons = []
        if unknown_size_entries:
            reasons.append(
                "Student counts are required to validate capacity for: "
                + ", ".join(sorted(unknown_size_entries))
            )
        if search_limit_reached:
            reasons.append("The bounded reassignment search limit was reached.")
        schedule_check = {"status": "unknown", "message": " ".join(reasons)}
        cascade_check = {"status": "unknown", "message": " ".join(reasons)}
    else:
        schedule_check = {
            "status": "fail",
            "message": "No capacity-valid, conflict-free room assignment was found for the affected entries.",
        }
        cascade_check = {
            "status": "fail",
            "message": "At least one conflict cannot be reassigned to an eligible room with sufficient capacity.",
        }

    resource_conflicts, unknown_resource_entries = _resource_schedule_conflicts(
        entries,
        resolved_assignments,
    )
    faculty_check = _resource_check(
        "a faculty identifier",
        resource_conflicts["faculty"],
        unknown_resource_entries["faculty"],
    )
    section_check = _resource_check(
        "the same section within a department",
        resource_conflicts["section"],
        unknown_resource_entries["section"],
    )
    room_suitability_check = {
        "status": "not_checked",
        "message": (
            "Facility and equipment compatibility with session_type is not checked; "
            "the available records do not define required facility or equipment rules."
        ),
    }
    checks = {
        "capacity": capacity_check,
        "destination_eligibility": eligibility_check,
        "destination_schedule": schedule_check,
        "cascade_reassignment": cascade_check,
        "faculty_schedule": faculty_check,
        "section_schedule": section_check,
        "room_suitability": room_suitability_check,
    }
    failed_checks = [check for check in checks.values() if check["status"] == "fail"]
    unknown_checks = [check for check in checks.values() if check["status"] == "unknown"]
    if failed_checks:
        result_status = "infeasible"
        feasible: bool | None = False
    elif unknown_checks:
        result_status = "incomplete"
        feasible = None
    else:
        result_status = "feasible"
        feasible = True

    validation_errors = [check["message"] for check in failed_checks]
    warnings = [check["message"] for check in unknown_checks]
    moved_ids = sorted(
        (
            affected_id for affected_id, room_id in resolved_assignments.items()
            if room_id != entries_by_id[affected_id].room_id
        ),
        key=lambda affected_id: (affected_id != entry.timetable_entry_id, affected_id),
    )
    moved_entries = [
        {
            "timetable_entry_id": affected_id,
            "subject_code": entries_by_id[affected_id].subject_code,
            "section": entries_by_id[affected_id].section,
            "semester": entries_by_id[affected_id].semester,
            "day_of_week": entries_by_id[affected_id].day_of_week,
            "start_time": entries_by_id[affected_id].start_time.isoformat(),
            "end_time": entries_by_id[affected_id].end_time.isoformat(),
            "source_room_id": entries_by_id[affected_id].room_id,
            "target_room_id": resolved_assignments[affected_id],
            "student_count": student_counts.get(affected_id),
        }
        for affected_id in moved_ids
    ]
    affected_room_ids = sorted({
        room_id
        for item in moved_entries
        for room_id in (item["source_room_id"], item["target_room_id"])
    })
    rooms_by_id = {room.room_id: room for room in rooms}
    utilization = [
        {
            "timetable_entry_id": item["timetable_entry_id"],
            "baseline": _room_metrics(rooms_by_id[item["source_room_id"]], item["student_count"]),
            "projected": _room_metrics(rooms_by_id[item["target_room_id"]], item["student_count"]),
        }
        for item in moved_entries
    ]
    effects = [
        {
            "effect_type": "primary_relocation" if item["timetable_entry_id"] == entry.timetable_entry_id
            else "cascading_reassignment",
            "timetable_entry_id": item["timetable_entry_id"],
            "from_room_id": item["source_room_id"],
            "to_room_id": item["target_room_id"],
            "status": "planned" if result_status == "feasible" else result_status,
        }
        for item in moved_entries
    ]
    affected_entities = [
        {"entity_type": "timetable_entry", "entity_id": item["timetable_entry_id"]}
        for item in moved_entries
    ] + [
        {"entity_type": "room", "entity_id": room_id}
        for room_id in affected_room_ids
    ]

    data_statuses = [
        entries_by_id[item["timetable_entry_id"]].data_status for item in moved_entries
    ] + [rooms_by_id[room_id].data_status for room_id in affected_room_ids]
    classification = (
        "synthetic_or_illustrative"
        if any("synthetic" in value.lower() or "illustrative" in value.lower() for value in data_statuses)
        else "database_records"
    )
    identity = {
        "timetable_entry_id": entry.timetable_entry_id,
        "source_room_id": source.room_id,
        "target_room_id": target.room_id,
        "student_count": request.student_count,
        "affected_student_counts": request.affected_student_counts,
        "occupancy_scenario": (
            request.occupancy_scenario.model_dump(mode="json")
            if request.occupancy_scenario else None
        ),
        "assignments": resolved_assignments,
        "status": result_status,
    }
    simulation_id = "SIM-" + hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    unresolved_by_pair: dict[tuple[str, str], set[str]] = {}
    for first, second in unresolved_conflicts:
        pair = tuple(sorted((first.timetable_entry_id, second.timetable_entry_id)))
        unresolved_by_pair.setdefault(pair, set()).add("room")
    for constraint, pairs in resource_conflicts.items():
        for pair in pairs:
            unresolved_by_pair.setdefault(pair, set()).add(constraint)

    return {
        "simulation_id": simulation_id,
        "status": result_status,
        "feasible": feasible,
        "scenario_inputs": {
            "timetable_entry_id": entry.timetable_entry_id,
            "source_room_id": source.room_id,
            "target_room_id": target.room_id,
            "student_count": request.student_count,
            "affected_student_counts": request.affected_student_counts,
            "occupancy_scenario": (
                request.occupancy_scenario.model_dump(mode="json")
                if request.occupancy_scenario else None
            ),
            "semester": entry.semester,
            "section": entry.section,
            "day_of_week": entry.day_of_week,
            "start_time": entry.start_time.isoformat(),
            "end_time": entry.end_time.isoformat(),
        },
        "baseline": _room_metrics(source, request.student_count),
        "proposed": _room_metrics(target, request.student_count),
        "projected_metrics": {
            "moved_entry_count": len(moved_entries),
            "cascaded_entry_count": max(0, len(moved_entries) - 1),
            "affected_room_ids": affected_room_ids,
            "class_capacity_utilization": utilization,
            "utilization_definition": (
                "Known class enrollment divided by assigned room capacity; "
                "this is not observed occupancy or time-based room utilization."
            ),
        },
        "checks": checks,
        "validation_errors": validation_errors,
        "warnings": warnings,
        "affected_entries": moved_entries,
        "affected_entities": affected_entities,
        "unresolved_conflicts": [
            {
                "timetable_entry_ids": list(pair),
                "room_ids": [
                    resolved_assignments.get(pair[0], entries_by_id[pair[0]].room_id),
                    resolved_assignments.get(pair[1], entries_by_id[pair[1]].room_id),
                ],
                "constraint_types": sorted(constraint_types),
            }
            for pair, constraint_types in sorted(unresolved_by_pair.items())
        ],
        "effects": effects,
        "ripple_effects": [
            f"{effect['timetable_entry_id']} would move from {effect['from_room_id']} to {effect['to_room_id']}."
            for effect in effects
        ],
        "search": {
            "explored_states": explored_states,
            "max_cascade_entries": _MAX_CASCADE_ENTRIES,
            "max_search_states": _MAX_SEARCH_STATES,
        },
        "energy_impact": {
            "status": "unavailable",
            "reason": "Room-level daily estimates cannot establish the energy change for scheduled classes.",
        },
        "cost_impact": {
            "status": "unavailable",
            "reason": "No schedule-level energy delta is available to calculate a cost change.",
        },
        "walking_impact": {
            "status": "unavailable",
            "reason": "No cohort origin or validated route change is supplied for the affected entries.",
        },
        "assumptions": [
            "A ripple effect is an additional timetable entry reassigned to another room because it overlaps a moved entry.",
            "Every reassigned entry keeps its semester, section, day, and time.",
            "Capacity for each automatically reassigned entry is checked only when its student count is supplied in affected_student_counts.",
            "Faculty and section conflicts are checked for overlapping affected entries within the same semester and day; section identity uses department and section.",
            "Facility and equipment compatibility with session_type is not checked because no required compatibility rules are defined.",
            "The bounded deterministic search permits at most eight additional reassigned entries and 2,000 search states.",
            "A feasible result is a proposed schedule/capacity check, not approval or a persisted timetable change.",
            "Synthetic or illustrative source records have not been verified as current campus operations.",
        ],
        "data_classification": classification,
    }
