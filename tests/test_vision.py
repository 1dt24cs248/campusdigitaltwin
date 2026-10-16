from datetime import datetime

import cv2
import numpy as np
import pytest

from backend.vision.detector import detect_occupancy


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
        def setSVMDetector(self, _detector):
            pass

        def detectMultiScale(self, *_args, **_kwargs):
            raise cv2.error("inference failed")

    monkeypatch.setattr(cv2, "HOGDescriptor", FailingDetector)
    with pytest.raises(RuntimeError, match="inference failed"):
        detect_occupancy(np.zeros((240, 320, 3), dtype=np.uint8), "A101")