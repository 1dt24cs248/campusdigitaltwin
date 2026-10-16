from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
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


def explanation_conflicts_with_result(
    text: str,
    simulation_result: Mapping[str, Any],
) -> bool:
    """Reject prose that contradicts the verdict or cites unknown room/class IDs."""
    if not isinstance(text, str) or not text.strip():
        return True
    feasible = simulation_result.get("feasible")
    lower = text.lower()
    if feasible is False:
        positive_verdict = re.search(
            r"\bfeasible\b|\bcan proceed\b|\bapproved\b|\bapproval granted\b|\bno conflicts? remain\b",
            lower,
        )
        explicit_negative = re.search(r"\bnot feasible\b|\binfeasible\b", lower)
        if positive_verdict and not explicit_negative:
            return True
    elif feasible is True:
        if re.search(
            r"\binfeasible\b|\bnot feasible\b|\bcannot proceed\b|\bcan't proceed\b|\brejected\b|\bconflicts? remain\b",
            lower,
        ):
            return True
    else:
        if re.search(r"\bfeasible\b|\binfeasible\b|\bapproved\b|\brejected\b", lower):
            return True

    allowed_ids: set[str] = set()
    for key in ("baseline", "proposed"):
        value = simulation_result.get(key)
        if isinstance(value, Mapping) and isinstance(value.get("room_id"), str):
            allowed_ids.add(value["room_id"])
    metrics = simulation_result.get("projected_metrics")
    if isinstance(metrics, Mapping):
        allowed_ids.update(item for item in metrics.get("affected_room_ids", []) if isinstance(item, str))
    for entry in simulation_result.get("affected_entries", []):
        if isinstance(entry, Mapping):
            for key in ("timetable_entry_id", "source_room_id", "target_room_id"):
                value = entry.get(key)
                if isinstance(value, str):
                    allowed_ids.add(value)
    mentioned_ids = set(re.findall(r"\b(?:TT[A-Z0-9-]+|[A-Z]+-[A-Z0-9]+(?:-[A-Z0-9]+)*)\b", text))
    if mentioned_ids - allowed_ids:
        return True

    # Keep generated prose qualitative. Numeric facts and exact constraint
    # outcomes stay in the simulator's structured fields, where they can be
    # shown without a language model paraphrasing them incorrectly.
    prose_without_ids = text
    for identifier in allowed_ids:
        prose_without_ids = prose_without_ids.replace(identifier, " ")
    if re.search(r"(?<![A-Za-z])\d+(?:[.,]\d+)?\s*%?", prose_without_ids):
        return True
    number_words = (
        r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
        r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million"
    )
    if re.search(
        rf"\b(?:{number_words})(?:[- ](?:{number_words}))*\s+"
        r"(?:students?|people|persons?|rooms?|classes|entries|percent|kwh|kilowatt-hours?|"
        r"inr|rupees?|meters?|metres?|minutes?|hours?|days?)\b",
        prose_without_ids,
        re.IGNORECASE,
    ):
        return True

    checks = simulation_result.get("checks")
    if isinstance(checks, Mapping):
        check_terms = {
            "capacity": r"capacity|enrollment|class size",
            "destination_eligibility": r"destination|eligib(?:le|ility)",
            "destination_schedule": r"destination|schedule|room conflict|overlap",
            "cascade_reassignment": r"cascade|reassign(?:ment)?",
            "faculty_schedule": r"faculty|instructor",
            "section_schedule": r"section|cohort",
            "room_suitability": r"facility|equipment|room suitability",
        }
        for check_name, check in checks.items():
            if not isinstance(check, Mapping):
                continue
            status = check.get("status")
            terms = check_terms.get(check_name)
            if status not in {"pass", "fail", "unknown", "not_checked", "not_evaluated"} or not terms:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", lower):
                if not re.search(terms, sentence):
                    continue
                claims_pass = bool(re.search(r"\b(pass(?:ed)?|clear|satisfied|no conflict|no overlap|eligible)\b", sentence))
                claims_fail = bool(re.search(r"\b(fail(?:ed)?|conflict|overlap|blocked|ineligible|not satisfied)\b", sentence))
                if status in {"fail", "unknown", "not_checked", "not_evaluated"} and claims_pass:
                    return True
                if status == "pass" and claims_fail:
                    return True

    # Quantitative sustainability outcomes are unavailable in the current
    # simulator. Reject unsupported benefit claims while allowing explicit
    # statements that those metrics are unknown or unavailable.
    impact_claim = re.compile(
        r"\b(energy|carbon|emissions?|cost|walking(?: distance)?)\b.{0,80}"
        r"\b(savings?|saved|reduction|reduced|decrease|decreased|shorter|lower|improvement)\b"
        r"|\b(savings?|saved|reduction|reduced|decrease|decreased|shorter|lower|improvement)\b.{0,80}"
        r"\b(energy|carbon|emissions?|cost|walking(?: distance)?)\b"
    )
    for sentence in re.split(r"(?<=[.!?])\s+", lower):
        if impact_claim.search(sentence) and not re.search(
            r"\b(unavailable|unknown|not calculated|not provided|cannot estimate|insufficient data|no validated)\b",
            sentence,
        ):
            return True
    return False


def _model_completion(messages: list[dict[str, str]]) -> str:
    """Call an OpenAI-compatible chat completion endpoint using backend-only secrets."""
    api_key = os.getenv("ECOTWIN_LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Language model is not configured")
    base_url = os.getenv("ECOTWIN_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("ECOTWIN_LLM_MODEL", "gpt-4o-mini").strip()
    payload = json.dumps({"model": model, "messages": messages, "temperature": 0.2}).encode()
    request = Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=float(os.getenv("ECOTWIN_LLM_TIMEOUT_SECONDS", "20"))) as response:
            data = json.loads(response.read())
    except HTTPError as exc:
        if exc.code == 429:
            raise RuntimeError("Language model rate limit reached") from exc
        raise RuntimeError(f"Language model provider returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError("Language model provider is unavailable or returned invalid data") from exc
    try:
        content = data["choices"][0]["message"]["content"]
    except (TypeError, KeyError, IndexError) as exc:
        raise RuntimeError("Language model provider returned an invalid response") from exc
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Language model provider returned an empty response")
    return content.strip()


def generate_grounded_response(question: str, context: Mapping[str, Any]) -> dict[str, Any]:
    """Generate a grounded answer, with a useful transparent fallback when unconfigured."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must not be empty")
    safe_context = json.dumps(context, ensure_ascii=False, default=str)
    prompt = (
        "Answer using only the supplied EcoTwin campus records. If a value is absent, say it is unknown. "
        "Never invent measurements, savings, occupancy, or schedule outcomes. Simulation feasibility "
        "comes only from the deterministic result. Clearly call out sample data and uncertainty. "
        "For simulation explanations, do not include numerical values or independently restate "
        "whether individual checks passed; explain the result qualitatively because those facts "
        "are shown separately from the simulator."
    )
    if not os.getenv("ECOTWIN_LLM_API_KEY", "").strip():
        return {
            "source": "deterministic_fallback",
            "provider_status": "not_configured",
            "model": None,
            "answer": "The language model is not configured. Review the campus records and available checks for this information.",
        }
    try:
        answer = _model_completion([
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Question: {question.strip()}\nCampus context: {safe_context}"},
        ])
        return {"source": "language_model", "provider_status": "available", "model": os.getenv("ECOTWIN_LLM_MODEL", "gpt-4o-mini"), "answer": answer}
    except RuntimeError as exc:
        return {
            "source": "deterministic_fallback",
            "provider_status": "unavailable",
            "model": None,
            "answer": f"A live AI explanation is unavailable ({exc}). I can only report the campus records provided; please review the room and schedule details directly.",
        }
