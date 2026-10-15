from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import OccupancyObservation, Room
from backend.schemas import OccupancyCreate, OccupancyRead


router = APIRouter(prefix="/api/occupancy", tags=["occupancy"])


@router.get("", response_model=list[OccupancyRead])
def list_occupancy(
    room_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[OccupancyObservation]:
    statement = select(OccupancyObservation)
    if room_id is not None:
        statement = statement.where(OccupancyObservation.room_id == room_id)
    statement = statement.order_by(OccupancyObservation.observed_at.desc(),
                                   OccupancyObservation.observation_id).offset(offset).limit(limit)
    return list(db.scalars(statement))


@router.post("", response_model=OccupancyRead, status_code=status.HTTP_201_CREATED)
def create_occupancy(
    request: OccupancyCreate,
    db: Session = Depends(get_db),
) -> OccupancyObservation:
    if db.get(Room, request.room_id) is None:
        raise HTTPException(status_code=404, detail="Room not found")

    observation = OccupancyObservation(
        observation_id=str(uuid4()),
        room_id=request.room_id,
        observed_at=request.observed_at.isoformat(),
        detected_person_count=request.detected_person_count,
        room_capacity=None,
        occupancy_percent=None,
        detection_method=request.detection_method,
        confidence_score=request.confidence_score,
        verified_by_human=request.verified_by_human,
        data_status=request.data_status,
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation
