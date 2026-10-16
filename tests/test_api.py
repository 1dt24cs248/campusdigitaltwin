from datetime import time

from backend.models import TimetableEntry


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


def test_simulator_checks_capacity_schedule_and_is_deterministic(seeded_client):
    request = {
        "timetable_entry_id": "TT0001",
        "source_room_id": "A-F1-04",
        "target_room_id": "A-G03",
        "student_count": 30,
    }

    response = seeded_client.post("/api/simulations", json=request)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "feasible"
    assert result["feasible"] is True
    assert result["checks"]["capacity"]["status"] == "pass"
    assert result["checks"]["destination_schedule"]["status"] == "pass"
    assert result["proposed"]["room_id"] == "A-G03"
    assert result["data_classification"] == "synthetic_or_illustrative"
    assert result["projected_metrics"]["moved_entry_count"] == 1
    assert result["projected_metrics"]["class_capacity_utilization"][0]["projected"]["allocation_utilization_percent"] == 75
    assert result["energy_impact"]["status"] == "unavailable"
    repeated = seeded_client.post("/api/simulations", json=request).json()
    assert repeated["simulation_id"] == result["simulation_id"]
    assert repeated["effects"] == result["effects"]
    assert seeded_client.post(
        "/api/simulations",
        json={**request, "source_room_id": "A-F2-01"},
    ).status_code == 422
    assert seeded_client.post(
        "/api/simulations",
        json={**request, "target_room_id": "UNKNOWN"},
    ).status_code == 404
    assert seeded_client.post(
        "/api/simulations",
        json={**request, "source_room_id": "UNKNOWN"},
    ).status_code == 404
    assert seeded_client.post(
        "/api/simulations",
        json={**request, "student_count": 41},
    ).json()["status"] == "infeasible"
    assert seeded_client.post(
        "/api/simulations",
        json={**request, "student_count": None},
    ).json()["status"] == "incomplete"
    conflict = seeded_client.post(
        "/api/simulations",
        json={**request, "target_room_id": "A-F4-01", "affected_student_counts": {"TT0031": 20}},
    ).json()
    assert conflict["status"] == "feasible"
    assert conflict["checks"]["destination_schedule"]["status"] == "pass"
    assert {item["timetable_entry_id"] for item in conflict["affected_entries"]} == {"TT0001", "TT0031"}
    assert conflict["effects"][1]["effect_type"] == "cascading_reassignment"
    assert conflict["projected_metrics"]["cascaded_entry_count"] == 1


def _add_test_entry(
    db_session,
    entry_id: str,
    room_id: str,
    *,
    start: time = time(8),
    end: time = time(8, 30),
    section: str | None = None,
    department: str = "CSE",
    faculty_id: str | None = None,
) -> None:
    db_session.add(
        TimetableEntry(
            timetable_entry_id=entry_id,
            semester=1,
            section=section if section is not None else entry_id,
            department=department,
            day_of_week="Monday",
            period_number=99,
            start_time=start,
            end_time=end,
            subject_code=entry_id,
            subject_name="Test timetable entry",
            room_id=room_id,
            faculty_id=faculty_id if faculty_id is not None else entry_id,
            session_type="Theory",
            data_status="SYNTHETIC test fixture",
        )
    )
    db_session.commit()


def test_simulator_cascades_multiple_entries_and_reports_affected_entities(
    seeded_client,
    db_session,
):
    _add_test_entry(db_session, "TEST-ROOT", "A-F1-04")
    _add_test_entry(db_session, "TEST-BLOCKER-1", "A-G03")
    _add_test_entry(db_session, "TEST-BLOCKER-2", "A-G03")
    request = {
        "timetable_entry_id": "TEST-ROOT",
        "source_room_id": "A-F1-04",
        "target_room_id": "A-G03",
        "student_count": 20,
        "affected_student_counts": {"TEST-BLOCKER-1": 10, "TEST-BLOCKER-2": 12},
    }

    result = seeded_client.post("/api/simulations", json=request).json()

    assert result["status"] == "feasible"
    assert result["checks"]["destination_schedule"]["status"] == "pass"
    assert result["checks"]["faculty_schedule"]["status"] == "pass"
    assert result["checks"]["section_schedule"]["status"] == "pass"
    assert result["checks"]["room_suitability"]["status"] == "not_checked"
    assert {"simulation_id", "checks", "baseline", "proposed", "effects"} <= result.keys()
    assert result["projected_metrics"]["moved_entry_count"] == 3
    assert result["projected_metrics"]["cascaded_entry_count"] == 2
    assert {effect["effect_type"] for effect in result["effects"]} == {
        "primary_relocation",
        "cascading_reassignment",
    }
    destinations = [entry["target_room_id"] for entry in result["affected_entries"]]
    assert len(destinations) == len(set(destinations))
    assert len(result["affected_entities"]) == 3 + len(result["projected_metrics"]["affected_room_ids"])
    db_session.expire_all()
    assert db_session.get(TimetableEntry, "TEST-ROOT").room_id == "A-F1-04"
    assert db_session.get(TimetableEntry, "TEST-BLOCKER-1").room_id == "A-G03"
    assert db_session.get(TimetableEntry, "TEST-BLOCKER-2").room_id == "A-G03"


def test_simulator_rejects_faculty_and_section_overlaps_across_rooms(
    seeded_client,
    db_session,
):
    _add_test_entry(db_session, "TEST-ROOT", "A-F1-04", faculty_id="FAC-SHARED", section="A")
    _add_test_entry(db_session, "TEST-FACULTY", "A-F1-01", faculty_id="FAC-SHARED", section="B")
    _add_test_entry(db_session, "TEST-SECTION", "A-F4-01", faculty_id="FAC-OTHER", section="A")

    result = seeded_client.post(
        "/api/simulations",
        json={
            "timetable_entry_id": "TEST-ROOT",
            "source_room_id": "A-F1-04",
            "target_room_id": "A-G03",
            "student_count": 20,
        },
    ).json()

    assert result["status"] == "infeasible"
    assert result["feasible"] is False
    assert result["checks"]["faculty_schedule"]["status"] == "fail"
    assert "TEST-FACULTY and TEST-ROOT" in result["checks"]["faculty_schedule"]["message"]
    assert result["checks"]["section_schedule"]["status"] == "fail"
    assert "TEST-ROOT and TEST-SECTION" in result["checks"]["section_schedule"]["message"]
    assert {
        tuple(conflict["timetable_entry_ids"]): set(conflict["constraint_types"])
        for conflict in result["unresolved_conflicts"]
    } == {
        ("TEST-FACULTY", "TEST-ROOT"): {"faculty"},
        ("TEST-ROOT", "TEST-SECTION"): {"section"},
    }


def test_simulator_allows_non_overlapping_consecutive_classes(seeded_client, db_session):
    _add_test_entry(db_session, "TEST-ROOT", "A-F1-04", end=time(8, 30), section="A")
    _add_test_entry(
        db_session,
        "TEST-NEXT",
        "A-G03",
        start=time(8, 30),
        end=time(9),
        faculty_id="TEST-ROOT",
        section="A",
    )

    result = seeded_client.post(
        "/api/simulations",
        json={
            "timetable_entry_id": "TEST-ROOT",
            "source_room_id": "A-F1-04",
            "target_room_id": "A-G03",
            "student_count": 20,
        },
    ).json()

    assert result["status"] == "feasible"
    assert result["checks"]["destination_schedule"]["status"] == "pass"
    assert result["checks"]["faculty_schedule"]["status"] == "pass"
    assert result["checks"]["section_schedule"]["status"] == "pass"


def test_simulator_reports_unknown_identifiers_and_unchecked_room_suitability(
    seeded_client,
    db_session,
):
    _add_test_entry(db_session, "TEST-ROOT", "A-F1-04")
    _add_test_entry(
        db_session,
        "TEST-MISSING-IDS",
        "A-F1-01",
        start=time(8, 10),
        end=time(8, 40),
        faculty_id="",
        section="",
    )

    result = seeded_client.post(
        "/api/simulations",
        json={
            "timetable_entry_id": "TEST-ROOT",
            "source_room_id": "A-F1-04",
            "target_room_id": "A-G03",
            "student_count": 20,
        },
    ).json()

    assert result["status"] == "incomplete"
    assert result["feasible"] is None
    assert result["checks"]["faculty_schedule"]["status"] == "unknown"
    assert result["checks"]["section_schedule"]["status"] == "unknown"
    assert "TEST-MISSING-IDS" in result["checks"]["faculty_schedule"]["message"]
    assert "TEST-MISSING-IDS" in result["checks"]["section_schedule"]["message"]
    assert result["checks"]["room_suitability"]["status"] == "not_checked"
    assert "not checked" in result["checks"]["room_suitability"]["message"]


def test_simulator_checks_cascade_assignments_for_resource_conflicts(
    seeded_client,
    db_session,
):
    _add_test_entry(db_session, "TEST-ROOT", "A-F1-04")
    _add_test_entry(db_session, "TEST-BLOCKER-1", "A-G03")
    _add_test_entry(db_session, "TEST-BLOCKER-2", "A-G03", faculty_id="FAC-CASCADE")
    _add_test_entry(db_session, "TEST-FACULTY", "A-F4-01", faculty_id="FAC-CASCADE")

    result = seeded_client.post(
        "/api/simulations",
        json={
            "timetable_entry_id": "TEST-ROOT",
            "source_room_id": "A-F1-04",
            "target_room_id": "A-G03",
            "student_count": 20,
            "affected_student_counts": {
                "TEST-BLOCKER-1": 10,
                "TEST-BLOCKER-2": 10,
            },
        },
    ).json()

    assert result["projected_metrics"]["cascaded_entry_count"] == 2
    assert result["checks"]["cascade_reassignment"]["status"] == "pass"
    assert result["checks"]["faculty_schedule"]["status"] == "fail"
    assert result["status"] == "infeasible"
    assert result["feasible"] is False
    assert any(
        set(conflict["timetable_entry_ids"]) == {"TEST-BLOCKER-2", "TEST-FACULTY"}
        and "faculty" in conflict["constraint_types"]
        for conflict in result["unresolved_conflicts"]
    )


def test_simulator_reports_ineligible_destination(seeded_client):
    result = seeded_client.post(
        "/api/simulations",
        json={
            "timetable_entry_id": "TT0001",
            "source_room_id": "A-F1-04",
            "target_room_id": "A-B01",
            "student_count": 20,
        },
    ).json()

    assert result["status"] == "infeasible"
    assert result["checks"]["destination_eligibility"]["status"] == "fail"


def test_simulator_reports_missing_class_size_and_impossible_reassignment(
    seeded_client,
    db_session,
):
    _add_test_entry(db_session, "TEST-ROOT", "A-F1-04")
    _add_test_entry(db_session, "TEST-BLOCKER", "A-G03")
    request = {
        "timetable_entry_id": "TEST-ROOT",
        "source_room_id": "A-F1-04",
        "target_room_id": "A-G03",
        "student_count": 20,
    }

    missing_data = seeded_client.post("/api/simulations", json=request).json()
    assert missing_data["status"] == "incomplete"
    assert missing_data["checks"]["cascade_reassignment"]["status"] == "unknown"
    assert "TEST-BLOCKER" in missing_data["checks"]["cascade_reassignment"]["message"]

    impossible = seeded_client.post(
        "/api/simulations",
        json={
            **request,
            "affected_student_counts": {"TEST-BLOCKER": 100_000},
        },
    ).json()
    assert impossible["status"] == "infeasible"
    assert impossible["checks"]["cascade_reassignment"]["status"] == "fail"
    assert impossible["unresolved_conflicts"]


def test_simulator_rejects_unknown_or_invalid_cascade_class_sizes(seeded_client):
    request = {
        "timetable_entry_id": "TT0001",
        "source_room_id": "A-F1-04",
        "target_room_id": "A-G03",
        "student_count": 30,
    }

    assert seeded_client.post(
        "/api/simulations",
        json={**request, "affected_student_counts": {"MISSING": 2}},
    ).status_code == 422
    assert seeded_client.post(
        "/api/simulations",
        json={**request, "affected_student_counts": {"TT0001": -1}},
    ).status_code == 422


def test_occupancy_context_is_separate_from_enrollment_and_must_match_scenario_room(seeded_client):
    payload = {
        "timetable_entry_id": "TT0001",
        "source_room_id": "A-F1-04",
        "target_room_id": "A-G03",
        "student_count": 30,
        "occupancy_scenario": {
            "room_id": "A-F1-04",
            "estimated_visible_person_count": 8,
            "observed_at": "2026-10-16T10:00:00Z",
            "source": "image_inference",
            "model": "OpenCV HOG test model",
        },
    }
    result = seeded_client.post("/api/simulations", json=payload)
    assert result.status_code == 200
    body = result.json()
    assert body["scenario_inputs"]["student_count"] == 30
    assert body["scenario_inputs"]["occupancy_scenario"]["estimated_visible_person_count"] == 8
    assert body["scenario_inputs"]["occupancy_scenario"]["room_id"] == "A-F1-04"

    mismatched = {**payload, "occupancy_scenario": {**payload["occupancy_scenario"], "room_id": "B-F1-09"}}
    assert seeded_client.post("/api/simulations", json=mismatched).status_code == 422
def test_energy_and_equipment_routes_filter_by_canonical_room(seeded_client):
    energy = seeded_client.get("/api/energy?room_id=A-G03")
    equipment = seeded_client.get("/api/equipment?room_id=A-G03")

    assert energy.status_code == 200
    assert energy.json()
    assert all(record["room_id"] == "A-G03" for record in energy.json())
    assert energy.json()[0]["data_status"] == "SYNTHETIC estimate"
    assert equipment.status_code == 200
    assert all(record["room_id"] == "A-G03" for record in equipment.json())


def test_sustainability_actions_preserve_supplied_data_status(seeded_client):
    response = seeded_client.get("/api/sustainability/actions")

    assert response.status_code == 200
    assert len(response.json()) == 4
    assert response.json()[0]["data_status"] == "Suggested action"
    assert all(action["requires_human_approval"] for action in response.json())
