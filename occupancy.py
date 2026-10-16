"""Prototype occupancy estimation with explicit synthetic/model provenance."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Collection


MODEL_ID = "opencv_hog_default_people_detector"
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
MODEL_LIMITATIONS = [
    "HOG pedestrian detection is not validated for classroom occupancy and may miss seated, occluded, small, or overhead-view people.",
    "A single image is a snapshot, not evidence of continuous occupancy or attendance.",
    "Lighting, camera angle, image resolution, and false detections affect the estimate.",
]


class OccupancyInputError(ValueError):
    """Raised when occupancy metadata cannot be validated."""


class OccupancyInferenceError(RuntimeError):
    """Raised when the image could not be processed by the detector."""


def _validate_metadata(
    room_id: str,
    capacity_students: int,
    known_room_ids: Collection[str] | None,
) -> None:
    if not isinstance(room_id, str) or not room_id.strip():
        raise OccupancyInputError("room_id is required")
    if isinstance(capacity_students, bool) or not isinstance(capacity_students, int) or capacity_students <= 0:
        raise OccupancyInputError("capacity_students must be a positive integer")
    if known_room_ids is not None and room_id not in known_room_ids:
        raise OccupancyInputError(f"Unknown room_id: {room_id}")


def _make_result(
    room_id: str,
    detection_count: int,
    capacity_students: int,
    model: str,
    source: str,
    detector_scores: list[float] | None,
) -> dict[str, Any]:
    over_capacity = detection_count > capacity_students
    return {
        "room_id": room_id,
        "estimated_occupancy": detection_count,
        "capacity_students": capacity_students,
        "occupancy_ratio": round(detection_count / capacity_students, 4),
        "source": source,
        "status": "over_capacity" if over_capacity else "estimated",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "data_label": source,
        "confidence": None,
        "detector_scores": detector_scores,
        "score_note": "Detector scores are not calibrated confidence probabilities.",
        "limitations": list(MODEL_LIMITATIONS),
        "warning": (
            "Detected count exceeds stated room capacity; review the frame and room metadata."
            if over_capacity
            else "Person detections are an estimate and may include misses or false positives."
        ),
    }


def estimate_from_detection_count(
    room_id: str,
    detection_count: int,
    capacity_students: int,
    detector: str,
    detector_scores: list[float] | None = None,
) -> dict[str, Any]:
    """Validate a bare count without claiming it came from image inference."""
    _validate_metadata(room_id, capacity_students, None)
    if isinstance(detection_count, bool) or not isinstance(detection_count, int) or detection_count < 0:
        raise OccupancyInputError("detection_count must be a non-negative integer")
    if not detector or not detector.strip():
        raise OccupancyInputError("detector name is required")
    if detector_scores is not None and any(not math.isfinite(score) for score in detector_scores):
        raise OccupancyInputError("detector_scores must contain finite numbers")
    result = _make_result(
        room_id, detection_count, capacity_students, detector, "unknown", detector_scores
    )
    result["model"] = None
    result["reported_detector"] = detector
    result["room_id_validation"] = "not_checked"
    result["limitations"].append("A bare count is not evidence of image inference.")
    return result


def estimate_from_manual_input(
    room_id: str,
    occupancy: int,
    capacity_students: int,
    known_room_ids: Collection[str] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Represent an operator-entered count without labeling it as vision output."""
    _validate_metadata(room_id, capacity_students, known_room_ids)
    if isinstance(occupancy, bool) or not isinstance(occupancy, int) or occupancy < 0:
        raise OccupancyInputError("occupancy must be a non-negative integer")
    if observed_at is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    else:
        try:
            parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as error:
            raise OccupancyInputError("observed_at must be an ISO-8601 timestamp") from error
        timestamp = (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed).isoformat()
    result = _make_result(
        room_id, occupancy, capacity_students, "manual_entry", "manual_input", None
    )
    result["observed_at"] = timestamp
    result["model"] = None
    result["room_id_validation"] = "verified" if known_room_ids is not None else "not_checked"
    result["warning"] = "Manual occupancy is user-entered and is not verified by computer vision."
    result["limitations"] = [
        "The count was entered by a user and was not verified by computer vision.",
        "A single observation is a snapshot, not proof of continuous room use.",
    ]
    return result


def estimate_from_image(
    image_path: str | Path,
    room_id: str,
    capacity_students: int,
    known_room_ids: Collection[str] | None = None,
) -> dict[str, Any]:
    """Estimate standing-person count in an image using OpenCV's HOG detector.

    This is a no-training prototype, not a validated classroom occupancy model.
    It does not retain or upload the image. HOG is especially likely to miss
    seated, occluded, small, or overhead-view people.
    """
    _validate_metadata(room_id, capacity_students, known_room_ids)
    try:
        path = Path(image_path)
    except (TypeError, ValueError) as error:
        raise OccupancyInputError("image_path must be a filesystem path") from error
    if path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise OccupancyInputError(f"Unsupported image format: {path.suffix or '(no extension)'}")
    if not path.is_file():
        raise FileNotFoundError(f"Image file does not exist: {path}")
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError(
            "Image inference requires OpenCV. Install with `python -m pip install -r requirements-vision.txt`."
        ) from error
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise OccupancyInputError(f"Image is corrupt or unreadable: {path}")
    return estimate_from_frame(image, room_id, capacity_students, known_room_ids)


def estimate_from_frame(
    frame: Any,
    room_id: str,
    capacity_students: int,
    known_room_ids: Collection[str] | None = None,
) -> dict[str, Any]:
    """Run HOG inference on a decoded OpenCV frame or compatible array."""
    _validate_metadata(room_id, capacity_students, known_room_ids)
    if frame is None or not hasattr(frame, "shape"):
        raise OccupancyInputError("frame must be a decoded image array")
    shape = frame.shape
    if len(shape) not in (2, 3) or shape[0] <= 0 or shape[1] <= 0:
        raise OccupancyInputError("frame has invalid image dimensions")
    if len(shape) == 3 and shape[2] not in (1, 3, 4):
        raise OccupancyInputError("frame must have 1, 3, or 4 color channels")

    try:
        import cv2
    except ImportError as error:
        raise RuntimeError(
            "Image inference requires OpenCV. Install with `python -m pip install -r requirements-vision.txt`."
        ) from error

    try:
        if len(shape) == 2 or (len(shape) == 3 and shape[2] == 1):
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif len(shape) == 3 and shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        detector = cv2.HOGDescriptor()
        detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        rectangles, raw_scores = detector.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
        if rectangles is None:
            raise RuntimeError("detector returned no result")
        if hasattr(raw_scores, "flatten"):
            raw_scores = raw_scores.flatten()
        scores = [float(score) for score in raw_scores]
    except Exception as error:
        raise OccupancyInferenceError(f"OpenCV HOG inference failed: {error}") from error

    result = _make_result(
        room_id,
        len(rectangles),
        capacity_students,
        MODEL_ID,
        "image_inference",
        scores,
    )
    result["image_retained"] = False
    result["room_id_validation"] = "verified" if known_room_ids is not None else "not_checked"
    return result