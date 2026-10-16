import base64
import binascii
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import OccupancyObservation, Room
from backend.schemas import (
    OccupancyCreate,
    OccupancyInferenceRead,
    OccupancyInferenceRequest,
    OccupancyRead,
)
from backend.vision import detect_occupancy, validate_image_dimensions


router = APIRouter(prefix="/api/occupancy", tags=["occupancy"])
_MAX_IMAGE_BYTES = 5 * 1024 * 1024


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


@router.post("/infer", response_model=OccupancyInferenceRead)
def infer_occupancy(
    request: OccupancyInferenceRequest,
    db: Session = Depends(get_db),
) -> dict:
    room = db.get(Room, request.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    try:
        image_bytes = base64.b64decode(request.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="image_base64 must contain valid base64 data") from exc
    if not image_bytes:
        raise HTTPException(status_code=422, detail="The supplied image is empty")
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=422, detail="Decoded image exceeds the 5 MiB limit")
    expected_signature = b"\x89PNG\r\n\x1a\n" if request.image_format == "png" else b"\xff\xd8"
    if not image_bytes.startswith(expected_signature):
        raise HTTPException(
            status_code=422,
            detail="Image content does not match the selected JPEG or PNG format.",
        )
    try:
        validate_image_dimensions(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if find_spec("cv2") is None or find_spec("numpy") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "occupancy_inference_unavailable",
                "message": "OpenCV and NumPy are required for image occupancy inference.",
            },
        )

    suffix = ".png" if request.image_format == "png" else ".jpg"
    try:
        with TemporaryDirectory() as temporary_directory:
            image_path = Path(temporary_directory) / f"occupancy{suffix}"
            image_path.write_bytes(image_bytes)
            estimate = detect_occupancy(
                image_path,
                request.room_id,
                valid_room_ids=[room.room_id],
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "occupancy_inference_failed", "message": str(exc)},
        ) from exc

    return {
        "estimate": estimate,
        "capacity_students": room.capacity_students,
        "persisted": False,
    }
