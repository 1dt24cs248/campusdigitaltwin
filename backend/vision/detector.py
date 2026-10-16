from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


MODEL_NAME = "OpenCV HOG default people detector (INRIA pedestrian SVM)"
MAX_IMAGE_PIXELS = 16_777_216
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_START_OF_FRAME_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}
LIMITATIONS = [
    "A single image is a snapshot, not evidence of continuous occupancy.",
    "Occlusion, seating position, lighting, camera angle, and non-upright poses can reduce detections.",
    "The detector is a general pedestrian model and is not calibrated for classroom seating.",
]


def validate_image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Validate PNG/JPEG headers and reject oversized images before pixel decode."""
    width = height = 0
    if image_bytes.startswith(_PNG_SIGNATURE):
        if len(image_bytes) >= 24 and image_bytes[12:16] == b"IHDR":
            width = int.from_bytes(image_bytes[16:20], "big")
            height = int.from_bytes(image_bytes[20:24], "big")
        else:
            raise ValueError("Image could not be decoded. Choose a valid JPEG or PNG image.")
    elif image_bytes.startswith(b"\xff\xd8"):
        offset = 2
        while offset < len(image_bytes):
            if image_bytes[offset] != 0xFF:
                break
            while offset < len(image_bytes) and image_bytes[offset] == 0xFF:
                offset += 1
            if offset >= len(image_bytes):
                break
            marker = image_bytes[offset]
            offset += 1
            if marker in {0xD9, 0xDA}:
                break
            if marker == 0x01 or 0xD0 <= marker <= 0xD7:
                continue
            if offset + 2 > len(image_bytes):
                break
            segment_length = int.from_bytes(image_bytes[offset:offset + 2], "big")
            if segment_length < 2 or offset + segment_length > len(image_bytes):
                break
            segment_start = offset + 2
            if marker in _JPEG_START_OF_FRAME_MARKERS:
                segment = image_bytes[segment_start:offset + segment_length]
                if len(segment) >= 5:
                    height = int.from_bytes(segment[1:3], "big")
                    width = int.from_bytes(segment[3:5], "big")
                break
            offset += segment_length
        if width <= 0 or height <= 0:
            raise ValueError("Image could not be decoded. Choose a valid JPEG or PNG image.")
    else:
        raise ValueError("Image could not be decoded. Choose a valid JPEG or PNG image.")

    if width <= 0 or height <= 0:
        raise ValueError("Image could not be decoded. Choose a valid JPEG or PNG image.")
    if width * height > MAX_IMAGE_PIXELS:
        raise ValueError(
            f"Image dimensions {width}x{height} exceed the "
            f"{MAX_IMAGE_PIXELS:,}-pixel limit."
        )
    return width, height


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
        image_bytes = image_path.read_bytes()
        validate_image_dimensions(image_bytes)
        frame = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if frame is None:
            raise ValueError("Image could not be decoded. Choose a valid JPEG or PNG image.")
    elif isinstance(image, np.ndarray):
        frame = image
    else:
        raise ValueError("image must be a file path or an OpenCV-compatible NumPy frame")

    if frame.size == 0:
        raise ValueError("Image frame is empty")
    if frame.ndim == 2:
        height, width = frame.shape
    elif frame.ndim == 3 and frame.shape[2] in {3, 4}:
        height, width = frame.shape[:2]
    else:
        raise ValueError("Image must be grayscale, BGR, or BGRA")
    if width * height > MAX_IMAGE_PIXELS:
        raise ValueError(
            f"Image dimensions {width}x{height} exceed the "
            f"{MAX_IMAGE_PIXELS:,}-pixel limit."
        )
    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.ndim == 3 and frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    detector = cv2.HOGDescriptor()
    window_width, window_height = detector.winSize
    if frame.shape[1] < window_width or frame.shape[0] < window_height:
        raise ValueError(
            f"Image must be at least {window_width} pixels wide and "
            f"{window_height} pixels tall for the HOG people detector."
        )

    try:
        detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        rectangles, scores = detector.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
    except cv2.error as error:
        raise RuntimeError("OpenCV HOG inference failed") from error

    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    detections = []
    for index, (x, y, width, height) in enumerate(rectangles):
        item = {"x": int(x), "y": int(y), "width": int(width), "height": int(height)}
        if index < len(scores):
            item["detector_score"] = float(scores[index])
        detections.append(item)
    return {
        "room_id": room_id,
        "estimated_occupancy": len(rectangles),
        "image_width": int(frame.shape[1]),
        "image_height": int(frame.shape[0]),
        "source": "image_inference",
        "status": "estimated",
        "observed_at": observed_at,
        "model": MODEL_NAME,
        "detections": detections,
        "limitations": LIMITATIONS.copy(),
    }
