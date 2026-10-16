from datetime import datetime, timezone

from backend.ai.recommendations import generate_recommendations


NOW = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)


def test_stale_synthetic_observation_is_labeled_and_not_used_for_utilization():
    recommendations = generate_recommendations({
        "rooms": [{"room_id": "A-G03", "building_id": "A", "capacity_students": 40}],
        "occupancy_observations": [{
            "room_id": "A-G03", "detected_person_count": 0,
            "observed_at": "2026-10-15T10:15:00+05:30", "data_status": "SYNTHETIC observation",
        }],
    }, now=NOW)

    assert len(recommendations) == 1
    assert recommendations[0]["data_source"] == "synthetic_demo_data"
    assert "Verify current occupancy" in recommendations[0]["title"]
    assert recommendations[0]["estimated_energy_impact"] is None


def test_low_count_recommends_review_and_mentions_timetable():
    recommendations = generate_recommendations({
        "rooms": [{"room_id": "A101", "building_id": "A", "capacity": 40}],
        "occupancy_observations": [{
            "room_id": "A101", "detected_person_count": 2,
            "observed_at": "2026-10-16T11:30:00Z", "source": "manual_input",
        }],
        "timetable": [{"room_id": "A101", "start_time": "12:00"}],
    }, now=NOW)

    assert len(recommendations) == 1
    item = recommendations[0]
    assert item["room_id"] == "A101"
    assert item["data_source"] == "manual_input"
    assert any("timetable" in constraint for constraint in item["operational_constraints"])
    assert item["estimated_cost_impact"] is None
    assert item["requires_verification"] is True


def test_react_nested_campus_fixture_is_supported():
    recommendations = generate_recommendations({
        "buildings": [{"building_id": "A", "floors": [{"rooms": [{
            "room_id": "A-101", "capacity": 120,
            "latest_occupancy": {
                "observed_person_count": 1, "observation_timestamp": "2026-10-16T11:00:00Z",
                "data_status": "Synthetic demonstration data",
            },
        }]}]}],
    }, now=NOW)

    assert recommendations[0]["building_id"] == "A"
    assert "synthetic" in " ".join(recommendations[0]["confidence_limitations"]).lower()


def test_simulation_values_and_validation_errors_are_passed_through():
    results = generate_recommendations({}, [{
        "simulation_id": "SIM004", "feasible": False,
        "energy_saved_kwh_day": -16, "cost_saved_inr_day": -136,
        "validation_errors": ["Capacity exceeded"], "data_status": "simulator output",
    }])

    assert results[0]["simulation_id"] == "SIM004"
    assert results[0]["simulator_reported_impacts"] == {
        "energy_saved_kwh_day": -16, "cost_saved_inr_day": -136,
    }
    assert results[0]["operational_constraints"] == ["Capacity exceeded"]
    assert results[0]["estimated_energy_impact"] is None
    assert "Revise rejected" in results[0]["title"]


def test_operating_equipment_requires_explicit_state_and_never_claims_savings():
    results = generate_recommendations({
        "rooms": [{"room_id": "A101", "capacity": 40}],
        "occupancy_observations": [{
            "room_id": "A101", "detected_person_count": 0,
            "observed_at": "2026-10-16T11:30:00Z", "source": "image_inference",
        }],
        "equipment_inventory": [{
            "room_id": "A101", "equipment_type": "Projector", "operating": True,
            "data_status": "measured status",
        }],
    }, now=NOW)

    item = next(item for item in results if "equipment operation" in item["title"].lower())
    assert item["estimated_energy_impact"] is None
    assert item["estimated_cost_impact"] is None
    assert "no energy consumption or waste is inferred" in item["operational_constraints"][0]