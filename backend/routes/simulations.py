from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Room, TimetableEntry
from backend.schemas import SimulationRequest


router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("")
def create_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    timetable_entry = db.get(TimetableEntry, request.timetable_entry_id)
    if timetable_entry is None:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    if db.get(Room, request.source_room_id) is None:
        raise HTTPException(status_code=404, detail="Source room not found")
    if db.get(Room, request.target_room_id) is None:
        raise HTTPException(status_code=404, detail="Target room not found")
    if request.source_room_id == request.target_room_id:
        raise HTTPException(status_code=422, detail="Source and target rooms must differ")
    if timetable_entry.room_id != request.source_room_id:
        raise HTTPException(
            status_code=422,
            detail="source_room_id does not match the selected timetable entry",
        )

    raise HTTPException(
        status_code=503,
        detail={
            "status": "integration_pending",
            "message": "No simulator module is available; no simulation was calculated.",
        },
    )
