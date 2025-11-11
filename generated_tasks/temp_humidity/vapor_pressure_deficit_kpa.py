#!/usr/bin/env python3
import os
import csv
import json
from datetime import datetime, timezone
from math import exp

TASK_NAME = "vapor_pressure_deficit_kpa"
TASK_DESCRIPTION = "Compute saturation vapor pressure (es) from temperature_c (Magnus), actual vapor pressure (ea = es * RH/100), and VPD = es - ea (kPa); classify humidity dryness bands (<0.6 humid, 0.6–1.2 moderate, >1.2 dry)."
DATA_TYPE = "temp_humidity"

def parse_ts(s):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s.strip())
    except Exception:
        return None

def read_rows(data_path):
    rows = []
    with open(data_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for r in reader:
            ts = parse_ts(r.get("timestamp", ""))
            if ts is None:
                continue
            try:
                t = float(r.get("temperature_c", ""))
                rh = float(r.get("humidity_percent", ""))
            except Exception:
                continue
            rows.append({"timestamp": ts, "temperature_c": t, "humidity_percent": rh})
    rows.sort(key=lambda x: x["timestamp"])
    return rows

def saturation_vapor_pressure_kpa(t_c):
    # Magnus formula (kPa)
    return 0.6108 * exp((17.27 * t_c) / (t_c + 237.3))

def vpd_band(vpd):
    if vpd < 0.6:
        return "humid"
    elif vpd <= 1.2:
        return "moderate"
    else:
        return "dry"

def iso_now_utc():
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

def iso(dt):
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt)

def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    out_dir = os.path.join("output", DATA_TYPE)
    os.makedirs(out_dir, exist_ok=True)
    result_path = os.path.join(out_dir, f"{TASK_NAME}_result.json")

    if not os.path.exists(data_path):
        print(f"[ERROR] Data file not found: {data_path}")
        return

    rows = read_rows(data_path)
    if not rows:
        print("[ERROR] No valid rows found.")
        return

    enhanced = []
    for r in rows:
        t = r["temperature_c"]
        rh = max(0.0, min(100.0, r["humidity_percent"]))
        es = saturation_vapor_pressure_kpa(t)
        ea = es * (rh / 100.0)
        vpd = es - ea
        enhanced.append({**r, "es_kpa": es, "ea_kpa": ea, "vpd_kpa": vpd, "band": vpd_band(vpd)})

    latest = enhanced[-1]
    max_row = max(enhanced, key=lambda x: x["vpd_kpa"])
    mean_vpd = sum(e["vpd_kpa"] for e in enhanced) / len(enhanced)

    dist = {"humid": 0, "moderate": 0, "dry": 0}
    for e in enhanced:
        dist[e["band"]] = dist.get(e["band"], 0) + 1

    result = {
        "task_name": TASK_NAME,
        "description": TASK_DESCRIPTION,
        "result_summary": [
            {
                "name": "latest_vpd_kpa",
                "value": {
                    "vpd_kpa": round(latest["vpd_kpa"], 3),
                    "band": latest["band"],
                    "es_kpa": round(latest["es_kpa"], 3),
                    "ea_kpa": round(latest["ea_kpa"], 3),
                    "temperature_c": round(latest["temperature_c"], 2),
                    "humidity_percent": round(latest["humidity_percent"], 2)
                },
                "description": "Latest vapor pressure deficit with components and dryness band.",
                "timestamp": iso(latest["timestamp"]) 
            },
            {
                "name": "max_vpd_kpa",
                "value": {
                    "vpd_kpa": round(max_row["vpd_kpa"], 3),
                    "band": max_row["band"],
                    "at": iso(max_row["timestamp"]),
                    "temperature_c": round(max_row["temperature_c"], 2),
                    "humidity_percent": round(max_row["humidity_percent"], 2)
                },
                "description": "Maximum VPD observed in the dataset.",
                "timestamp": iso(max_row["timestamp"]) 
            },
            {
                "name": "mean_vpd_kpa",
                "value": round(mean_vpd, 3),
                "description": "Mean VPD across all readings.",
                "timestamp": iso(latest["timestamp"]) 
            },
            {
                "name": "dryness_distribution",
                "value": dist,
                "description": "Counts of readings in each dryness band.",
                "timestamp": iso(latest["timestamp"]) 
            }
        ],
        "result_generated_at": iso_now_utc()
    }

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] Results written to {result_path}")
    print(json.dumps(result["result_summary"], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()