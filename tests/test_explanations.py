from backend.ai.explanations import explanation_conflicts_with_result, generate_explanation


def test_explanation_preserves_rejected_result_and_signed_values():
    result = generate_explanation({
        "simulation_id": "SIM004", "feasible": False,
        "validation_errors": ["Capacity exceeded"],
        "baseline_energy_kwh_day": 520, "proposed_energy_kwh_day": 536,
        "energy_saved_kwh_day": -16, "cost_saved_inr_day": -136,
        "walking_distance_change_m_day": -40,
    })

    assert result["source"] == "deterministic_fallback"
    assert result["feasible"] is False
    assert result["simulator_metrics"]["energy_saved_kwh_day"] == -16
    assert "-16 kWh/day" in result["explanation"]
    assert "-136 INR/day" in result["explanation"]
    assert "infeasible" in result["explanation"]
    assert "Capacity exceeded" in result["explanation"]


def test_missing_values_are_reported_as_unavailable():
    result = generate_explanation({"simulation_id": "SIM001"})

    assert result["feasible"] is None
    assert "Baseline Energy: unavailable" in result["explanation"]
    assert "feasibility is unavailable" in result["explanation"].lower()


def test_nested_metrics_and_assumptions_are_supported():
    result = generate_explanation({
        "is_feasible": True,
        "metrics": {"baseline_energy_kwh": 100, "proposed_energy_kwh": 90},
        "assumptions": ["Tariff not supplied"],
    })

    assert result["simulator_metrics"] == {
        "baseline_energy_kwh": 100, "proposed_energy_kwh": 90,
    }
    assert "Tariff not supplied" in result["explanation"]
    assert "simulator marks this proposal feasible" in result["explanation"]


def test_caller_context_is_echoed_without_changing_simulator_verdict():
    result = generate_explanation(
        {"feasible": False, "validation_errors": ["Room conflict"]},
        {"timetable_constraints": ["Faculty availability not checked"]},
    )

    assert result["feasible"] is False
    assert result["campus_context"]["timetable_constraints"] == ["Faculty availability not checked"]
    assert "Faculty availability not checked" in result["explanation"]


def test_model_explanation_rejects_false_numeric_claims_even_when_verdict_matches():
    simulation = {
        "feasible": True,
        "baseline": {"room_id": "A-F1-04"},
        "proposed": {"room_id": "A-G03"},
        "checks": {"capacity": {"status": "pass"}},
        "energy_impact": {"status": "unavailable"},
    }

    assert explanation_conflicts_with_result(
        "The proposal is feasible and room A-G03 accommodates 999 students.", simulation,
    )
    assert explanation_conflicts_with_result(
        "The proposal is feasible and provides energy savings of 20%.", simulation,
    )
    assert explanation_conflicts_with_result(
        "The proposal is feasible and room A-G03 accommodates nine hundred students.", simulation,
    )


def test_model_explanation_rejects_individual_check_claim_that_conflicts():
    simulation = {
        "feasible": None,
        "baseline": {"room_id": "A-F1-04"},
        "proposed": {"room_id": "A-G03"},
        "checks": {"faculty_schedule": {"status": "unknown"}},
    }

    assert explanation_conflicts_with_result(
        "The result is incomplete, but the faculty check passed.", simulation,
    )
