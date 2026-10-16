from __future__ import annotations

from typing import Any, Mapping


_METRICS = {
    "baseline energy": ("baseline_energy_kwh_day", "baseline_energy_kwh_per_day", "baseline_energy_kwh"),
    "proposed energy": ("proposed_energy_kwh_day", "proposed_energy_kwh_per_day", "proposed_energy_kwh"),
    "energy change": ("energy_saved_kwh_day", "energy_change_kwh", "net_energy_change_kwh"),
    "cost change": ("cost_saved_inr_day", "cost_change_inr", "estimated_cost_change"),
    "baseline walking distance": ("baseline_walk_m_day", "baseline_walking_distance_m", "baseline_walk_m"),
    "proposed walking distance": ("proposed_walk_m_day", "proposed_walking_distance_m", "proposed_walk_m"),
    "walking-distance change": ("walking_distance_change_m_day", "walking_distance_change_m"),
}


def _value(result: Mapping[str, Any], keys: tuple[str, ...]) -> tuple[str, Any] | None:
    containers = [result]
    containers.extend(
        value for key in ("metrics", "energy", "cost", "walking")
        if isinstance((value := result.get(key)), Mapping)
    )
    for container in containers:
        for key in keys:
            if key in container and container[key] is not None:
                return key, container[key]
    return None


def _display(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return repr(value)
    return str(value)


def generate_explanation(
    simulation_result: Mapping[str, Any],
    campus_context: Mapping[str, Any] | None = None,
) -> dict:
    """Explain an actual simulator payload without deriving or changing its values."""
    if not isinstance(simulation_result, Mapping):
        raise TypeError("simulation_result must be a mapping")
    if campus_context is not None and not isinstance(campus_context, Mapping):
        raise TypeError("campus_context must be a mapping when provided")

    result = simulation_result
    feasible_key = next((key for key in ("feasible", "is_feasible", "is_valid") if key in result), None)
    feasible = result.get(feasible_key) if feasible_key else None
    validation_errors = result.get("validation_errors", result.get("errors", []))
    validation_errors = validation_errors if isinstance(validation_errors, list) else [validation_errors]
    if feasible is True:
        status = "The simulator marks this proposal feasible."
    elif feasible is False:
        status = "The simulator marks this proposal infeasible; do not treat it as approved."
    elif validation_errors:
        status = "Validation errors were returned; feasibility is not explicitly marked, so the proposal must not be treated as approved."
    else:
        status = "Feasibility is unavailable in the simulator result."

    affected = []
    for key in ("affected_rooms", "source_room_id", "target_room_id", "room_id", "affected_classes", "class_id", "subject_code"):
        if key in result and result[key] is not None:
            affected.append(f"{key}={_display(result[key])}")
    metrics = {}
    metric_lines = []
    for label, keys in _METRICS.items():
        found = _value(result, keys)
        if found is not None:
            key, value = found
            metrics[key] = value
            unit = " kWh/day" if "energy" in label else " INR/day" if "cost" in label else " m/day" if "distance" in label else ""
            metric_lines.append(f"{label.title()}: {key} = {_display(value)}{unit} (simulator-reported).")
        else:
            metric_lines.append(f"{label.title()}: unavailable in simulator result.")

    errors_text = "; ".join(_display(error) for error in validation_errors) if validation_errors else "None supplied."
    assumptions = result.get("assumptions", result.get("missing_information", []))
    assumptions_text = _display(assumptions) if assumptions else "No assumptions were supplied; missing inputs cannot be inferred."
    context_fields = (
        "context_notes", "operational_constraints", "timetable_constraints",
        "capacity_constraints", "assumptions", "missing_information",
    )
    supplied_context = {
        key: campus_context[key]
        for key in context_fields
        if campus_context is not None and key in campus_context
    }
    if feasible is True:
        next_step = "Confirm the timetable, capacity, and on-site conditions with the responsible campus owner before applying the change."
    else:
        next_step = "Review the simulator validation output and required inputs, then rerun the scenario; do not enact this proposal based on this explanation."

    explanation = "\n".join([
        status,
        "Affected rooms/classes: " + ("; ".join(affected) if affected else "unavailable in simulator result."),
        *metric_lines,
        "Validation errors: " + errors_text,
        "Assumptions or missing information: " + assumptions_text,
        "Caller-supplied campus context: " + (_display(supplied_context) if supplied_context else "none supplied."),
        "Next verification step: " + next_step,
    ])
    return {
        "source": "deterministic_fallback",
        "simulation_id": result.get("simulation_id"),
        "feasible": feasible,
        "validation_errors": validation_errors,
        "affected_entities": affected,
        "simulator_metrics": metrics,
        "campus_context": supplied_context,
        "explanation": explanation,
        "next_step": next_step,
    }