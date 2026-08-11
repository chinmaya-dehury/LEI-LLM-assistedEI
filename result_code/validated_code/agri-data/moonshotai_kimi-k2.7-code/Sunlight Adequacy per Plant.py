"""
Task: Sunlight Adequacy per Plant
Description: Evaluate whether the average daily Sunlight_Exposure divided by Crop_Density meets a minimum per-plant light requirement for the current growth stage.
"""

# Programmatic path resolution pre-injected for reliability
import os
import sys
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Minimum per-plant sunlight requirement (hours/day per plant) by growth stage
STAGE_THRESHOLDS = {
    "Seedling": 0.3,
    "Vegetative": 0.5,
    "Flowering": 0.7,
}

STAGE_MAP = {
    "1": "Seedling",
    "2": "Vegetative",
    "3": "Flowering",
}

REQUIRED_COLS = {"sunlight_exposure", "crop_density", "growth_stage"}


def find_data_file():
    """Locate raw_data.csv or raw_data.txt under the project root."""
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    for name in ["raw_data.csv", "raw_data.txt"]:
        candidate = root_dir / "data" / "agri-data" / name
        if candidate.exists():
            return candidate
    return None


def safe_float(value, column):
    """Convert a value to float, treating missing/invalid placeholders as None."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.upper() in ("NA", "N/A", "NULL"):
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{column}': {value}", file=sys.stderr)
        return None


def normalize_stage(stage):
    """Map numeric or string growth stage to a canonical name."""
    stage = (stage or "").strip()
    if stage in STAGE_MAP:
        return STAGE_MAP[stage]
    return stage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Skip rows with missing required fields")
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/agri-data/", file=sys.stderr)
        sys.exit(1)

    records = []
    dropped = 0
    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=2):
            # Normalize column names to lowercase
            row = {k.lower(): v for k, v in row.items()}

            if not REQUIRED_COLS.issubset(row.keys()):
                print("Error: required columns missing from dataset", file=sys.stderr)
                sys.exit(1)

            sunlight = safe_float(row.get("sunlight_exposure"), "sunlight_exposure")
            density = safe_float(row.get("crop_density"), "crop_density")
            stage = normalize_stage(row.get("growth_stage"))

            if sunlight is None or density is None or density <= 0 or not stage:
                dropped += 1
                if args.strict:
                    continue
                # Non-strict: still skip uncomputable rows
                continue

            per_plant = sunlight / density
            threshold = STAGE_THRESHOLDS.get(stage, 0.5)
            adequate = per_plant >= threshold

            records.append({
                "row": row_idx,
                "growth_stage": stage,
                "sunlight_per_plant": round(per_plant, 4),
                "threshold": threshold,
                "adequate": adequate,
            })

    # Summarize by growth stage
    summary = {}
    for rec in records:
        stage = rec["growth_stage"]
        if stage not in summary:
            summary[stage] = {
                "count": 0,
                "adequate": 0,
                "inadequate": 0,
                "avg_sunlight_per_plant": 0.0,
            }
        s = summary[stage]
        s["count"] += 1
        if rec["adequate"]:
            s["adequate"] += 1
        else:
            s["inadequate"] += 1
        s["avg_sunlight_per_plant"] += rec["sunlight_per_plant"]

    for s in summary.values():
        if s["count"]:
            s["avg_sunlight_per_plant"] = round(s["avg_sunlight_per_plant"] / s["count"], 4)

    # Build result_summary as list of key-value pairs
    result_summary = []
    for stage, stats in summary.items():
        result_summary.append({
            "key": stage,
            "value": {
                "count": stats["count"],
                "adequate": stats["adequate"],
                "inadequate": stats["inadequate"],
                "avg_sunlight_per_plant": stats["avg_sunlight_per_plant"]
            }
        })

    result = {
        "task_name": "Sunlight Adequacy per Plant",
        "result_summary": result_summary,
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "Sunlight_Adequacy_per_Plant_result.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Saved result to {out_file}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()