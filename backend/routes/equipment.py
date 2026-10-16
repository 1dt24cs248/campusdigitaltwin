from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Equipment
from backend.schemas import EquipmentRead


router = APIRouter(prefix="/api/equipment", tags=["equipment"])


@router.get("", response_model=list[EquipmentRead])
def list_equipment(
    room_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Equipment]:
    statement = select(Equipment)
    if room_id is not None:
        statement = statement.where(Equipment.room_id == room_id)
    statement = statement.order_by(Equipment.room_id, Equipment.equipment_id).offset(offset).limit(limit)
    return list(db.scalars(statement))
