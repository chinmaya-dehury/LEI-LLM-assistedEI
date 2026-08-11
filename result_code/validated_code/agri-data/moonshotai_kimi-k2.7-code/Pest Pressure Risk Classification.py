import json
import sys
import csv
import os
from pathlib import Path
from datetime import datetime, timezone
import argparse

"""
Task: Pest Pressure Risk Classification
Description: Classify pest risk level (low, medium, high) using Pest_Pressure along with Humidity and Temperature thresholds, supporting targeted pest management decisions.
"""

MISSING = {'', 'na', 'n/a', 'none', 'null'}

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ("raw_data.csv", "raw_data.txt"):
        f = root_dir / "data" / "agri-data" / name
        if f.exists():
            return f
    return None

def to_float(value, col):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value '{value}' in column '{col}', skipping field", file=sys.stderr)
        return None

def classify(pp, hum, temp):
    if pp >= 1.5 or (hum > 80 and 20 <= temp <= 30):
        return "high"
    if pp >= 1.0 or (hum > 70 and temp > 18):
        return "medium"
    return "low"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Skip rows with missing required values")
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/agri-data/", file=sys.stderr)
        sys.exit(1)

    required = ["pest_pressure", "humidity", "temperature"]
    counts = {"low": 0, "medium": 0, "high": 0}
    total = 0
    dropped = 0
    invalid = 0
    samples = []

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = [h.lower().strip() for h in (reader.fieldnames or [])]
        missing_cols = [c for c in required if c not in headers]
        if missing_cols:
            print(f"Error: required columns missing from header: {missing_cols}", file=sys.stderr)
            sys.exit(1)

        for row in reader:
            total += 1
            row = {k.lower().strip(): v for k, v in row.items()}
            missing_req = any(row.get(c, "").strip().lower() in MISSING for c in required)
            if missing_req:
                dropped += 1
                if args.strict:
                    continue
                continue

            pp = to_float(row.get("pest_pressure"), "pest_pressure")
            hum = to_float(row.get("humidity"), "humidity")
            temp = to_float(row.get("temperature"), "temperature")
            if pp is None or hum is None or temp is None:
                invalid += 1
                continue

            risk = classify(pp, hum, temp)
            counts[risk] += 1
            if len(samples) < 5:
                samples.append({"pest_pressure": pp, "humidity": hum, "temperature": temp, "risk": risk})

    summary = {
        "input_file": str(data_file),
        "total_rows": total,
        "dropped_missing": dropped,
        "invalid_numeric": invalid,
        "classified_rows": sum(counts.values()),
        "thresholds": {
            "high": "pest_pressure >= 1.5 OR (humidity > 80 AND 20 <= temperature <= 30)",
            "medium": "pest_pressure >= 1.0 OR (humidity > 70 AND temperature > 18)",
            "low": "otherwise"
        },
        "risk_distribution": counts,
        "sample_classifications": samples
    }

    # Convert summary to list of key-value pairs for result_summary
    result_summary = [{"key": k, "value": v} for k, v in summary.items()]

    result = {
        "task_name": "Pest Pressure Risk Classification",
        "result_summary": result_summary
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "pest_pressure_risk_classification_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    # Print the result JSON to stdout for validation capture
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()