"""Transparent, configurable sustainability recommendation rules."""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from typing import Any, Sequence


PRIORITY_ORDER = {"operational": 0, "data_quality": 1, "review": 2}


def build_recommendations(
    rooms: Sequence[dict[str, Any]],
    occupancy_observations: Sequence[dict[str, Any]],
    energy_records: Sequence[dict[str, Any]],
    sustainability_actions: Sequence[dict[str, Any]],
    low_occupancy_threshold: float = 0.25,
    high_connected_load_kw: float = 0.8,
    timetable: Sequence[dict[str, Any]] = (),
    equipment_inventory: Sequence[dict[str, Any]] = (),
    simulation_results: Sequence[dict[str, Any]] | dict[str, Any] = (),
    max_observation_age_hours: float = 24.0,
    now: datetime | None = None,
    timetable_timezone: tzinfo | None = None,
) -> dict[str, Any]:
    """Generate evidence-grounded review prompts; never issue equipment commands."""
    if not 0 <= low_occupancy_threshold <= 1:
        raise ValueError("low_occupancy_threshold must be between 0 and 1")
    if high_connected_load_kw < 0:
        raise ValueError("high_connected_load_kw must not be negative")
    if max_observation_age_hours <= 0:
        raise ValueError("max_observation_age_hours must be positive")

    action_by_trigger = {row["trigger_type"]: row for row in sustainability_actions}
    room_by_id = {row["room_id"]: row for row in rooms}
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    def parse_timestamp(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed

    latest_observation: dict[str, dict[str, Any]] = {}
    latest_timestamp: dict[str, datetime] = {}
    warnings: list[str] = []
    for observation in occupancy_observations:
        room_id = observation.get("room_id")
        if room_id not in room_by_id:
            warnings.append(f"Occupancy observation references unknown room {room_id}.")
            continue
        observed_at = parse_timestamp(
            observation.get("observed_at", observation.get("observation_timestamp"))
        )
        current_timestamp = latest_timestamp.get(room_id)
        if observed_at is not None and (current_timestamp is None or observed_at > current_timestamp):
            latest_observation[room_id] = observation
            latest_timestamp[room_id] = observed_at
        elif room_id not in latest_observation:
            latest_observation[room_id] = observation

    recommendations: list[dict[str, Any]] = []

    def action_for(trigger: str) -> dict[str, Any] | None:
        return action_by_trigger.get(trigger)

    def schedule_context(
        room_id: str, observed_at: datetime | None
    ) -> list[dict[str, Any]] | None:
        if observed_at is None:
            return None
        if timetable_timezone is not None:
            observed_local = observed_at.astimezone(timetable_timezone)
        elif observed_at.utcoffset() == timezone.utc.utcoffset(observed_at):
            return None
        else:
            observed_local = observed_at
        matches = []
        observed_day = observed_local.strftime("%A").casefold()
        observed_time = observed_local.strftime("%H:%M")
        for entry in timetable:
            if entry.get("room_id") != room_id:
                continue
            if str(entry.get("day_of_week", "")).casefold() != observed_day:
                continue
            start_time = str(entry.get("start_time", ""))
            end_time = str(entry.get("end_time", ""))
            if start_time <= observed_time < end_time:
                matches.append(
                    {
                        "timetable_entry_id": entry.get("timetable_entry_id"),
                        "subject_name": entry.get("subject_name"),
                        "start_time": start_time,
                        "end_time": end_time,
                        "expected_students": entry.get("expected_students"),
                    }
                )
        return matches

    for room_id in sorted(room_by_id):
        room = room_by_id[room_id]
        try:
            capacity = int(room["capacity_students"])
        except (KeyError, TypeError, ValueError):
            capacity = 0
            warnings.append(f"Capacity is unavailable for {room_id}; occupancy ratio cannot be assessed.")
        observation = latest_observation.get(room_id)
        if observation is None:
            warnings.append(f"No occupancy observation is available for {room_id}.")
            action = action_for("missing_or_stale_occupancy")
            if action:
                recommendations.append(
                    {
                        "recommendation_id": f"REC-MISSING-{room_id}",
                        "action_id": action["action_id"],
                        "action_name": action["action_name"],
                        "room_id": room_id,
                        "building_id": room.get("building_id"),
                        "priority": action["priority"],
                        "reason": "No occupancy observation was supplied for this room.",
                        "evidence": {"occupancy_observation": "missing"},
                        "data_source": "occupancy_observations input",
                        "data_timestamp": None,
                        "confidence_limitations": "Room utilization cannot be inferred without an observation.",
                        "operational_constraints": "Check timetable and room records before making allocation decisions.",
                        "required_follow_up": "Collect a valid, timestamped observation and compare it with the schedule.",
                        "data_label": "unknown",
                    }
                )
        else:
            observed_at = latest_timestamp.get(room_id) or parse_timestamp(
                observation.get("observed_at", observation.get("observation_timestamp"))
            )
            observation_timestamp = observation.get("observed_at", observation.get("observation_timestamp"))
            age_hours = None if observed_at is None else (now - observed_at).total_seconds() / 3600
            stale = age_hours is None or age_hours < 0 or age_hours > max_observation_age_hours
            label = observation.get("data_label", "unknown")
            if label == "synthetic_demo_data":
                warnings.append(
                    f"Occupancy for {room_id} is synthetic and must not be treated as a live observation."
                )
            if stale:
                warnings.append(f"Occupancy observation for {room_id} is missing a valid timestamp or is stale.")
                action = action_for("missing_or_stale_occupancy")
                if action:
                    recommendations.append(
                        {
                            "recommendation_id": f"REC-STALE-{room_id}",
                            "action_id": action["action_id"],
                            "action_name": action["action_name"],
                            "room_id": room_id,
                            "building_id": room.get("building_id"),
                            "priority": action["priority"],
                            "reason": (
                                "The latest occupancy observation is not recent enough for current decisions."
                                if age_hours is not None
                                else "The occupancy observation has no valid timestamp."
                            ),
                            "evidence": {
                                "observation_timestamp": observation_timestamp,
                                "age_hours": None if age_hours is None else round(age_hours, 2),
                                "max_observation_age_hours": max_observation_age_hours,
                                "data_label": label,
                            },
                            "data_source": observation.get("source", "occupancy_observations"),
                            "data_timestamp": observation_timestamp,
                            "confidence_limitations": "Stale or undated observations do not represent current occupancy.",
                            "operational_constraints": "Do not use this observation alone to consolidate or close a room.",
                            "required_follow_up": "Capture a current observation and compare it with the timetable.",
                            "data_label": label,
                        }
                    )

            try:
                occupancy = int(observation["estimated_occupancy"])
            except (KeyError, TypeError, ValueError):
                occupancy = -1
            if capacity <= 0 or occupancy < 0 or occupancy > capacity:
                warnings.append(f"Invalid occupancy/capacity data for {room_id}; occupancy rule skipped.")
            elif not stale and occupancy / capacity <= low_occupancy_threshold:
                action = action_for("low_observed_occupancy")
                if action:
                    ratio = occupancy / capacity
                    timestamp_schedule = schedule_context(room_id, observed_at)
                    schedule_supplied = bool(timetable)
                    schedule_note = (
                        "A class is scheduled in this room at the observation time; verify the observation and attendance before interpreting the low count."
                        if timestamp_schedule
                        else "The observation timezone could not be aligned with the timetable; schedule context is unavailable."
                        if timestamp_schedule is None and schedule_supplied
                        else "No class is listed in the supplied timetable at the observation time; this single snapshot does not establish underutilization."
                        if schedule_supplied
                        else "Timetable data was not supplied; room utilization cannot be established."
                    )
                    recommendations.append(
                        {
                            "recommendation_id": f"REC-LOW-{room_id}",
                            "action_id": action["action_id"],
                            "action_name": action["action_name"],
                            "room_id": room_id,
                            "building_id": room.get("building_id"),
                            "priority": action["priority"],
                            "reason": (
                                f"The latest observation shows {occupancy}/{capacity} occupants "
                                f"({ratio:.0%}), at or below the configured "
                                f"{low_occupancy_threshold:.0%} review threshold. {schedule_note}"
                            ),
                            "evidence": {
                                "estimated_occupancy": occupancy,
                                "capacity_students": capacity,
                                "occupancy_ratio": round(ratio, 4),
                                "observation_timestamp": observation_timestamp,
                                "source": observation.get("source"),
                                "data_label": label,
                                "scheduled_entries_at_observation_time": timestamp_schedule,
                                "timetable_timezone": str(timetable_timezone)
                                if timetable_timezone is not None
                                else "observation timestamp offset",
                            },
                            "data_source": observation.get("source", "occupancy_observations"),
                            "data_timestamp": observation_timestamp,
                            "confidence_limitations": "A single snapshot may be affected by detection misses, occlusion, and timing.",
                            "operational_constraints": "This is a review prompt, not evidence that the room is unused or equipment is wasting energy.",
                            "required_follow_up": "Check repeated observations and timetable bookings before considering room consolidation.",
                            "data_label": label,
                        }
                    )
                    equipment_records = [row for row in equipment_inventory if row.get("room_id") == room_id]
                    if equipment_records:
                        runtime_hours = sum(
                            float(row.get("assumed_daily_hours", 0) or 0)
                            for row in equipment_records
                        )
                        equipment_action = action_for("low_occupancy_with_equipment")
                        if equipment_action:
                            recommendations.append(
                                {
                                    "recommendation_id": f"REC-EQUIPMENT-{room_id}",
                                    "action_id": equipment_action["action_id"],
                                    "action_name": equipment_action["action_name"],
                                    "room_id": room_id,
                                    "building_id": room.get("building_id"),
                                    "priority": equipment_action["priority"],
                                    "reason": "Equipment inventory and a low occupancy snapshot are both supplied; inventory does not prove equipment was operating during the observation.",
                                    "evidence": {
                                        "equipment_record_count": len(equipment_records),
                                        "sum_of_assumed_daily_hours_across_records": runtime_hours,
                                        "occupancy_timestamp": observation_timestamp,
                                        "data_label": label,
                                    },
                                    "data_source": "equipment_inventory and occupancy_observations inputs",
                                    "data_timestamp": observation_timestamp,
                                    "confidence_limitations": "Assumed daily runtime is not an observed on/off state.",
                                    "operational_constraints": "Do not switch equipment off based on this recommendation.",
                                    "required_follow_up": "Verify the room schedule and equipment controls with facilities staff.",
                                    "data_label": label,
                                }
                            )

        try:
            connected_load = float(room["estimated_connected_load_kw"])
        except (KeyError, TypeError, ValueError):
            warnings.append(f"Connected load is unavailable for {room_id}.")
            continue
        if connected_load >= high_connected_load_kw:
            action = action_for("high_connected_load")
            if action:
                recommendations.append(
                    {
                        "recommendation_id": f"REC-LOAD-{room_id}",
                        "action_id": action["action_id"],
                        "action_name": action["action_name"],
                        "room_id": room_id,
                        "building_id": room.get("building_id"),
                        "priority": action["priority"],
                        "reason": (
                            f"Connected equipment load is {connected_load:.3f} kW, at or above "
                            f"the configured {high_connected_load_kw:.3f} kW review threshold."
                        ),
                        "evidence": {
                            "estimated_connected_load_kw": connected_load,
                            "threshold_kw": high_connected_load_kw,
                            "data_label": room.get("data_label", "unspecified"),
                        },
                        "data_label": room.get("data_label", "unspecified"),
                        "required_follow_up": "Review equipment inventory and operating assumptions; no shutdown is recommended automatically.",
                        "data_source": "rooms input",
                        "data_timestamp": None,
                        "confidence_limitations": "Connected load is not measured energy consumption or proof of current operation.",
                        "operational_constraints": "No equipment control action is performed.",
                    }
                )

    if energy_records and "unverified_tariff" in action_by_trigger:
        unverified_records = [
            row
            for row in energy_records
            if str(row.get("tariff_is_verified", "false")).casefold() != "true"
        ]
        if unverified_records:
            action = action_by_trigger["unverified_tariff"]
            recommendations.append(
                {
                    "recommendation_id": "REC-VERIFY-TARIFF",
                    "action_id": action["action_id"],
                    "action_name": action["action_name"],
                    "room_id": None,
                    "building_id": None,
                    "priority": action["priority"],
                    "reason": (
                        f"{len(unverified_records)} of {len(energy_records)} supplied energy records "
                        "do not establish a verified campus tariff."
                    ),
                    "evidence": {
                        "unverified_record_count": len(unverified_records),
                        "total_record_count": len(energy_records),
                        "data_label": "synthetic_demo_data"
                        if all(row.get("data_label") == "synthetic_demo_data" for row in energy_records)
                        else "mixed_or_unspecified",
                    },
                    "data_label": "synthetic_demo_data"
                    if all(row.get("data_label") == "synthetic_demo_data" for row in energy_records)
                    else "mixed_or_unspecified",
                    "required_follow_up": "Obtain an approved tariff before using cost estimates for decisions.",
                    "data_source": "energy_records input",
                    "data_timestamp": None,
                    "confidence_limitations": "Supplied tariff values do not establish a verified campus tariff.",
                    "operational_constraints": "Do not present cost estimates as verified bills.",
                }
            )

    if isinstance(simulation_results, dict):
        simulation_results = [simulation_results]
    simulation_action = action_for("feasible_simulation_review")
    if simulation_action:
        for result_index, result in enumerate(simulation_results, start=1):
            if result.get("status", result.get("feasibility_status")) != "feasible":
                continue
            if result.get("validation_errors"):
                continue
            baseline = result.get("baseline") or {}
            proposed = result.get("proposed") or {}
            if not baseline.get("room_id") or not proposed.get("room_id"):
                warnings.append("A feasible simulator result is missing baseline/proposed room IDs; no relocation recommendation was generated.")
                continue
            recommendations.append(
                {
                    "recommendation_id": f"REC-SIM-{result.get('simulation_id') or baseline.get('timetable_entry_id') or result_index}-{baseline.get('room_id')}-{proposed.get('room_id')}",
                    "action_id": simulation_action["action_id"],
                    "action_name": simulation_action["action_name"],
                    "room_id": proposed.get("room_id"),
                    "building_id": room_by_id.get(proposed.get("room_id"), {}).get("building_id"),
                    "priority": simulation_action["priority"],
                    "reason": "The supplied simulator result marks this room reassignment feasible; review its baseline-versus-proposed impacts before making a timetable change.",
                    "evidence": {
                        "baseline": baseline,
                        "proposed": proposed,
                        "energy_impact": result.get("energy_impact"),
                        "cost_impact": result.get("cost_impact"),
                        "walking_impact": result.get("walking_impact"),
                        "validation_errors": result.get("validation_errors", []),
                    },
                    "energy_impact": result.get("energy_impact"),
                    "cost_impact": result.get("cost_impact"),
                    "walking_impact": result.get("walking_impact"),
                    "simulation_id": result.get("simulation_id"),
                    "data_source": "Member 3 simulator result",
                    "data_timestamp": result.get("created_at"),
                    "confidence_limitations": "Impacts retain the simulator's assumptions and availability status; this module does not recalculate them.",
                    "operational_constraints": "A feasible simulation does not apply or persist a timetable change.",
                    "required_follow_up": "Confirm the timetable, class size, and assumptions with the campus operator.",
                    "data_label": result.get("data_classification", "simulated_result"),
                }
            )

    recommendations.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(item["priority"], len(PRIORITY_ORDER)),
            item["room_id"] or "",
            item["recommendation_id"],
        )
    )
    for rank, recommendation in enumerate(recommendations, start=1):
        recommendation["priority_rank"] = rank

    return {
        "status": "available",
        "recommendations": recommendations,
        "warnings": sorted(set(warnings)),
        "ranking_policy": "priority category, then room ID and recommendation ID; not scientifically validated",
        "thresholds": {
            "low_occupancy_ratio": low_occupancy_threshold,
            "high_connected_load_kw": high_connected_load_kw,
        },
        "data_label": "synthetic_demo_data"
        if any(row.get("data_label") == "synthetic_demo_data" for row in occupancy_observations)
        else "derived_from_supplied_records",
    }