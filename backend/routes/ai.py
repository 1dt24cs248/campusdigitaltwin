import os

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai import generate_explanation, generate_recommendations
from backend.ai.explanations import explanation_conflicts_with_result, generate_grounded_response
from backend.database import get_db
from backend.models import Equipment, OccupancyObservation, Room, TimetableEntry
from backend.schemas import CampusQuestionRequest, SimulationExplanationRequest


router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/recommendations")
def list_recommendations(db: Session = Depends(get_db)) -> list[dict]:
    rooms = list(db.scalars(select(Room).order_by(Room.room_id)))
    observations = list(db.scalars(
        select(OccupancyObservation).order_by(
            OccupancyObservation.observed_at,
            OccupancyObservation.observation_id,
        )
    ))
    timetable = list(db.scalars(select(TimetableEntry).order_by(TimetableEntry.timetable_entry_id)))
    equipment = list(db.scalars(select(Equipment).order_by(Equipment.equipment_id)))

    campus_data = {
        "rooms": [
            {
                "room_id": room.room_id,
                "building_id": room.building_id,
                "capacity_students": room.capacity_students,
                "data_status": room.data_status,
            }
            for room in rooms
        ],
        "occupancy_observations": [
            {
                "room_id": observation.room_id,
                "detected_person_count": observation.detected_person_count,
                "observed_at": observation.observed_at,
                "detection_method": observation.detection_method,
                "data_status": observation.data_status,
            }
            for observation in observations
        ],
        "timetable": [
            {
                "room_id": entry.room_id,
                "day_of_week": entry.day_of_week,
                "period_number": entry.period_number,
                "start_time": entry.start_time.isoformat(),
                "end_time": entry.end_time.isoformat(),
                "data_status": entry.data_status,
            }
            for entry in timetable
        ],
        "equipment_inventory": [
            {
                "room_id": item.room_id,
                "equipment_type": item.equipment_type,
                "data_status": item.data_status,
            }
            for item in equipment
        ],
    }
    return generate_recommendations(campus_data, simulation_results=None)


@router.post("/explanations")
def explain_simulation(request: SimulationExplanationRequest) -> dict:
    result_for_explanation = request.simulation_result.model_dump(mode="json")
    baseline = result_for_explanation.get("baseline")
    proposed = result_for_explanation.get("proposed")
    projected_metrics = result_for_explanation.get("projected_metrics")
    if isinstance(baseline, dict):
        result_for_explanation.setdefault("source_room_id", baseline.get("room_id"))
    if isinstance(proposed, dict):
        result_for_explanation.setdefault("target_room_id", proposed.get("room_id"))
    if isinstance(projected_metrics, dict):
        result_for_explanation.setdefault(
            "affected_rooms",
            projected_metrics.get("affected_room_ids"),
        )
    affected_entries = result_for_explanation.get("affected_entries")
    if isinstance(affected_entries, list):
        result_for_explanation.setdefault(
            "affected_classes",
            [
                entry.get("timetable_entry_id")
                for entry in affected_entries
                if isinstance(entry, dict) and entry.get("timetable_entry_id") is not None
            ],
        )
    fallback = generate_explanation(
        result_for_explanation,
        request.campus_context,
    )
    fallback.update({"provider_status": "not_configured", "model": None})
    if os.getenv("ECOTWIN_LLM_API_KEY", "").strip():
        authoritative_verdict = {
            True: "FEASIBLE",
            False: "INFEASIBLE",
            None: "INCOMPLETE / UNKNOWN",
        }[request.simulation_result.feasible]
        response = generate_grounded_response(
            f"The deterministic simulator's authoritative verdict is {authoritative_verdict}. This exact verdict cannot be changed. Explain only the supplied result, its checks, affected rooms and entries, trade-offs, and uncertainty. Do not introduce other room IDs, timetable IDs, measurements, or counts.",
            {"authoritative_verdict": authoritative_verdict, "simulation_result": result_for_explanation, "campus_context": request.campus_context or {}},
        )
        if response["source"] == "language_model" and not explanation_conflicts_with_result(
            response["answer"], result_for_explanation,
        ):
            fallback.update({
                "explanation": response["answer"],
                "source": "language_model",
                "provider_status": "available",
                "model": response["model"],
            })
        else:
            fallback["provider_status"] = (
                "conflicting_response" if response["source"] == "language_model"
                else response["provider_status"]
            )
            if response["source"] == "language_model":
                fallback["explanation"] = (
                    "The model returned an explanation that did not match the simulator result. "
                    + fallback["explanation"]
                )
    return {
        **fallback,
        "authoritative_status": request.simulation_result.status,
        "input_provenance": "caller_supplied; not run or validated by this API",
    }


@router.post("/chat")
def ask_campus_question(request: CampusQuestionRequest, db: Session = Depends(get_db)) -> dict:
    rooms = list(db.scalars(select(Room).order_by(Room.room_id)))
    entries = list(db.scalars(select(TimetableEntry).order_by(TimetableEntry.timetable_entry_id)))
    observations = list(db.scalars(select(OccupancyObservation).order_by(OccupancyObservation.observed_at.desc())))
    context = {
        "rooms": [{"room_id": room.room_id, "building": room.building_name, "capacity": room.capacity_students, "data_status": room.data_status} for room in rooms],
        "timetable": [{"entry_id": entry.timetable_entry_id, "room_id": entry.room_id, "subject": entry.subject_name, "day": entry.day_of_week, "start": entry.start_time.isoformat(), "end": entry.end_time.isoformat(), "semester": entry.semester, "data_status": entry.data_status} for entry in entries],
        "occupancy_observations": [{"room_id": item.room_id, "count": item.detected_person_count, "observed_at": item.observed_at, "method": item.detection_method, "data_status": item.data_status} for item in observations[:100]],
        "scope": "Illustrative campus records; no live sensor feed or sustainability deltas are available.",
    }
    result = generate_grounded_response(request.question, context)
    return {**result, "context_source": "campus_database", "data_provenance": "records may be illustrative"}
