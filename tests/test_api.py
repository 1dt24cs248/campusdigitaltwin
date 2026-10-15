def test_buildings_list_detail_and_unknown_id(seeded_client):
    response = seeded_client.get("/api/buildings")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["data_status"] == "SYNTHETIC"
    assert seeded_client.get("/api/buildings/A").json()["building_name"] == "A Block"
    assert seeded_client.get("/api/buildings/UNKNOWN").status_code == 404


def test_room_filters_detail_timetable_and_missing_room(seeded_client):
    response = seeded_client.get(
        "/api/rooms",
        params={
            "building_id": "A",
            "floor_number": -1,
            "min_capacity": 0,
            "max_capacity": 24,
            "timetable_eligible": "false",
        },
    )

    assert response.status_code == 200
    assert response.json()
    assert all(room["building_id"] == "A" and not room["timetable_eligible"] for room in response.json())
    assert seeded_client.get("/api/rooms/A-B01").json()["room_id"] == "A-B01"
    assert seeded_client.get("/api/rooms/A-F1-04/timetable?semester=1").status_code == 200
    assert seeded_client.get("/api/rooms/UNKNOWN").status_code == 404
    assert seeded_client.get("/api/rooms?min_capacity=30&max_capacity=10").status_code == 422
    assert seeded_client.get("/api/rooms?min_capacity=-1").status_code == 422


def test_timetable_filters_and_no_implicit_semester(seeded_client):
    response = seeded_client.get(
        "/api/timetables",
        params={"semester": 1, "section": "A", "day_of_week": "Monday", "subject_code": "CSE101"},
    )

    assert response.status_code == 200
    assert [entry["timetable_entry_id"] for entry in response.json()] == ["TT0001"]
    assert response.json()[0]["data_status"] == "SYNTHETIC - illustrative timetable"
    assert seeded_client.get("/api/timetables?limit=500").json()
    assert len(seeded_client.get("/api/timetables?semester=1&limit=500").json()) == 60


def test_occupancy_validation_and_provenance(seeded_client):
    payload = {
        "room_id": "A-G03",
        "detected_person_count": 5,
        "observed_at": "2026-10-15T11:00:00+05:30",
        "detection_method": "manual demo estimate",
        "confidence_score": 0.8,
        "data_status": "USER_SUBMITTED_ESTIMATE",
    }
    created = seeded_client.post("/api/occupancy", json=payload)

    assert created.status_code == 201
    assert created.json()["detected_person_count"] == 5
    assert created.json()["data_status"] == "USER_SUBMITTED_ESTIMATE"
    assert created.json()["detection_method"] == "manual demo estimate"
    assert seeded_client.get("/api/occupancy?room_id=A-G03").json()
    assert seeded_client.post("/api/occupancy", json={**payload, "detected_person_count": -1}).status_code == 422
    assert seeded_client.post("/api/occupancy", json={**payload, "room_id": "UNKNOWN"}).status_code == 404


def test_simulator_returns_explicit_pending_without_calculating(seeded_client):
    request = {
        "timetable_entry_id": "TT0001",
        "source_room_id": "A-F1-04",
        "target_room_id": "A-F2-01",
    }

    response = seeded_client.post("/api/simulations", json=request)

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "integration_pending"
    assert "no simulation was calculated" in response.json()["detail"]["message"].lower()
    assert seeded_client.post(
        "/api/simulations",
        json={**request, "source_room_id": "A-F2-01"},
    ).status_code == 422
    assert seeded_client.post(
        "/api/simulations",
        json={**request, "target_room_id": "UNKNOWN"},
    ).status_code == 404


def test_sustainability_actions_preserve_supplied_data_status(seeded_client):
    response = seeded_client.get("/api/sustainability/actions")

    assert response.status_code == 200
    assert len(response.json()) == 4
    assert response.json()[0]["data_status"] == "Suggested action"
    assert all(action["requires_human_approval"] for action in response.json())
