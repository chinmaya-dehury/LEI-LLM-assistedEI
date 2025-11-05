#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
absolute_humidity_estimation

Reads environmental sensor data from data/environment/raw_data.csv and computes
absolute humidity (g/m³) for each record using the Magnus formula.
Outputs summary metrics to output/environment/absolute_humidity_estimation_result.json
and prints the same JSON to stdout.

Lightweight: uses only Python standard libraries.
"""

import csv
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

DATA_TYPE = "environment"
INPUT_PATH = Path(f"data/{DATA_TYPE}/raw_data.csv")
OUTPUT_DIR = Path(f"output/{DATA_TYPE}")
OUTPUT_FILE = OUTPUT_DIR / "absolute_humidity_estimation_result.json"
TASK_NAME = "absolute_humidity_estimation"
TASK_DESCRIPTION = (
    "Compute absolute humidity (g/m³) from temperature_c and humidity_percent to quantify moisture load independent of temperature."
)


def parse_row(row: Dict[str, str]) -> Tuple[datetime, float, float]:
    """Parse a CSV row into (timestamp, temp_c, rh_percent)."""
    # Accept common timestamp formats; prefer ISO-like
    ts_str = row.get("timestamp", "").strip()
    # Try multiple formats for robustness
    dt = None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            dt = datetime.strptime(ts_str, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        raise ValueError(f"Unrecognized timestamp format: {ts_str}")

    t_c = float(row.get("temperature_c", "nan"))
    rh = float(row.get("humidity_percent", "nan"))
    if math.isnan(t_c) or math.isnan(rh):
        raise ValueError("Missing temperature or humidity value")
    return dt, t_c, rh


def saturation_vapor_pressure_hpa(temp_c: float) -> float:
    """Magnus-Tetens approximation for saturation vapor pressure over water in hPa.
    Uses constants suitable for 0°C to 50°C range.
    """
    return 6.112 * math.exp((17.62 * temp_c) / (243.12 + temp_c))


def absolute_humidity_g_m3(temp_c: float, rh_percent: float) -> float:
    """Compute absolute humidity in g/m³.

    Steps:
    - Compute saturation vapor pressure es (hPa)
    - Actual vapor pressure e = RH * es / 100 (hPa)
    - AH (g/m³) = 216.7 * e / (T_K) where T_K = T_C + 273.15 and e in hPa
    """
    es = saturation_vapor_pressure_hpa(temp_c)
    e = (rh_percent / 100.0) * es  # hPa
    t_k = temp_c + 273.15
    ah = 216.7 * e / t_k
    return ah


def load_data(path: Path) -> List[Dict]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    records: List[Dict] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        expected_cols = {"timestamp", "temperature_c", "humidity_percent"}
        if not expected_cols.issubset(set(c.strip() for c in reader.fieldnames or [])):
            raise ValueError(
                f"CSV missing required columns. Found: {reader.fieldnames}, expected at least: {sorted(expected_cols)}"
            )
        for row in reader:
            try:
                dt, t_c, rh = parse_row(row)
            except Exception as e:
                # Skip bad rows but continue
                continue
            ah = absolute_humidity_g_m3(t_c, rh)
            records.append({
                "timestamp": dt,
                "temperature_c": t_c,
                "humidity_percent": rh,
                "absolute_humidity_g_m3": ah,
            })

    # Sort by timestamp
    records.sort(key=lambda r: r["timestamp"]) 
    return records


def summarize(records: List[Dict]) -> List[Dict]:
    if not records:
        return []

    # Basic aggregates
    ah_values = [r["absolute_humidity_g_m3"] for r in records]

    avg_ah = sum(ah_values) / len(ah_values)
    max_idx = max(range(len(records)), key=lambda i: records[i]["absolute_humidity_g_m3"]) 
    min_idx = min(range(len(records)), key=lambda i: records[i]["absolute_humidity_g_m3"]) 

    first_dt = records[0]["timestamp"]
    last_dt = records[-1]["timestamp"]
    # Timestamp choice for average: midpoint of the dataset window to avoid implying a single reading time
    if last_dt >= first_dt:
        midpoint_dt = first_dt + (last_dt - first_dt) / 2
    else:
        midpoint_dt = first_dt

    def ts(dt: datetime) -> str:
        # Use naive local ISO string with seconds to match data style and avoid timezone mixing
        return dt.isoformat(timespec="seconds")

    def round2(x: float) -> float:
        return float(round(x, 2))

    summary = [
        {
            "name": "average_absolute_humidity_g_m3",
            "value": round2(avg_ah),
            "description": f"Mean absolute humidity over dataset window from {ts(first_dt)} to {ts(last_dt)}.",
            "timestamp": ts(midpoint_dt),
        },
        {
            "name": "max_absolute_humidity_g_m3",
            "value": round2(records[max_idx]["absolute_humidity_g_m3"]),
            "description": "Maximum absolute humidity observed and its timestamp.",
            "timestamp": ts(records[max_idx]["timestamp"]),
        },
        {
            "name": "min_absolute_humidity_g_m3",
            "value": round2(records[min_idx]["absolute_humidity_g_m3"]),
            "description": "Minimum absolute humidity observed and its timestamp.",
            "timestamp": ts(records[min_idx]["timestamp"]),
        },
        {
            "name": "latest_absolute_humidity_g_m3",
            "value": round2(records[-1]["absolute_humidity_g_m3"]),
            "description": "Most recent absolute humidity value.",
            "timestamp": ts(last_dt),
        },
    ]

    return summary


def main() -> None:
    try:
        records = load_data(INPUT_PATH)
    except Exception as e:
        print(json.dumps({
            "task_name": TASK_NAME,
            "description": TASK_DESCRIPTION,
            "error": str(e),
            "result_generated_at": datetime.now().isoformat(timespec="seconds")
        }, ensure_ascii=False))
        return

    result_summary = summarize(records)

    result = {
        "task_name": TASK_NAME,
        "description": TASK_DESCRIPTION,
        "result_summary": result_summary,
        # Use naive local time to keep consistent with data timestamps (no timezone)
        "result_generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Also print to stdout
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
