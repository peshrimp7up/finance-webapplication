"""변경 이력을 CSV 파일에 append 한다."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "audit_log.csv"
FIELDS = ["timestamp", "dept", "sheet", "category_id", "category_name", "year", "before", "after"]


def _ensure_file() -> None:
    if not LOG_PATH.exists():
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()


def log_change(dept: str, sheet: str, category_id: str, category_name: str,
               year: str, before, after) -> None:
    _ensure_file()
    with LOG_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writerow({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dept": dept,
            "sheet": sheet,
            "category_id": category_id,
            "category_name": category_name,
            "year": year,
            "before": "" if before is None else str(before),
            "after": "" if after is None else str(after),
        })


def read_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def clear_log() -> None:
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    _ensure_file()
