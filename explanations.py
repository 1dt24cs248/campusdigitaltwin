"""Deterministic, result-grounded explanations for the prototype."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def explain_occupancy(estimate: dict[str, Any]) -> str:
    room_id = estimate.get("room_id", "unknown room")
    count = estimate.get("estimated_occupancy")
    capacity = estimate.get("capacity_students")
    label = estimate.get("data_label", "unspecified data")
    if count is None or capacity is None:
        return f"Occupancy for {room_id} is unavailable because count or capacity is missing. Data label: {label}."
    source = estimate.get("source", "unknown")
    if source == "image_inference":
        subject = "The image detector estimated"
    elif source == "manual_input":
        subject = "A user entered"
    elif source == "synthetic_demo_data":
        subject = "Synthetic demo data records"
    else:
        subject = "The supplied observation reports"
    if estimate.get("status") == "over_capacity":
        return (
            f"{subject} {count} people in {room_id}, above its stated capacity of "
            f"{capacity}. Treat this as a review warning, not a confirmed occupancy count. Data label: {label}."
        )
    if capacity <= 0:
        return f"Occupancy for {room_id} cannot be compared because capacity is invalid. Data label: {label}."
    percentage = estimate.get("occupancy_ratio", count / capacity) * 100
    return (
        f"{subject} {count} people in {room_id} ({percentage:.1f}% of capacity {capacity}). "
        f"This is an estimate, not verified attendance. Data label: {label}."
    )


def explain_recommendation(recommendation: dict[str, Any]) -> str:
    action = recommendation.get("action_name", "Review the supplied campus data")
    reason = recommendation.get("reason", "The supporting evidence is not available.")
    follow_up = recommendation.get("required_follow_up")
    label = recommendation.get("data_label", "unspecified data")
    explanation = f"{action}: {reason} Data label: {label}."
    if follow_up:
        explanation += f" Follow-up: {follow_up}"
    return explanation


def build_simulation_explanation(
    result: Mapping[str, Any], campus_context: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Build a deterministic explanation that treats simulator fields as authoritative."""
    status = result.get("status", "unknown")
    errors = result.get("validation_errors") or []
    baseline = result.get("baseline") or {}
    proposed = result.get("proposed") or {}
    details = [f"Explanation mode: deterministic_fallback. Simulator status: {status}."]
    if status == "feasible":
        details.append("The simulator marked the proposed allocation feasible under its available checks.")
    elif status == "infeasible":
        details.append("The simulator rejected the proposed allocation; this explanation does not override that result.")
    elif status == "needs_input":
        details.append("The simulator needs additional input before feasibility can be established.")

    entry_id = baseline.get("timetable_entry_id") or proposed.get("timetable_entry_id")
    subject_name = baseline.get("subject_name") or proposed.get("subject_name")
    if entry_id or subject_name:
        details.append(
            "Affected class: " + " ".join(
                str(value) for value in (entry_id, subject_name) if value
            ) + "."
        )
    baseline_room = baseline.get("room_id")
    proposed_room = proposed.get("room_id")
    if baseline_room or proposed_room:
        details.append(f"Room comparison: baseline {baseline_room or 'unavailable'}; proposed {proposed_room or 'unavailable'}.")
    day = baseline.get("day_of_week") or proposed.get("day_of_week")
    start = baseline.get("start_time") or proposed.get("start_time")
    end = baseline.get("end_time") or proposed.get("end_time")
    if day or start or end:
        details.append(f"Scheduled period: {day or 'day unavailable'} {start or '?'}-{end or '?'}.")
    affected = result.get("affected_timetable_entries")
    if affected:
        details.append("Affected timetable entry IDs: " + ", ".join(map(str, affected)) + ".")
    if errors:
        details.append("Validation errors: " + " ".join(str(error) for error in errors))

    for key, label, baseline_key, proposed_key, saving_key, unit in (
        ("energy_impact", "Energy", "baseline_kwh", "proposed_kwh", "savings_kwh", "kWh"),
        ("cost_impact", "Electricity cost", "baseline_inr", "proposed_inr", "savings_inr", "INR"),
        ("walking_impact", "Walking distance", "baseline_distance_m", "proposed_distance_m", "distance_savings_m", "m"),
    ):
        impact = result.get(key) or {}
        if impact.get("status") == "available":
            baseline_value = impact.get(baseline_key)
            proposed_value = impact.get(proposed_key)
            saving_value = impact.get(saving_key)
            if baseline_value is not None and proposed_value is not None:
                metric = f"{label}: baseline {baseline_value} {unit}; proposed {proposed_value} {unit}"
                if saving_value is not None:
                    metric += f"; simulator-reported savings {saving_value} {unit}"
                    if saving_value < 0:
                        metric += " (an increase)"
                    elif saving_value == 0:
                        metric += " (no net reduction)"
                details.append(metric + ".")
            else:
                details.append(f"{label}: unavailable because baseline or proposed values are missing.")
        else:
            details.append(f"{label}: unavailable from the simulator result.")

    assumptions = result.get("assumptions") or []
    if assumptions:
        details.append("Assumptions: " + " ".join(str(item) for item in assumptions))
    warnings = result.get("warnings") or []
    if warnings:
        details.append("Warnings: " + " ".join(str(item) for item in warnings))
    if campus_context:
        context_items = [
            f"{key}: {value}" for key, value in campus_context.items()
            if value is not None and key in {"building_name", "occupancy_source", "occupancy_observed_at", "room_type"}
        ]
        if context_items:
            details.append("Supplied campus context: " + "; ".join(context_items) + ".")
    if result.get("data_classification"):
        details.append(f"Data classification: {result['data_classification']}.")
    return {
        "mode": "deterministic_fallback",
        "simulation_id": result.get("simulation_id"),
        "status": status,
        "text": " ".join(details),
        "limitations": [
            "Numerical values are copied from the simulator response and are not independently recalculated.",
            "This is a deterministic fallback, not a live generative AI response.",
        ],
    }


def explain_simulation(
    result: Mapping[str, Any], campus_context: Mapping[str, Any] | None = None
) -> str:
    """Backward-compatible text helper for existing consumers."""
    return build_simulation_explanation(result, campus_context)["text"]


def explain_recommendations(recommendations: Sequence[dict[str, Any]]) -> list[str]:
    return [explain_recommendation(recommendation) for recommendation in recommendations]