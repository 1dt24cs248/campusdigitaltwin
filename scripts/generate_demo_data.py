"""Generate reproducible, internally consistent fictional EcoTwin campus CSVs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import random
from typing import Any


DEFAULT_SEED = 20261015
DEFAULT_TARIFF = 8.50
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
TIME_SLOTS = (("09:00", "10:00"), ("10:15", "11:15"), ("13:00", "14:00"))

CSV_FIELDS: dict[str, tuple[str, ...]] = {
    "buildings.csv": (
        "building_id", "building_name", "number_of_floors",
        "fictional_location_description", "data_label",
    ),
    "rooms.csv": (
        "room_id", "building_id", "floor", "room_name", "room_type",
        "capacity_students", "timetable_eligible", "estimated_connected_load_kw",
        "data_label",
    ),
    "timetable.csv": (
        "timetable_entry_id", "semester", "section", "department", "day_of_week",
        "start_time", "end_time", "subject_code", "subject_name", "room_id",
        "faculty_id", "expected_students", "data_label",
    ),
    "equipment_inventory.csv": (
        "equipment_id", "room_id", "equipment_type", "quantity",
        "unit_power_watts", "total_power_watts", "assumed_daily_hours", "data_label",
    ),
    "energy_records.csv": (
        "energy_record_id", "room_id", "estimated_energy_kwh_per_day",
        "estimated_energy_kwh_per_week", "electricity_tariff_inr_per_kwh",
        "estimated_cost_inr_per_week", "data_source", "data_label",
    ),
    "occupancy_observations.csv": (
        "observation_id", "room_id", "observation_timestamp", "estimated_occupancy",
        "source", "status", "confidence", "data_label",
    ),
    "simulation_scenarios.csv": (
        "scenario_id", "scenario_type", "timetable_entry_id", "proposed_room_id",
        "class_size", "expected_status", "description", "data_label",
    ),
    "sustainability_actions.csv": (
        "action_id", "action_name", "trigger_type", "description", "priority",
        "data_label",
    ),
}


def _make_dataset(seed: int, tariff: float) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)
    label = "synthetic_demo_data"
    buildings = [
        {
            "building_id": f"BLK-{letter}",
            "building_name": f"Block {letter}",
            "number_of_floors": rng.randint(2, 4),
            "fictional_location_description": description,
            "data_label": label,
        }
        for letter, description in (
            ("A", "Fictional north campus courtyard"),
            ("B", "Fictional central learning walk"),
            ("C", "Fictional south garden edge"),
        )
    ]

    rooms: list[dict[str, Any]] = []
    equipment: list[dict[str, Any]] = []
    equipment_types = (
        ("lights", 20, 4, 10),
        ("projector", 250, 1, 1),
        ("computers", 150, 2, 6),
    )
    room_ids = [f"{block}{number:02d}" for block in "ABC" for number in range(101, 105)]
    for index, room_id in enumerate(room_ids):
        block = room_id[0]
        floor = rng.randint(1, buildings[ord(block) - ord("A")]["number_of_floors"])
        capacity = rng.randint(24, 60)
        room_type = "computer_lab" if index % 4 == 2 else "classroom"
        eligible = room_id != "C104"
        fans_quantity = rng.randint(2, 5)
        equipment.append(
            {
                "equipment_id": f"EQ-{len(equipment) + 1:03d}",
                "room_id": room_id,
                "equipment_type": "fans",
                "quantity": fans_quantity,
                "unit_power_watts": 70,
                "total_power_watts": fans_quantity * 70,
                "assumed_daily_hours": rng.randint(5, 9),
                "data_label": label,
            }
        )
        equipment_type, unit_watts, min_quantity, max_quantity = equipment_types[index % len(equipment_types)]
        quantity = rng.randint(min_quantity, max_quantity)
        equipment.append(
            {
                "equipment_id": f"EQ-{len(equipment) + 1:03d}",
                "room_id": room_id,
                "equipment_type": equipment_type,
                "quantity": quantity,
                "unit_power_watts": unit_watts,
                "total_power_watts": quantity * unit_watts,
                "assumed_daily_hours": rng.randint(4, 9),
                "data_label": label,
            }
        )
        connected_watts = sum(
            row["total_power_watts"] for row in equipment if row["room_id"] == room_id
        )
        rooms.append(
            {
                "room_id": room_id,
                "building_id": f"BLK-{block}",
                "floor": floor,
                "room_name": f"{block} Block Room {room_id[1:]}",
                "room_type": room_type,
                "capacity_students": capacity,
                "timetable_eligible": str(eligible).lower(),
                "estimated_connected_load_kw": round(connected_watts / 1000, 3),
                "data_label": label,
            }
        )

    eligible_rooms = [row for row in rooms if row["timetable_eligible"] == "true"]
    timetable: list[dict[str, Any]] = []
    peer_by_entry: dict[str, dict[str, Any]] = {}
    subjects = (
        ("CS201", "Data Structures", "Computer Science"),
        ("EE204", "Circuit Analysis", "Electrical Engineering"),
        ("ME110", "Engineering Design", "Mechanical Engineering"),
        ("MA130", "Applied Mathematics", "Mathematics"),
        ("PH120", "Physics Lab", "Physics"),
        ("CE220", "Sustainable Systems", "Civil Engineering"),
    )
    entry_number = 0
    for day in WEEKDAYS:
        for start, end in TIME_SLOTS:
            assigned_rooms = rng.sample(eligible_rooms, 2)
            slot_entries = []
            for room in assigned_rooms:
                entry_number += 1
                subject_code, subject_name, department = rng.choice(subjects)
                expected_students = rng.randint(18, min(int(room["capacity_students"]), 42))
                entry = {
                    "timetable_entry_id": f"TT-{entry_number:03d}",
                    "semester": "2026-Fall",
                    "section": f"SEC-{entry_number:03d}",
                    "department": department,
                    "day_of_week": day,
                    "start_time": start,
                    "end_time": end,
                    "subject_code": subject_code,
                    "subject_name": subject_name,
                    "room_id": room["room_id"],
                    "faculty_id": f"FAC-{entry_number:03d}",
                    "expected_students": expected_students,
                    "data_label": label,
                }
                timetable.append(entry)
                slot_entries.append(entry)
            peer_by_entry[slot_entries[0]["timetable_entry_id"]] = slot_entries[1]

    energy_records = []
    for room in rooms:
        room_equipment = [row for row in equipment if row["room_id"] == room["room_id"]]
        daily_kwh = sum(
            row["total_power_watts"] / 1000 * row["assumed_daily_hours"]
            for row in room_equipment
        )
        weekly_kwh = round(daily_kwh * 5, 3)
        energy_records.append(
            {
                "energy_record_id": f"EN-{len(energy_records) + 1:03d}",
                "room_id": room["room_id"],
                "estimated_energy_kwh_per_day": round(daily_kwh, 3),
                "estimated_energy_kwh_per_week": weekly_kwh,
                "electricity_tariff_inr_per_kwh": f"{tariff:.2f}",
                "estimated_cost_inr_per_week": round(weekly_kwh * tariff, 2),
                "data_source": "synthetic_equipment_power_and_runtime_assumptions",
                "data_label": label,
            }
        )

    occupancy = []
    for index, room in enumerate(rooms, start=1):
        occupancy.append(
            {
                "observation_id": f"OBS-{index:03d}",
                "room_id": room["room_id"],
                "observation_timestamp": "2026-10-15T10:30:00+05:30",
                "estimated_occupancy": rng.randint(0, int(room["capacity_students"])),
                "source": "synthetic_data_generator",
                "status": "synthetic_demo_data",
                "confidence": "",
                "data_label": label,
            }
        )

    target = timetable[0]
    peer = peer_by_entry[target["timetable_entry_id"]]
    open_room = next(
        room
        for room in eligible_rooms
        if room["room_id"] not in {target["room_id"], peer["room_id"]}
        and int(room["capacity_students"]) >= int(target["expected_students"])
    )
    capacity_test_room = min(
        (room for room in eligible_rooms if room["room_id"] != target["room_id"]),
        key=lambda room: int(room["capacity_students"]),
    )
    ineligible_room = next(room for room in rooms if room["timetable_eligible"] == "false")
    scenarios = [
        {
            "scenario_id": "SCN-VALID",
            "scenario_type": "valid_reassignment",
            "timetable_entry_id": target["timetable_entry_id"],
            "proposed_room_id": open_room["room_id"],
            "class_size": target["expected_students"],
            "expected_status": "feasible",
            "description": "Open eligible room with sufficient capacity and no slot conflict.",
            "data_label": label,
        },
        {
            "scenario_id": "SCN-ROOM-CONFLICT",
            "scenario_type": "room_timetable_conflict",
            "timetable_entry_id": target["timetable_entry_id"],
            "proposed_room_id": peer["room_id"],
            "class_size": target["expected_students"],
            "expected_status": "infeasible",
            "description": "Destination is occupied by another entry in the same time slot.",
            "data_label": label,
        },
        {
            "scenario_id": "SCN-CAPACITY",
            "scenario_type": "capacity_exceeded",
            "timetable_entry_id": target["timetable_entry_id"],
            "proposed_room_id": capacity_test_room["room_id"],
            "class_size": int(capacity_test_room["capacity_students"]) + 1,
            "expected_status": "infeasible",
            "description": "Test input exceeds the destination room's stated capacity.",
            "data_label": label,
        },
        {
            "scenario_id": "SCN-INELIGIBLE",
            "scenario_type": "room_not_timetable_eligible",
            "timetable_entry_id": target["timetable_entry_id"],
            "proposed_room_id": ineligible_room["room_id"],
            "class_size": min(int(target["expected_students"]), int(ineligible_room["capacity_students"])),
            "expected_status": "infeasible",
            "description": "Destination is explicitly marked as not timetable-eligible.",
            "data_label": label,
        },
    ]

    actions = [
        {
            "action_id": "ACT-001", "action_name": "Review low-occupancy room schedules",
            "trigger_type": "low_observed_occupancy", "description": "Compare repeated observations with scheduled class sizes before consolidating room use.",
            "priority": "review", "data_label": label,
        },
        {
            "action_id": "ACT-002", "action_name": "Inspect high connected-load rooms",
            "trigger_type": "high_connected_load", "description": "Review equipment runtime assumptions and avoid switching equipment off without authorization.",
            "priority": "review", "data_label": label,
        },
        {
            "action_id": "ACT-003", "action_name": "Verify electricity tariff",
            "trigger_type": "unverified_tariff", "description": "Replace the illustrative tariff with an approved campus tariff before cost decisions.",
            "priority": "data_quality", "data_label": label,
        },
        {
            "action_id": "ACT-004", "action_name": "Check room eligibility and capacity",
            "trigger_type": "allocation_validation", "description": "Confirm room-use policy and expected class size before changing a timetable.",
            "priority": "operational", "data_label": label,
        },
        {
            "action_id": "ACT-005", "action_name": "Refresh occupancy observation",
            "trigger_type": "missing_or_stale_occupancy", "description": "Collect a timestamped occupancy observation and compare it with the room timetable.",
            "priority": "data_quality", "data_label": label,
        },
        {
            "action_id": "ACT-006", "action_name": "Review equipment runtime assumptions",
            "trigger_type": "low_occupancy_with_equipment", "description": "Verify room schedule and equipment controls when an occupancy observation and inventory are both available.",
            "priority": "review", "data_label": label,
        },
        {
            "action_id": "ACT-007", "action_name": "Review feasible room relocation",
            "trigger_type": "feasible_simulation_review", "description": "Review a feasible simulator result and its assumptions before an operator changes a timetable.",
            "priority": "operational", "data_label": label,
        },
    ]

    return {
        "buildings.csv": buildings,
        "rooms.csv": rooms,
        "timetable.csv": timetable,
        "equipment_inventory.csv": equipment,
        "energy_records.csv": energy_records,
        "occupancy_observations.csv": occupancy,
        "simulation_scenarios.csv": scenarios,
        "sustainability_actions.csv": actions,
    }


def validate_datasets(datasets: dict[str, list[dict[str, Any]]]) -> None:
    buildings = datasets["buildings.csv"]
    rooms = datasets["rooms.csv"]
    timetable = datasets["timetable.csv"]
    equipment = datasets["equipment_inventory.csv"]
    energies = datasets["energy_records.csv"]
    occupancy = datasets["occupancy_observations.csv"]
    building_ids = {row["building_id"] for row in buildings}
    room_by_id = {row["room_id"]: row for row in rooms}
    if len(building_ids) != 3 or len(room_by_id) != 12:
        raise ValueError("Expected exactly three buildings and twelve unique rooms.")
    if any(room["building_id"] not in building_ids for room in rooms):
        raise ValueError("A room references a missing building.")
    if len(timetable) != 30 or len(equipment) != 24 or len(energies) != 12:
        raise ValueError("Unexpected demo record count.")
    if len({row["timetable_entry_id"] for row in timetable}) != len(timetable):
        raise ValueError("Timetable entry IDs must be unique.")
    for row in timetable:
        room = room_by_id.get(row["room_id"])
        if room is None or room["timetable_eligible"] != "true":
            raise ValueError(f"Timetable entry {row['timetable_entry_id']} uses an invalid room.")
        if int(row["expected_students"]) > int(room["capacity_students"]):
            raise ValueError(f"Timetable entry {row['timetable_entry_id']} exceeds room capacity.")
    for index, left in enumerate(timetable):
        for right in timetable[index + 1 :]:
            same_day = left["day_of_week"] == right["day_of_week"]
            same_semester = left["semester"] == right["semester"]
            overlaps = left["start_time"] < right["end_time"] and left["end_time"] > right["start_time"]
            if same_day and same_semester and overlaps:
                if left["room_id"] == right["room_id"]:
                    raise ValueError("Normal timetable has a room-time conflict.")
                if left["faculty_id"] == right["faculty_id"] or left["section"] == right["section"]:
                    raise ValueError("Normal timetable has a faculty or section conflict.")
    equipment_room_ids = set()
    for row in equipment:
        equipment_room_ids.add(row["room_id"])
        if int(row["quantity"]) * int(row["unit_power_watts"]) != int(row["total_power_watts"]):
            raise ValueError(f"Equipment total power is inconsistent for {row['equipment_id']}.")
    for room in rooms:
        watts = sum(int(row["total_power_watts"]) for row in equipment if row["room_id"] == room["room_id"])
        if round(watts / 1000, 3) != float(room["estimated_connected_load_kw"]):
            raise ValueError(f"Connected load does not match equipment for {room['room_id']}.")
    if equipment_room_ids != set(room_by_id):
        raise ValueError("Every room must have equipment inventory.")
    for energy in energies:
        expected_cost = round(
            float(energy["estimated_energy_kwh_per_week"])
            * float(energy["electricity_tariff_inr_per_kwh"]),
            2,
        )
        if expected_cost != float(energy["estimated_cost_inr_per_week"]):
            raise ValueError(f"Weekly energy cost is inconsistent for {energy['room_id']}.")
    if {row["room_id"] for row in occupancy} != set(room_by_id):
        raise ValueError("There must be one occupancy observation for every room.")
    for observation in occupancy:
        if int(observation["estimated_occupancy"]) > int(room_by_id[observation["room_id"]]["capacity_students"]):
            raise ValueError(f"Occupancy exceeds capacity for {observation['room_id']}.")
        if observation["data_label"] != "synthetic_demo_data":
            raise ValueError("Generated occupancy must be labeled synthetic_demo_data.")
    timetable_ids = {row["timetable_entry_id"] for row in timetable}
    for scenario in datasets["simulation_scenarios.csv"]:
        if scenario["timetable_entry_id"] not in timetable_ids:
            raise ValueError("A scenario references a missing timetable entry.")
        if scenario["proposed_room_id"] not in room_by_id:
            raise ValueError("A scenario references a missing room.")


def generate_demo_data(
    output_dir: Path | str,
    seed: int = DEFAULT_SEED,
    tariff: float = DEFAULT_TARIFF,
) -> dict[str, int]:
    if tariff < 0:
        raise ValueError("tariff must not be negative")
    datasets = _make_dataset(seed, tariff)
    validate_datasets(datasets)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for filename, rows in datasets.items():
        with (output_path / filename).open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS[filename])
            writer.writeheader()
            writer.writerows(rows)
    return {filename: len(rows) for filename, rows in datasets.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="directory for generated CSVs (default: project data/)",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--tariff", type=float, default=DEFAULT_TARIFF)
    args = parser.parse_args()
    counts = generate_demo_data(args.output_dir, args.seed, args.tariff)
    for filename, count in counts.items():
        print(f"{filename}: {count} rows")
    print(f"Generated synthetic demo data at {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()