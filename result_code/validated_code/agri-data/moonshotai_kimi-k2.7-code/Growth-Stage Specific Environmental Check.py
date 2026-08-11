"""
Task: Growth-Stage Specific Environmental Check
Description: Validate that Temperature, Humidity, Soil_Moisture, and Sunlight_Exposure fall within recommended ranges for the current Growth_Stage, highlighting conditions that may hinder development.
"""

# Programmatic path resolution pre-injected for reliability
import os
from pathlib import Path

_curr_dir = Path(__file__).resolve().parent
_root_dir = _curr_dir
while _root_dir.name and not (_root_dir / "data").exists():
    _parent = _root_dir.parent
    if _parent == _root_dir:
        break
    _root_dir = _parent

DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "agri-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Recommended environmental ranges per growth stage
GROWTH_RANGES = {
    1: {  # Seedling
        "temperature": (18.0, 28.0),
        "humidity": (60.0, 80.0),
        "soil_moisture": (40.0, 60.0),
        "sunlight_exposure": (6.0, 10.0),
    },
    2: {  # Vegetative
        "temperature": (20.0, 30.0),
        "humidity": (50.0, 80.0),
        "soil_moisture": (50.0, 70.0),
        "sunlight_exposure": (8.0, 12.0),
    },
    3: {  # Flowering
        "temperature": (22.0, 32.0),
        "humidity": (40.0, 70.0),
        "soil_moisture": (45.0, 65.0),
        "sunlight_exposure": (10.0, 14.0),
    },
}

STAGE_NAMES = {1: "Seedling", 2: "Vegetative", 3: "Flowering"}
CHECK_FIELDS = ["temperature", "humidity", "soil_moisture", "sunlight_exposure"]
MISSING_MARKERS = {"", "NA", "N/A", "None", "None"}


def resolve_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for fname in ["raw_data.csv", "raw_data.txt"]:
        candidate = root_dir / "data" / "agri-data" / fname
        if candidate.exists():
            return candidate
    return None


def to_float(val, col):
    if val is None:
        return None
    s = str(val).strip()
    if s in MISSING_MARKERS:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value for '{col}': {val!r}", file=sys.stderr)
        return None


def to_int(val, col):
    f = to_float(val, col)
    return None if f is None else int(f)


def main():
    parser = argparse.ArgumentParser(description="Growth-stage specific environmental check")
    parser.add_argument("--strict", action="store_true",
                        help="Skip rows missing any required field")
    args = parser.parse_args()

    data_file = resolve_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/agri-data/",
              file=sys.stderr)
        sys.exit(1)

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "growth_stage_environmental_check_result.json"

    required = CHECK_FIELDS + ["growth_stage"]
    rows_total = 0
    rows_dropped = 0
    flags = []
    stage_counts = {name: 0 for name in STAGE_NAMES.values()}

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            rows_total += 1
            row = {k.lower().strip(): v for k, v in row.items()}

            stage_raw = row.get("growth_stage")
            stage = to_int(stage_raw, "growth_stage")
            if stage is None or stage not in GROWTH_RANGES:
                rows_dropped += 1
                print(f"Warning row {idx}: missing/unknown growth stage ({stage_raw!r}); skipped")
                continue

            stage_name = STAGE_NAMES.get(stage, str(stage))
            stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
            ranges = GROWTH_RANGES[stage]

            missing_required = [
                c for c in required
                if row.get(c) is None or str(row.get(c)).strip() in MISSING_MARKERS
            ]
            if args.strict and missing_required:
                rows_dropped += 1
                print(f"Warning row {idx}: strict mode skipping due to missing fields {missing_required}")
                continue

            row_flags = []
            for field in CHECK_FIELDS:
                val = to_float(row.get(field), field)
                if val is None:
                    row_flags.append({
                        "field": field,
                        "value": None,
                        "status": "missing",
                        "recommended": None,
                    })
                    continue
                lo, hi = ranges[field]
                if val < lo:
                    status = "below"
                elif val > hi:
                    status = "above"
                else:
                    status = "ok"
                if status != "ok":
                    row_flags.append({
                        "field": field,
                        "value": val,
                        "status": status,
                        "recommended": f"{lo}-{hi}",
                    })

            if row_flags:
                flags.append({
                    "row": idx,
                    "growth_stage": stage_name,
                    "flags": row_flags,
                })

    summary = {
        "total_rows": rows_total,
        "valid_rows": rows_total - rows_dropped,
        "dropped_rows": rows_dropped,
        "stage_distribution": stage_counts,
        "flagged_rows": len(flags),
        "flags": flags[:200],
    }

    result = {
        "task_name": "Growth-Stage Specific Environmental Check",
        "description": "Validate that Temperature, Humidity, Soil_Moisture, and Sunlight_Exposure fall within recommended ranges for the current Growth_Stage, highlighting conditions that may hinder development.",
        "result_summary": [summary],
        "result_generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Result saved to {out_file}")
    print(f"Rows: {rows_total}, dropped: {rows_dropped}, flagged: {len(flags)}")


if __name__ == "__main__":
    main()