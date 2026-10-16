import base64
from pathlib import Path

import cv2
import numpy as np

import backend.routes.occupancy as occupancy_routes
import backend.ai.explanations as explanations


def _blank_png_bytes(width=320, height=240):
    success, encoded = cv2.imencode(".png", np.zeros((height, width, 3), dtype=np.uint8))
    assert success
    return encoded.tobytes()


def test_recommendations_use_database_records_and_preserve_synthetic_provenance(seeded_client):
    response = seeded_client.get("/api/ai/recommendations")

    assert response.status_code == 200
    recommendations = response.json()
    room_recommendation = next(item for item in recommendations if item["room_id"] == "A-G03")
    assert room_recommendation["data_source"] == "synthetic_demo_data"
    assert room_recommendation["estimated_energy_impact"] is None
    assert room_recommendation["estimated_cost_impact"] is None
    assert not any(item["simulation_id"] is not None for item in recommendations)


def test_explanation_route_labels_supplied_result_as_unverified(seeded_client):
    simulation = seeded_client.post("/api/simulations", json={
        "timetable_entry_id": "TT0001", "source_room_id": "A-F1-04",
        "target_room_id": "A-G03", "student_count": 30,
    }).json()
    response = seeded_client.post(
        "/api/ai/explanations",
        json={"simulation_result": simulation},
    )

    assert response.status_code == 200
    explanation = response.json()
    assert explanation["simulation_id"] == simulation["simulation_id"]
    assert explanation["feasible"] == simulation["feasible"]
    assert explanation["input_provenance"] == "caller_supplied; not run or validated by this API"


def test_explanation_route_requires_an_object(seeded_client):
    response = seeded_client.post("/api/ai/explanations", json={"simulation_result": "not-an-object"})

    assert response.status_code == 422


def test_explanation_route_rejects_inconsistent_verdict(seeded_client):
    simulation = seeded_client.post("/api/simulations", json={
        "timetable_entry_id": "TT0001", "source_room_id": "A-F1-04",
        "target_room_id": "A-G03", "student_count": 30,
    }).json()
    simulation["feasible"] = not simulation["feasible"]
    assert seeded_client.post("/api/ai/explanations", json={"simulation_result": simulation}).status_code == 422


def test_explanation_route_includes_structured_relocation_entities(seeded_client):
    simulation = seeded_client.post(
        "/api/simulations",
        json={
            "timetable_entry_id": "TT0001",
            "source_room_id": "A-F1-04",
            "target_room_id": "A-G03",
            "student_count": 30,
        },
    ).json()

    response = seeded_client.post(
        "/api/ai/explanations",
        json={"simulation_result": simulation},
    )

    assert response.status_code == 200
    explanation = response.json()
    assert "source_room_id=A-F1-04" in explanation["explanation"]
    assert "target_room_id=A-G03" in explanation["explanation"]
    assert "affected_rooms=['A-F1-04', 'A-G03']" in explanation["explanation"]
    assert "affected_classes=['TT0001']" in explanation["explanation"]
    assert explanation["input_provenance"] == "caller_supplied; not run or validated by this API"


def test_chat_uses_model_with_database_context(seeded_client, monkeypatch):
    captured = {}
    monkeypatch.setenv("ECOTWIN_LLM_API_KEY", "test-key")

    def fake_completion(messages):
        captured["messages"] = messages
        return "Room A-G03 has a listed capacity of 40 in the campus records."

    monkeypatch.setattr(explanations, "_model_completion", fake_completion)
    response = seeded_client.post("/api/ai/chat", json={"question": "Which room fits 30?"})
    assert response.status_code == 200
    assert response.json()["source"] == "language_model"
    assert "A-G03" in response.json()["answer"]
    assert "A-G03" in captured["messages"][1]["content"]


def test_chat_falls_back_without_credentials(seeded_client, monkeypatch):
    monkeypatch.delenv("ECOTWIN_LLM_API_KEY", raising=False)
    response = seeded_client.post("/api/ai/chat", json={"question": "Explain occupancy limitations"})
    assert response.status_code == 200
    assert response.json()["source"] == "deterministic_fallback"
    assert "not configured" in response.json()["answer"]


def test_simulation_explanation_uses_model_but_preserves_verdict(seeded_client, monkeypatch):
    monkeypatch.setenv("ECOTWIN_LLM_API_KEY", "test-key")
    simulation = seeded_client.post("/api/simulations", json={
        "timetable_entry_id": "TT0001", "source_room_id": "A-F1-04",
        "target_room_id": "A-G03", "student_count": 1000,
    }).json()
    assert simulation["feasible"] is False
    captured = {}
    monkeypatch.setattr(explanations, "_model_completion", lambda messages: captured.setdefault("prompt", messages) and "This proposal is feasible per the simulator.")
    response = seeded_client.post("/api/ai/explanations", json={"simulation_result": simulation})
    assert response.status_code == 200
    assert response.json()["feasible"] is False
    assert response.json()["source"] == "deterministic_fallback"
    assert response.json()["provider_status"] == "conflicting_response"
    assert "infeasible" in response.json()["explanation"].lower()
    assert "feasible per the simulator" not in response.json()["explanation"].lower()
    assert "INFEASIBLE" in captured["prompt"][1]["content"]


def test_simulation_explanation_accepts_consistent_model_answer(seeded_client, monkeypatch):
    monkeypatch.setenv("ECOTWIN_LLM_API_KEY", "test-key")
    simulation = seeded_client.post("/api/simulations", json={
        "timetable_entry_id": "TT0001", "source_room_id": "A-F1-04",
        "target_room_id": "A-G03", "student_count": 30,
    }).json()
    assert simulation["feasible"] is True
    monkeypatch.setattr(explanations, "_model_completion", lambda _messages: "The simulator marks this proposal feasible for the listed rooms.")
    response = seeded_client.post("/api/ai/explanations", json={"simulation_result": simulation})
    assert response.status_code == 200
    assert response.json()["source"] == "language_model"
    assert response.json()["provider_status"] == "available"


def test_simulation_explanation_rejects_invented_room(seeded_client, monkeypatch):
    monkeypatch.setenv("ECOTWIN_LLM_API_KEY", "test-key")
    simulation = seeded_client.post("/api/simulations", json={
        "timetable_entry_id": "TT0001", "source_room_id": "A-F1-04",
        "target_room_id": "A-G03", "student_count": 30,
    }).json()
    monkeypatch.setattr(explanations, "_model_completion", lambda _messages: "A-X999 is an alternative room.")
    response = seeded_client.post("/api/ai/explanations", json={"simulation_result": simulation})
    assert response.status_code == 200
    assert response.json()["source"] == "deterministic_fallback"
    assert response.json()["provider_status"] == "conflicting_response"


def test_simulation_explanation_rejects_false_numeric_claim(seeded_client, monkeypatch):
    monkeypatch.setenv("ECOTWIN_LLM_API_KEY", "test-key")
    simulation = seeded_client.post("/api/simulations", json={
        "timetable_entry_id": "TT0001", "source_room_id": "A-F1-04",
        "target_room_id": "A-G03", "student_count": 30,
    }).json()
    monkeypatch.setattr(
        explanations,
        "_model_completion",
        lambda _messages: "The proposal is feasible and room A-G03 accommodates 999 students.",
    )

    response = seeded_client.post("/api/ai/explanations", json={"simulation_result": simulation})

    assert response.status_code == 200
    assert response.json()["feasible"] is True
    assert response.json()["source"] == "deterministic_fallback"
    assert response.json()["provider_status"] == "conflicting_response"
    assert "999" not in response.json()["explanation"]


def test_occupancy_inference_rejects_noncanonical_room_alias(seeded_client):
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A101",
            "image_format": "png",
            "image_base64": base64.b64encode(b"image").decode("ascii"),
        },
    )

    assert response.status_code == 404


def test_occupancy_inference_rejects_invalid_base64(seeded_client):
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={"room_id": "A-G03", "image_format": "png", "image_base64": "not base64!"},
    )

    assert response.status_code == 422


def test_occupancy_inference_reports_missing_optional_dependencies(seeded_client, monkeypatch):
    monkeypatch.setattr(
        occupancy_routes,
        "find_spec",
        lambda module_name: None if module_name == "cv2" else object(),
    )
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A-G03",
            "image_format": "png",
            "image_base64": base64.b64encode(_blank_png_bytes()).decode("ascii"),
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "occupancy_inference_unavailable"


def test_occupancy_inference_calls_member4_detector_without_persisting(
    seeded_client,
    monkeypatch,
):
    captured = {}

    def fake_detect_occupancy(image, room_id, valid_room_ids):
        captured["path_exists"] = Path(image).is_file()
        captured["room_id"] = room_id
        captured["valid_room_ids"] = list(valid_room_ids)
        return {
            "room_id": room_id,
            "estimated_occupancy": 3,
            "source": "image_inference",
            "status": "estimated",
            "observed_at": "2026-10-16T12:00:00Z",
            "limitations": ["Snapshot only"],
        }

    monkeypatch.setattr(occupancy_routes, "find_spec", lambda _module_name: object())
    monkeypatch.setattr(occupancy_routes, "detect_occupancy", fake_detect_occupancy)
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A-G03",
            "image_format": "png",
            "image_base64": base64.b64encode(_blank_png_bytes()).decode("ascii"),
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["estimate"]["estimated_occupancy"] == 3
    assert result["capacity_students"] == 40
    assert result["persisted"] is False
    assert captured == {
        "path_exists": True,
        "room_id": "A-G03",
        "valid_room_ids": ["A-G03"],
    }


def test_occupancy_inference_processes_a_valid_image_without_persisting(seeded_client):
    success, encoded = cv2.imencode(".png", np.zeros((240, 320, 3), dtype=np.uint8))
    assert success
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A-G03",
            "image_format": "png",
            "image_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["estimate"]["source"] == "image_inference"
    assert result["estimate"]["image_width"] == 320
    assert result["estimate"]["image_height"] == 240
    assert result["estimate"]["estimated_occupancy"] == 0
    assert result["persisted"] is False


def test_occupancy_inference_rejects_images_smaller_than_hog_window(seeded_client):
    success, encoded = cv2.imencode(".png", np.zeros((1, 1, 3), dtype=np.uint8))
    assert success
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A-G03",
            "image_format": "png",
            "image_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Image must be at least 64 pixels wide and 128 pixels tall for the HOG people detector."
    )


def test_occupancy_inference_rejects_excessive_dimensions_before_decode(seeded_client):
    image_header = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + (5000).to_bytes(4, "big")
        + (4000).to_bytes(4, "big")
    )
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A-G03",
            "image_format": "png",
            "image_base64": base64.b64encode(image_header).decode("ascii"),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Image dimensions 5000x4000 exceed the 16,777,216-pixel limit."
    )


def test_occupancy_inference_processes_jpeg_without_persisting(seeded_client):
    success, encoded = cv2.imencode(".jpg", np.zeros((180, 240, 3), dtype=np.uint8))
    assert success
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A-G03",
            "image_format": "jpeg",
            "image_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["estimate"]["image_width"] == 240
    assert result["estimate"]["image_height"] == 180
    assert result["persisted"] is False


def test_occupancy_inference_rejects_corrupt_image(seeded_client):
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A-G03",
            "image_format": "png",
            "image_base64": base64.b64encode(b"\x89PNG\r\n\x1a\ntruncated").decode("ascii"),
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Image could not be decoded. Choose a valid JPEG or PNG image."


def test_occupancy_inference_rejects_declared_format_mismatch(seeded_client):
    success, encoded = cv2.imencode(".png", np.zeros((240, 320, 3), dtype=np.uint8))
    assert success
    response = seeded_client.post(
        "/api/occupancy/infer",
        json={
            "room_id": "A-G03",
            "image_format": "jpeg",
            "image_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Image content does not match the selected JPEG or PNG format."
