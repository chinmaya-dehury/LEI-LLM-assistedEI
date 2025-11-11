#!/usr/bin/env python3
import os
import csv
import json
from datetime import datetime, timezone
from math import atan, sqrt, pow

TASK_NAME = "wet_bulb_temperature_stull"
TASK_DESCRIPTION = "Estimate wet-bulb temperature (°C) per reading using Stull’s empirical formula from temperature_c and humidity_percent; output WBT and simple heat stress bands (e.g., <20 safe, 20–24 caution, 24–26 high caution, >26 danger)."
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

def stull_wbt_c(t, rh):
    rhc = max(0.0, min(100.0, rh))
    return (
        t * atan(0.151977 * sqrt(rhc + 8.313659))
        + atan(t + rhc)
        - atan(rhc - 1.676331)
        + 0.00391838 * pow(rhc, 1.5) * atan(0.023101 * rhc)
        - 4.686035
    )

def band_from_wbt(wbt):
    if wbt < 20.0:
        return "safe"
    elif wbt < 24.0:
        return "caution"
    elif wbt < 26.0:
        return "high caution"
    else:
        return "danger"

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
        wbt = stull_wbt_c(r["temperature_c"], r["humidity_percent"])
        band = band_from_wbt(wbt)
        enhanced.append({**r, "wbt_c": wbt, "band": band})

    latest = enhanced[-1]
    max_row = max(enhanced, key=lambda x: x["wbt_c"])

    # Distribution counts
    dist = {"safe": 0, "caution": 0, "high caution": 0, "danger": 0}
    for e in enhanced:
        dist[e["band"]] = dist.get(e["band"], 0) + 1

    mean_wbt = sum(e["wbt_c"] for e in enhanced) / len(enhanced)

    result = {
        "task_name": TASK_NAME,
        "description": TASK_DESCRIPTION,
        "result_summary": [
            {
                "name": "latest_wet_bulb_temperature_c",
                "value": {
                    "wbt_c": round(latest["wbt_c"], 2),
                    "band": latest["band"],
                    "temperature_c": round(latest["temperature_c"], 2),
                    "humidity_percent": round(latest["humidity_percent"], 2)
                },
                "description": "Latest computed wet-bulb temperature and heat stress band.",
                "timestamp": iso(latest["timestamp"]) 
            },
            {
                "name": "max_wet_bulb_temperature_c",
                "value": {
                    "wbt_c": round(max_row["wbt_c"], 2),
                    "band": max_row["band"],
                    "at": iso(max_row["timestamp"]),
                    "temperature_c": round(max_row["temperature_c"], 2),
                    "humidity_percent": round(max_row["humidity_percent"], 2)
                },
                "description": "Maximum wet-bulb temperature observed in the dataset.",
                "timestamp": iso(max_row["timestamp"]) 
            },
            {
                "name": "mean_wet_bulb_temperature_c",
                "value": round(mean_wbt, 2),
                "description": "Mean wet-bulb temperature across all readings.",
                "timestamp": iso(latest["timestamp"]) 
            },
            {
                "name": "heat_stress_distribution",
                "value": dist,
                "description": "Counts of readings in each heat stress band.",
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