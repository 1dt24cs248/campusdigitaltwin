from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Room, TimetableEntry
from backend.schemas import RoomRead, TimetableEntryRead


router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomRead])
def list_rooms(
    building_id: str | None = None,
    floor_number: int | None = None,
    facility_type: str | None = None,
    min_capacity: int | None = Query(default=None, ge=0),
    max_capacity: int | None = Query(default=None, ge=0),
    timetable_eligible: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Room]:
    if min_capacity is not None and max_capacity is not None and min_capacity > max_capacity:
        raise HTTPException(status_code=422, detail="min_capacity must not exceed max_capacity")

    statement = select(Room)
    if building_id is not None:
        statement = statement.where(Room.building_id == building_id)
    if floor_number is not None:
        statement = statement.where(Room.floor_number == floor_number)
    if facility_type is not None:
        statement = statement.where(Room.facility_type == facility_type)
    if min_capacity is not None:
        statement = statement.where(Room.capacity_students >= min_capacity)
    if max_capacity is not None:
        statement = statement.where(Room.capacity_students <= max_capacity)
    if timetable_eligible is not None:
        statement = statement.where(Room.timetable_eligible == timetable_eligible)
    statement = statement.order_by(Room.room_id).offset(offset).limit(limit)
    return list(db.scalars(statement))


@router.get("/{room_id}/timetable", response_model=list[TimetableEntryRead])
def get_room_timetable(
    room_id: str,
    semester: int | None = Query(default=None, ge=1),
    day_of_week: str | None = None,
    db: Session = Depends(get_db),
) -> list[TimetableEntry]:
    if db.get(Room, room_id) is None:
        raise HTTPException(status_code=404, detail="Room not found")
    statement = select(TimetableEntry).where(TimetableEntry.room_id == room_id)
    if semester is not None:
        statement = statement.where(TimetableEntry.semester == semester)
    if day_of_week is not None:
        statement = statement.where(TimetableEntry.day_of_week == day_of_week)
    statement = statement.order_by(TimetableEntry.semester, TimetableEntry.day_of_week,
                                   TimetableEntry.start_time, TimetableEntry.timetable_entry_id)
    return list(db.scalars(statement))


@router.get("/{room_id}", response_model=RoomRead)
def get_room(room_id: str, db: Session = Depends(get_db)) -> Room:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room
