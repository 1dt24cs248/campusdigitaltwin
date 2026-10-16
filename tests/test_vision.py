from datetime import datetime

import cv2
import numpy as np
import pytest

from backend.vision.detector import (
    MAX_IMAGE_PIXELS,
    detect_occupancy,
    validate_image_dimensions,
)


def test_valid_frame_runs_model_and_returns_image_inference_result():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    result = detect_occupancy(frame, "A101", ["A101"])

    assert result["room_id"] == "A101"
    assert isinstance(result["estimated_occupancy"], int)
    assert result["estimated_occupancy"] >= 0
    assert result["source"] == "image_inference"
    assert result["status"] == "estimated"
    assert datetime.fromisoformat(result["observed_at"].replace("Z", "+00:00"))
    assert "HOG" in result["model"]
    assert result["image_width"] == 320
    assert result["image_height"] == 240
    assert isinstance(result["detections"], list)
    assert result["limitations"]


def test_file_path_runs_model(tmp_path):
    path = tmp_path / "blank.png"
    assert cv2.imwrite(str(path), np.zeros((240, 320, 3), dtype=np.uint8))
    assert detect_occupancy(path, "A101")["source"] == "image_inference"


def test_missing_image_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        detect_occupancy(tmp_path / "missing.png", "A101")


def test_corrupt_image_is_rejected(tmp_path):
    path = tmp_path / "corrupt.png"
    path.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="could not be decoded"):
        detect_occupancy(path, "A101")


@pytest.mark.parametrize("height,width", [(127, 64), (128, 63)])
def test_images_smaller_than_hog_window_are_rejected(height, width):
    with pytest.raises(ValueError, match="at least 64 pixels wide and 128 pixels tall"):
        detect_occupancy(np.zeros((height, width, 3), dtype=np.uint8), "A101")


def _png_header(width, height):
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
    )


def test_excessive_png_dimensions_are_rejected_before_decode():
    image_bytes = _png_header(MAX_IMAGE_PIXELS + 1, 1)

    with pytest.raises(ValueError, match="exceed the 16,777,216-pixel limit"):
        validate_image_dimensions(image_bytes)


def test_unsupported_or_truncated_image_headers_are_rejected_before_decode():
    with pytest.raises(ValueError, match="Choose a valid JPEG or PNG"):
        validate_image_dimensions(b"RIFF\x00\x00\x00\x00WEBP")
    with pytest.raises(ValueError, match="Choose a valid JPEG or PNG"):
        validate_image_dimensions(b"\x89PNG\r\n\x1a\n")


def test_excessive_jpeg_dimensions_are_rejected_before_decode():
    width, height = 5000, 4000
    image_bytes = (
        b"\xff\xd8\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x00" * 10
    )

    with pytest.raises(ValueError, match="exceed the 16,777,216-pixel limit"):
        validate_image_dimensions(image_bytes)


def test_oversized_numpy_frame_is_rejected_without_copying_pixels():
    pixel = np.zeros((1, 1, 3), dtype=np.uint8)
    oversized = np.lib.stride_tricks.as_strided(
        pixel,
        shape=(4097, 4097, 3),
        strides=(0, 0, 0),
    )

    with pytest.raises(ValueError, match="exceed the 16,777,216-pixel limit"):
        detect_occupancy(oversized, "A101")


def test_invalid_room_ids_are_rejected():
    with pytest.raises(ValueError, match="Unknown room_id"):
        detect_occupancy(np.zeros((240, 320, 3), dtype=np.uint8), "A999", ["A101"])
    with pytest.raises(ValueError, match="non-empty"):
        detect_occupancy(np.zeros((240, 320, 3), dtype=np.uint8), " ")


def test_synthetic_count_payload_cannot_be_used_as_image_inference():
    with pytest.raises(ValueError, match="image must be a file path"):
        detect_occupancy({"estimated_occupancy": 12, "source": "synthetic_demo_data"}, "A101")


def test_inference_failure_is_not_reported_as_estimate(monkeypatch):
    class FailingDetector:
        winSize = (64, 128)

        def setSVMDetector(self, _detector):
            pass

        def detectMultiScale(self, *_args, **_kwargs):
            raise cv2.error("inference failed")

    monkeypatch.setattr(cv2, "HOGDescriptor", FailingDetector)
    with pytest.raises(RuntimeError, match="inference failed"):
        detect_occupancy(np.zeros((240, 320, 3), dtype=np.uint8), "A101")
