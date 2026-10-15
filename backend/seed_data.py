import argparse
import json
import sys
from pathlib import Path

from backend.database import SessionLocal, initialize_database
from backend.services.data_importer import DatasetImportError, import_datasets


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Import canonical EcoTwin AI CSV datasets.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=project_root / "data" / "raw" / "ecotwin_dataset",
        help="Directory containing the required canonical CSV files.",
    )
    args = parser.parse_args()

    try:
        initialize_database()
        with SessionLocal() as session:
            report = import_datasets(args.data_dir, session)
    except DatasetImportError as exc:
        print(f"Dataset import failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report.to_dict(), indent=2))
    return 1 if report.rejected_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
