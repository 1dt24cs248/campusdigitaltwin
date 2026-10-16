from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


MODEL_NAME = "OpenCV HOG default people detector (INRIA pedestrian SVM)"
LIMITATIONS = [
    "A single image is a snapshot, not evidence of continuous occupancy.",
    "Occlusion, seating position, lighting, camera angle, and non-upright poses can reduce detections.",
    "The detector is a general pedestrian model and is not calibrated for classroom seating.",
]


def detect_occupancy(
    image: str | Path | object,
    room_id: str,
    valid_room_ids: Iterable[str] | None = None,
) -> dict:
    """Estimate people in an image/frame using OpenCV's pretrained HOG detector."""
    if not isinstance(room_id, str) or not room_id.strip():
        raise ValueError("room_id must be a non-empty string")
    room_id = room_id.strip()
    if not room_id[0].isalnum() or any(
        not (character.isalnum() or character in "-_") for character in room_id
    ):
        raise ValueError("room_id may contain only letters, numbers, hyphens, and underscores")
    if valid_room_ids is not None and room_id not in set(valid_room_ids):
        raise ValueError(f"Unknown room_id: {room_id}")

    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise RuntimeError("OpenCV is required for image occupancy inference") from error

    if isinstance(image, (str, Path)):
        image_path = Path(image)
        if not image_path.is_file():
            raise FileNotFoundError(f"Image file does not exist: {image_path}")
        frame = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if frame is None:
            raise ValueError(f"Image could not be decoded: {image_path}")
    elif isinstance(image, np.ndarray):
        frame = image
    else:
        raise ValueError("image must be a file path or an OpenCV-compatible NumPy frame")

    if frame.size == 0:
        raise ValueError("Image frame is empty")
    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.ndim == 3 and frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    elif frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Image must be grayscale, BGR, or BGRA")

    try:
        detector = cv2.HOGDescriptor()
        detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        rectangles, _scores = detector.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
    except cv2.error as error:
        raise RuntimeError("OpenCV HOG inference failed") from error

    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "room_id": room_id,
        "estimated_occupancy": len(rectangles),
        "source": "image_inference",
        "status": "estimated",
        "observed_at": observed_at,
        "model": MODEL_NAME,
        "limitations": LIMITATIONS.copy(),
    }