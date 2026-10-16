from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import EnergyRecord
from backend.schemas import EnergyRecordRead


router = APIRouter(prefix="/api/energy", tags=["energy"])


@router.get("", response_model=list[EnergyRecordRead])
def list_energy_records(
    room_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[EnergyRecord]:
    statement = select(EnergyRecord)
    if room_id is not None:
        statement = statement.where(EnergyRecord.room_id == room_id)
    statement = statement.order_by(EnergyRecord.room_id, EnergyRecord.record_date.desc(),
                                   EnergyRecord.energy_record_id).offset(offset).limit(limit)
    return list(db.scalars(statement))
