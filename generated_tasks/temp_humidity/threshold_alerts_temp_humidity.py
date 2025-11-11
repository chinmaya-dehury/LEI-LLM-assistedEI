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
    TASK_NAME = "threshold_alerts_temp_humidity"
    TASK_DESCRIPTION = "Trigger alerts when temperature_c > 30.0°C or humidity_percent > 65.0% for at least 2 consecutive readings; include start time, end time, and duration."
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

        cond_series = (df["temperature_c"] > 30.0) | (df["humidity_percent"] > 65.0)
        cond = cond_series.fillna(False).tolist()

        alerts = []
        in_run = False
        start_idx = 0
        for i, flag in enumerate(cond):
            if flag and not in_run:
                in_run = True
                start_idx = i
            elif not flag and in_run:
                end_idx = i - 1
                length = end_idx - start_idx + 1
                if length >= 2:
                    seg = df.iloc[start_idx:end_idx + 1]
                    start_ts = seg["timestamp"].iloc[0]
                    end_ts = seg["timestamp"].iloc[-1]
                    duration_min = int(length * typical_interval_min)
                    alerts.append({
                        "start_time": start_ts.isoformat(),
                        "end_time": end_ts.isoformat(),
                        "duration_minutes": duration_min,
                        "count_readings": int(length),
                        "max_temperature_c": float(round(seg["temperature_c"].max(), 2)),
                        "max_humidity_percent": float(round(seg["humidity_percent"].max(), 2))
                    })
                in_run = False
        # Handle trailing run
        if in_run:
            end_idx = len(cond) - 1
            length = end_idx - start_idx + 1
            if length >= 2:
                seg = df.iloc[start_idx:end_idx + 1]
                start_ts = seg["timestamp"].iloc[0]
                end_ts = seg["timestamp"].iloc[-1]
                duration_min = int(length * typical_interval_min)
                alerts.append({
                    "start_time": start_ts.isoformat(),
                    "end_time": end_ts.isoformat(),
                    "duration_minutes": duration_min,
                    "count_readings": int(length),
                    "max_temperature_c": float(round(seg["temperature_c"].max(), 2)),
                    "max_humidity_percent": float(round(seg["humidity_percent"].max(), 2))
                })

        if alerts:
            for idx, a in enumerate(alerts, 1):
                result["result_summary"].append({
                    "name": f"alert_period_{idx}",
                    "value": a,
                    "description": "Consecutive readings exceeded thresholds (temp>30.0°C or humidity>65.0%).",
                    "timestamp": a["end_time"]
                })
            result["result_summary"].append({
                "name": "total_alert_periods",
                "value": {"count": len(alerts)},
                "description": "Total number of alert periods detected.",
                "timestamp": iso_now()
            })
        else:
            result["result_summary"].append({
                "name": "no_alerts",
                "value": {"count": 0},
                "description": "No periods with thresholds exceeded for at least 2 consecutive readings.",
                "timestamp": iso_now()
            })

    out_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()