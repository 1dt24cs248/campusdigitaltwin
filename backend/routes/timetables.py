from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import TimetableEntry
from backend.schemas import TimetableEntryRead


router = APIRouter(prefix="/api/timetables", tags=["timetables"])


@router.get("", response_model=list[TimetableEntryRead])
def list_timetables(
    semester: int | None = Query(default=None, ge=1),
    section: str | None = None,
    department: str | None = None,
    day_of_week: str | None = None,
    room_id: str | None = None,
    subject_code: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[TimetableEntry]:
    statement = select(TimetableEntry)
    filters = (
        (semester, TimetableEntry.semester),
        (section, TimetableEntry.section),
        (department, TimetableEntry.department),
        (day_of_week, TimetableEntry.day_of_week),
        (room_id, TimetableEntry.room_id),
        (subject_code, TimetableEntry.subject_code),
    )
    for value, column in filters:
        if value is not None:
            statement = statement.where(column == value)
    statement = statement.order_by(
        TimetableEntry.semester,
        TimetableEntry.day_of_week,
        TimetableEntry.start_time,
        TimetableEntry.timetable_entry_id,
    ).offset(offset).limit(limit)
    return list(db.scalars(statement))
