from datetime import datetime

import numpy as np

from backend.ai import generate_explanation, generate_recommendations
from backend.vision import detect_occupancy


def test_member4_functions_compose_without_shared_backend_or_simulator():
    occupancy = detect_occupancy(np.zeros((240, 320, 3), dtype=np.uint8), "A101")
    observation_time = datetime.fromisoformat(occupancy["observed_at"].replace("Z", "+00:00"))
    simulation_result = {
        "simulation_id": "SIM-TEST-REJECTED",
        "feasible": False,
        "validation_errors": ["Capacity exceeded"],
        "energy_saved_kwh_day": -16,
        "cost_saved_inr_day": -136,
    }

    recommendations = generate_recommendations(
        {
            "rooms": [{"room_id": occupancy["room_id"], "building_id": "A", "capacity": 40}],
            "occupancy_observations": [{
                "room_id": occupancy["room_id"],
                "detected_person_count": occupancy["estimated_occupancy"],
                "observed_at": occupancy["observed_at"],
                "source": occupancy["source"],
            }],
            "timetable": [{"room_id": occupancy["room_id"], "period_number": 1}],
        },
        simulation_results=[simulation_result],
        now=observation_time,
    )
    occupancy_recommendation = next(item for item in recommendations if item["room_id"] == "A101")
    simulation_recommendation = next(
        item for item in recommendations if item["simulation_id"] == "SIM-TEST-REJECTED"
    )
    explanation = generate_explanation(simulation_result)

    assert occupancy_recommendation["data_source"] == "image_inference"
    assert occupancy_recommendation["estimated_energy_impact"] is None
    assert simulation_recommendation["simulator_reported_impacts"] == {
        "energy_saved_kwh_day": -16,
        "cost_saved_inr_day": -136,
    }
    assert explanation["source"] == "deterministic_fallback"
    assert explanation["feasible"] is False
    assert explanation["validation_errors"] == ["Capacity exceeded"]
    assert explanation["simulator_metrics"]["energy_saved_kwh_day"] == -16
    assert explanation["simulator_metrics"]["cost_saved_inr_day"] == -136