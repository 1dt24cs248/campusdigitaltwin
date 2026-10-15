import csv
from pathlib import Path

import pytest

from backend.models import Building, Room, TimetableEntry
from backend.services.data_importer import DatasetImportError, import_datasets


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "ecotwin_dataset"


def test_canonical_datasets_import_and_repeat_without_duplicates(db_session):
    first = import_datasets(DATA_DIR, db_session)
    second = import_datasets(DATA_DIR, db_session)

    assert first.rejected_rows == 0
    assert sum(result.inserted for result in first.datasets.values()) == 2 + 128 + 480 + 260 + 128 + 59 + 276 + 4
    assert all(result.skipped == result.source_rows for result in second.datasets.values())
    assert db_session.query(Building).count() == 2
    assert db_session.query(Room).count() == 128
    assert db_session.query(TimetableEntry).count() == 480


def test_importer_rejects_missing_required_column(db_session, tmp_path):
    source = DATA_DIR
    for path in source.glob("*.csv"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    with (tmp_path / "rooms.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["room_id", "building_id"])

    with pytest.raises(DatasetImportError, match="missing required columns"):
        import_datasets(tmp_path, db_session)


def test_importer_rejects_unknown_room_foreign_key(db_session, tmp_path):
    for path in DATA_DIR.glob("*.csv"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    timetable_path = tmp_path / "timetable.csv"
    with timetable_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
        headers = list(rows[0])
    rows[0]["room_id"] = "UNKNOWN"
    with timetable_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    report = import_datasets(tmp_path, db_session)

    assert report.datasets["timetable.csv"].rejected == 1
    assert report.issues[0].file == "timetable.csv"
    assert "unknown room_id UNKNOWN" in report.issues[0].message
    assert db_session.query(TimetableEntry).count() == 479
