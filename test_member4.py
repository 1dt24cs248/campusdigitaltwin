import csv
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from explanations import (
    build_simulation_explanation,
    explain_occupancy,
    explain_recommendation,
    explain_simulation,
)
from occupancy import (
    OccupancyInputError,
    estimate_from_detection_count,
    estimate_from_frame,
    estimate_from_image,
    estimate_from_manual_input,
)
from scripts.generate_demo_data import generate_demo_data
from simulator import (
    CampusData,
    EnergyRecord,
    EquipmentRecord,
    Room,
    SimulationRequest,
    TimetableEntry,
    simulate_reassignment,
)
from sustainability import build_recommendations


PROJECT_DIR = Path(__file__).resolve().parent
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def action_fixtures():
    return [
        {
            "action_id": "A1", "action_name": "Review occupancy",
            "trigger_type": "low_observed_occupancy", "description": "Review occupancy.",
            "priority": "review",
        },
        {
            "action_id": "A2", "action_name": "Inspect connected load",
            "trigger_type": "high_connected_load", "description": "Inspect load.",
            "priority": "operational",
        },
        {
            "action_id": "A3", "action_name": "Verify tariff",
            "trigger_type": "unverified_tariff", "description": "Verify tariff.",
            "priority": "data_quality",
        },
        {
            "action_id": "A4", "action_name": "Refresh occupancy",
            "trigger_type": "missing_or_stale_occupancy", "description": "Refresh occupancy.",
            "priority": "data_quality",
        },
        {
            "action_id": "A5", "action_name": "Review equipment runtime",
            "trigger_type": "low_occupancy_with_equipment", "description": "Review equipment.",
            "priority": "review",
        },
        {
            "action_id": "A6", "action_name": "Review feasible relocation",
            "trigger_type": "feasible_simulation_review", "description": "Review simulation.",
            "priority": "operational",
        },
    ]


class Member4Tests(unittest.TestCase):
    def test_data_generator_is_reproducible_and_counts_are_expected(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first_counts = generate_demo_data(first_dir, seed=57)
            second_counts = generate_demo_data(second_dir, seed=57)

            self.assertEqual(first_counts, second_counts)
            for filename in first_counts:
                self.assertEqual(
                    (Path(first_dir) / filename).read_bytes(),
                    (Path(second_dir) / filename).read_bytes(),
                )
            self.assertEqual(first_counts["buildings.csv"], 3)
            self.assertEqual(first_counts["rooms.csv"], 12)
            self.assertEqual(first_counts["timetable.csv"], 30)
            self.assertEqual(first_counts["equipment_inventory.csv"], 24)
            self.assertEqual(first_counts["energy_records.csv"], 12)
            self.assertEqual(first_counts["occupancy_observations.csv"], 12)
            self.assertEqual(first_counts["sustainability_actions.csv"], 7)

    def test_generated_data_is_labeled_and_relationally_consistent(self):
        buildings = read_csv(PROJECT_DIR / "data" / "buildings.csv")
        rooms = read_csv(PROJECT_DIR / "data" / "rooms.csv")
        timetable = read_csv(PROJECT_DIR / "data" / "timetable.csv")
        equipment = read_csv(PROJECT_DIR / "data" / "equipment_inventory.csv")
        energies = read_csv(PROJECT_DIR / "data" / "energy_records.csv")
        occupancy = read_csv(PROJECT_DIR / "data" / "occupancy_observations.csv")

        room_by_id = {row["room_id"]: row for row in rooms}
        self.assertEqual(len({row["building_id"] for row in buildings}), 3)
        self.assertTrue(all(row["building_id"] in {b["building_id"] for b in buildings} for row in rooms))
        self.assertTrue(all(row["room_id"] in room_by_id for row in timetable))
        self.assertTrue(all(row["data_label"] == "synthetic_demo_data" for row in occupancy))
        for row in equipment:
            self.assertEqual(
                int(row["quantity"]) * int(row["unit_power_watts"]),
                int(row["total_power_watts"]),
            )
        for row in energies:
            expected = round(float(row["estimated_energy_kwh_per_week"]) * float(row["electricity_tariff_inr_per_kwh"]), 2)
            self.assertEqual(float(row["estimated_cost_inr_per_week"]), expected)
        for observation in occupancy:
            self.assertLessEqual(
                int(observation["estimated_occupancy"]),
                int(room_by_id[observation["room_id"]]["capacity_students"]),
            )

    def test_occupancy_estimate_preserves_provenance_and_count(self):
        estimate = estimate_from_detection_count(
            "A101", 12, 40, "test_detector", detector_scores=[0.7, 0.9]
        )

        self.assertEqual(estimate["estimated_occupancy"], 12)
        self.assertEqual(estimate["occupancy_ratio"], 0.3)
        self.assertEqual(estimate["source"], "unknown")
        self.assertEqual(estimate["data_label"], "unknown")
        self.assertIsNone(estimate["confidence"])
        self.assertEqual(estimate["detector_scores"], [0.7, 0.9])
        self.assertIn("not calibrated confidence probabilities", estimate["score_note"])

    def test_occupancy_above_capacity_is_flagged_not_clipped(self):
        estimate = estimate_from_detection_count("A101", 42, 40, "test_detector")

        self.assertEqual(estimate["estimated_occupancy"], 42)
        self.assertEqual(estimate["status"], "over_capacity")
        self.assertGreater(estimate["occupancy_ratio"], 1)

    def test_manual_input_has_distinct_source_and_model(self):
        observation = estimate_from_manual_input(
            "A101", 7, 40, known_room_ids={"A101"}, observed_at="2026-10-16T10:00:00Z"
        )

        self.assertEqual(observation["source"], "manual_input")
        self.assertEqual(observation["data_label"], "manual_input")
        self.assertIsNone(observation["model"])
        self.assertIn("not verified by computer vision", observation["limitations"][0])

    def test_invalid_occupancy_inputs_are_rejected(self):
        with self.assertRaises(OccupancyInputError):
            estimate_from_detection_count("A101", -1, 40, "test_detector")
        with self.assertRaises(OccupancyInputError):
            estimate_from_detection_count("A101", 1, 0, "test_detector")

    @unittest.skipIf(cv2 is None, "optional OpenCV dependency is not installed")
    def test_image_inference_result_has_required_provenance_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "blank.png"
            self.assertTrue(cv2.imwrite(str(image_path), np.zeros((128, 64, 3), dtype=np.uint8)))
            estimate = estimate_from_image(
                image_path,
                "A101",
                40,
                known_room_ids={"A101", "A102"},
            )

        self.assertEqual(estimate["source"], "image_inference")
        self.assertEqual(estimate["data_label"], "image_inference")
        self.assertEqual(estimate["model"], "opencv_hog_default_people_detector")
        self.assertIsNotNone(estimate["observed_at"])
        self.assertTrue(estimate["limitations"])
        self.assertFalse(estimate["image_retained"])
        self.assertEqual(estimate["room_id_validation"], "verified")

    def test_missing_corrupt_unsupported_images_and_unknown_rooms_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing.png"
            corrupt = root / "corrupt.png"
            unsupported = root / "document.txt"
            corrupt.write_text("not an image", encoding="utf-8")
            unsupported.write_text("not an image", encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                estimate_from_image(missing, "A101", 40)
            with self.assertRaises(OccupancyInputError):
                estimate_from_image(unsupported, "A101", 40)
            with self.assertRaises(OccupancyInputError):
                estimate_from_image(missing, "Z999", 40, known_room_ids={"A101"})
            if cv2 is not None:
                with self.assertRaises(OccupancyInputError):
                    estimate_from_image(corrupt, "A101", 40)

    @unittest.skipIf(cv2 is None, "optional OpenCV dependency is not installed")
    def test_detector_failure_raises_instead_of_returning_estimate(self):
        with patch("cv2.HOGDescriptor", side_effect=RuntimeError("detector unavailable")):
            with self.assertRaisesRegex(RuntimeError, "HOG inference failed"):
                estimate_from_frame(np.zeros((128, 64, 3), dtype=np.uint8), "A101", 40)

    @unittest.skipIf(cv2 is None, "optional OpenCV dependency is not installed")
    def test_hog_inference_runs_on_a_temporary_image(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "blank.png"
            self.assertTrue(cv2.imwrite(str(image_path), np.zeros((128, 64, 3), dtype=np.uint8)))
            estimate = estimate_from_image(image_path, "A101", 40)

        self.assertEqual(estimate["estimated_occupancy"], 0)
        self.assertEqual(estimate["data_label"], "image_inference")
        self.assertFalse(estimate["image_retained"])

    def test_recommendations_are_deterministic_ranked_and_cautious(self):
        rooms = [
            {
                "room_id": "A101", "capacity_students": "40",
                "estimated_connected_load_kw": "1.20", "data_label": "synthetic_demo_data",
            }
        ]
        observations = [
            {
                "room_id": "A101", "estimated_occupancy": "5",
                "observation_timestamp": "2026-10-15T10:30:00+05:30",
                "source": "synthetic_data_generator", "data_label": "synthetic_demo_data",
            }
        ]
        energy = [{"room_id": "A101", "data_label": "synthetic_demo_data"}]
        now = datetime.fromisoformat("2026-10-15T11:00:00+05:30")
        equipment = [{"room_id": "A101", "equipment_type": "lights", "assumed_daily_hours": 6}]
        first = build_recommendations(
            rooms, observations, energy, action_fixtures(), equipment_inventory=equipment, now=now
        )
        second = build_recommendations(
            rooms, observations, energy, action_fixtures(), equipment_inventory=equipment, now=now
        )

        self.assertEqual(first, second)
        self.assertEqual(
            [row["priority_rank"] for row in first["recommendations"]],
            list(range(1, len(first["recommendations"]) + 1)),
        )
        self.assertTrue(any("repeated observations" in row["required_follow_up"] for row in first["recommendations"]))
        self.assertTrue(any("approved tariff" in row["required_follow_up"] for row in first["recommendations"]))
        self.assertTrue(any(row["recommendation_id"] == "REC-EQUIPMENT-A101" for row in first["recommendations"]))
        self.assertTrue(any("synthetic" in warning for warning in first["warnings"]))
        json.dumps(first)

    def test_missing_and_stale_occupancy_are_flagged(self):
        rooms = [
            {"room_id": "A101", "building_id": "BLK-A", "capacity_students": 40, "estimated_connected_load_kw": 0.2},
            {"room_id": "A102", "building_id": "BLK-A", "capacity_students": 35, "estimated_connected_load_kw": 0.2},
        ]
        stale = {
            "room_id": "A101", "estimated_occupancy": 0,
            "observation_timestamp": "2026-10-13T08:00:00+00:00",
            "source": "image_inference", "data_label": "image_inference",
        }
        result = build_recommendations(
            rooms,
            [stale],
            [],
            action_fixtures(),
            now=datetime.fromisoformat("2026-10-15T08:00:00+00:00"),
        )

        recommendation_ids = {item["recommendation_id"] for item in result["recommendations"]}
        self.assertIn("REC-STALE-A101", recommendation_ids)
        self.assertIn("REC-MISSING-A102", recommendation_ids)
        self.assertNotIn("REC-LOW-A101", recommendation_ids)

    def test_timetable_context_prevents_unused_room_claim(self):
        room = {"room_id": "A101", "building_id": "BLK-A", "capacity_students": 40, "estimated_connected_load_kw": 0.2}
        observation = {
            "room_id": "A101", "estimated_occupancy": 2,
            "observation_timestamp": "2026-10-15T10:30:00+05:30",
            "source": "image_inference", "data_label": "image_inference",
        }
        timetable = [{
            "timetable_entry_id": "T1", "room_id": "A101", "day_of_week": "Thursday",
            "start_time": "10:15", "end_time": "11:15", "subject_name": "Math",
            "expected_students": 25,
        }]
        result = build_recommendations(
            [room], [observation], [], action_fixtures(), timetable=timetable,
            now=datetime.fromisoformat("2026-10-15T10:31:00+05:30"),
        )
        underuse = next(item for item in result["recommendations"] if item["recommendation_id"] == "REC-LOW-A101")

        self.assertEqual(underuse["building_id"], "BLK-A")
        self.assertEqual(underuse["evidence"]["scheduled_entries_at_observation_time"][0]["timetable_entry_id"], "T1")
        self.assertIn("scheduled in this room", underuse["reason"])
        self.assertIn("not evidence that the room is unused", underuse["operational_constraints"])

    def test_feasible_simulation_impacts_are_passed_through_unchanged(self):
        energy_impact = {"status": "available", "savings_kwh": -0.5}
        result = build_recommendations(
            [{"room_id": "B101", "building_id": "BLK-B", "capacity_students": 40, "estimated_connected_load_kw": 0.2}],
            [], [], action_fixtures(),
            simulation_results={
                "simulation_id": "SIM-1", "status": "feasible", "validation_errors": [],
                "baseline": {"room_id": "A101"}, "proposed": {"room_id": "B101"},
                "energy_impact": energy_impact,
                "cost_impact": {"status": "unavailable"},
                "walking_impact": {"status": "unavailable"},
            },
        )
        recommendation = next(
            item for item in result["recommendations"] if item.get("simulation_id") == "SIM-1"
        )

        self.assertEqual(recommendation["energy_impact"], energy_impact)
        self.assertEqual(recommendation["building_id"], "BLK-B")
        self.assertEqual(recommendation["data_source"], "Member 3 simulator result")

    def test_incomplete_or_infeasible_simulations_do_not_generate_recommendations(self):
        results = [
            {"simulation_id": "SIM-BAD", "status": "feasible", "validation_errors": []},
            {
                "simulation_id": "SIM-REJECTED", "status": "infeasible", "validation_errors": ["conflict"],
                "baseline": {"room_id": "A101"}, "proposed": {"room_id": "B101"},
            },
        ]
        result = build_recommendations(
            [{"room_id": "B101", "building_id": "BLK-B", "capacity_students": 40, "estimated_connected_load_kw": 0.2}],
            [], [], action_fixtures(), simulation_results=results,
        )

        self.assertFalse(any(item.get("simulation_id") for item in result["recommendations"]))
        self.assertTrue(any("missing baseline/proposed room IDs" in warning for warning in result["warnings"]))

    def test_generated_data_simulator_recommendation_explanation_contract(self):
        rooms_csv = read_csv(PROJECT_DIR / "data" / "rooms.csv")
        timetable_csv = read_csv(PROJECT_DIR / "data" / "timetable.csv")
        equipment_csv = read_csv(PROJECT_DIR / "data" / "equipment_inventory.csv")
        energy_csv = read_csv(PROJECT_DIR / "data" / "energy_records.csv")
        scenario = next(
            row for row in read_csv(PROJECT_DIR / "data" / "simulation_scenarios.csv")
            if row["scenario_type"] == "valid_reassignment"
        )
        campus_data = CampusData(
            rooms=tuple(
                Room(
                    row["room_id"],
                    int(row["capacity_students"]),
                    row["timetable_eligible"].casefold() == "true",
                )
                for row in rooms_csv
            ),
            timetable=tuple(
                TimetableEntry(
                    row["timetable_entry_id"], row["room_id"], row["day_of_week"],
                    row["start_time"], row["end_time"], row["semester"], row["section"],
                    row["department"], row["faculty_id"], row["subject_name"],
                    int(row["expected_students"]),
                )
                for row in timetable_csv
            ),
            equipment=tuple(
                EquipmentRecord(
                    row["room_id"], float(row["quantity"]), float(row["unit_power_watts"]),
                    float(row["total_power_watts"]), float(row["assumed_daily_hours"]),
                )
                for row in equipment_csv
            ),
            energy_records=tuple(
                EnergyRecord(row["room_id"], float(row["electricity_tariff_inr_per_kwh"]))
                for row in energy_csv
            ),
            data_classification="synthetic_demo_data",
        )
        simulation = simulate_reassignment(
            campus_data,
            SimulationRequest(
                scenario["timetable_entry_id"], scenario["proposed_room_id"],
                int(scenario["class_size"]),
            ),
        )
        self.assertEqual(simulation["status"], "feasible")
        recommendation_result = build_recommendations(
            rooms_csv,
            read_csv(PROJECT_DIR / "data" / "occupancy_observations.csv"),
            energy_csv,
            read_csv(PROJECT_DIR / "data" / "sustainability_actions.csv"),
            timetable=timetable_csv,
            equipment_inventory=equipment_csv,
            simulation_results=simulation,
            now=datetime.fromisoformat("2026-10-15T10:30:00+05:30"),
        )
        simulation_recommendation = next(
            item for item in recommendation_result["recommendations"]
            if item["data_source"] == "Member 3 simulator result"
        )
        explanation = build_simulation_explanation(simulation)

        self.assertEqual(simulation_recommendation["energy_impact"], simulation["energy_impact"])
        self.assertEqual(explanation["mode"], "deterministic_fallback")
        self.assertIn(simulation["baseline"]["room_id"], explanation["text"])
        self.assertIn(simulation["proposed"]["room_id"], explanation["text"])

    def test_thresholds_must_be_valid(self):
        with self.assertRaises(ValueError):
            build_recommendations([], [], [], [], low_occupancy_threshold=1.1)
        with self.assertRaises(ValueError):
            build_recommendations([], [], [], [], high_connected_load_kw=-0.1)

    def test_explanations_only_use_supplied_results(self):
        occupancy = estimate_from_detection_count("A101", 5, 40, "test_detector")
        recommendation = {
            "action_name": "Review schedule",
            "reason": "Observed count is low.",
            "required_follow_up": "Verify repeated observations.",
            "data_label": "synthetic_demo_data",
        }
        simulation = {
            "status": "feasible",
            "data_classification": "synthetic_or_illustrative",
            "energy_impact": {"status": "available", "savings_kwh": -1.0},
            "cost_impact": {"status": "unavailable"},
            "walking_impact": {"status": "unavailable"},
        }

        self.assertIn("5 people", explain_occupancy(occupancy))
        self.assertIn("synthetic_demo_data", explain_recommendation(recommendation))
        simulation["baseline"] = {
            "room_id": "A101", "timetable_entry_id": "T1", "subject_name": "Math"
        }
        simulation["proposed"] = {"room_id": "B101"}
        simulation["energy_impact"].update({"baseline_kwh": 1.0, "proposed_kwh": 2.0})
        explanation = build_simulation_explanation(simulation)
        self.assertEqual(explanation["mode"], "deterministic_fallback")
        self.assertIn("baseline 1.0 kWh; proposed 2.0 kWh", explanation["text"])
        self.assertIn("-1.0 kWh (an increase)", explanation["text"])
        self.assertIn("deterministic_fallback", explain_simulation(simulation))
        self.assertIn("unavailable from the simulator result", explain_simulation(simulation))


if __name__ == "__main__":
    unittest.main()