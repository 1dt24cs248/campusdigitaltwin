from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Building
from backend.schemas import BuildingRead


router = APIRouter(prefix="/api/buildings", tags=["buildings"])


@router.get("", response_model=list[BuildingRead])
def list_buildings(db: Session = Depends(get_db)) -> list[Building]:
    return list(db.scalars(select(Building).order_by(Building.building_id)))


@router.get("/{building_id}", response_model=BuildingRead)
def get_building(building_id: str, db: Session = Depends(get_db)) -> Building:
    building = db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return building
