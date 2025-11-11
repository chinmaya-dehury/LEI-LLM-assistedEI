#!/usr/bin/env python3
import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def main():
    TASK_NAME = "sensor_stuck_detection"
    TASK_DESCRIPTION = "Detect potential sensor lock-up by checking if rolling std over the last 6 readings is < 0.05°C for temperature or < 0.5% for humidity; flag the period as suspect."
    DATA_TYPE = "temp_humidity"

    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_dir = os.path.join("output", DATA_TYPE)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    result = {
        "task_name": TASK_NAME,
        "description": TASK_DESCRIPTION,
        "result_summary": [],
        "result_generated_at": iso_now()
    }

    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        result["result_summary"].append({
            "name": "read_error",
            "value": {"error": str(e)},
            "description": f"Failed to read data from {data_path}",
            "timestamp": iso_now()
        })
        out_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    required_cols = {"timestamp", "temperature_c", "humidity_percent"}
    if df.empty or not required_cols.issubset(set(df.columns)):
        result["result_summary"].append({
            "name": "no_data",
            "value": {"count": 0},
            "description": "Input data is empty or missing required columns.",
            "timestamp": iso_now()
        })
    else:
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        # Infer typical sampling interval in minutes
        if len(df) > 1:
            deltas = df["timestamp"].diff().dropna()
            try:
                typical_interval_min = int(round(deltas.dt.total_seconds().median() / 60.0))
                if typical_interval_min <= 0:
                    typical_interval_min = 5
            except Exception:
                typical_interval_min = 5
        else:
            typical_interval_min = 5

        # Rolling std over last 6 readings
        df["temp_std6"] = df["temperature_c"].rolling(window=6, min_periods=6).std()
        df["hum_std6"] = df["humidity_percent"].rolling(window=6, min_periods=6).std()

        temp_suspect = df["temp_std6"] < 0.05
        hum_suspect = df["hum_std6"] < 0.5
        suspect = (temp_suspect | hum_suspect).fillna(False).tolist()

        periods = []
        in_run = False
        start_idx = 0
        for i, flag in enumerate(suspect):
            if flag and not in_run:
                in_run = True
                start_idx = i
            elif not flag and in_run:
                end_idx = i - 1
                seg = df.iloc[start_idx:end_idx + 1]
                start_ts = seg["timestamp"].iloc[0]
                end_ts = seg["timestamp"].iloc[-1]
                length = end_idx - start_idx + 1
                duration_min = int(length * typical_interval_min)
                trig = []
                if (seg["temp_std6"] < 0.05).any():
                    trig.append("temperature")
                if (seg["hum_std6"] < 0.5).any():
                    trig.append("humidity")
                periods.append({
                    "start_time": start_ts.isoformat(),
                    "end_time": end_ts.isoformat(),
                    "duration_minutes": duration_min,
                    "count_readings": int(length),
                    "triggered_by": trig,
                    "min_temp_std6": (float(round(seg["temp_std6"].min(), 4)) if not seg["temp_std6"].isna().all() else None),
                    "min_hum_std6": (float(round(seg["hum_std6"].min(), 4)) if not seg["hum_std6"].isna().all() else None)
                })
                in_run = False
        # Handle trailing run
        if in_run:
            end_idx = len(suspect) - 1
            seg = df.iloc[start_idx:end_idx + 1]
            start_ts = seg["timestamp"].iloc[0]
            end_ts = seg["timestamp"].iloc[-1]
            length = end_idx - start_idx + 1
            duration_min = int(length * typical_interval_min)
            trig = []
            if (seg["temp_std6"] < 0.05).any():
                trig.append("temperature")
            if (seg["hum_std6"] < 0.5).any():
                trig.append("humidity")
            periods.append({
                "start_time": start_ts.isoformat(),
                "end_time": end_ts.isoformat(),
                "duration_minutes": duration_min,
                "count_readings": int(length),
                "triggered_by": trig,
                "min_temp_std6": (float(round(seg["temp_std6"].min(), 4)) if not seg["temp_std6"].isna().all() else None),
                "min_hum_std6": (float(round(seg["hum_std6"].min(), 4)) if not seg["hum_std6"].isna().all() else None)
            })

        if periods:
            for idx, p in enumerate(periods, 1):
                result["result_summary"].append({
                    "name": f"suspect_period_{idx}",
                    "value": p,
                    "description": "Low rolling std suggests sensor may be stuck.",
                    "timestamp": p["end_time"]
                })
            result["result_summary"].append({
                "name": "total_suspect_periods",
                "value": {"count": len(periods)},
                "description": "Total number of suspect periods detected.",
                "timestamp": iso_now()
            })
        else:
            result["result_summary"].append({
                "name": "no_suspect_periods",
                "value": {"count": 0},
                "description": "No suspect periods detected using rolling std thresholds.",
                "timestamp": iso_now()
            })

    out_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()