#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime
import pandas as pd
import numpy as np

def iso_now():
    return datetime.now().isoformat()

def compute_absolute_humidity(T_c, RH_percent):
    """
    Compute absolute humidity (g/m^3) using Tetens formula for saturation vapor pressure.
    e_s (hPa) = 6.112 * exp(17.67*T/(T+243.5))
    e (hPa) = RH/100 * e_s
    AH (g/m^3) = 216.7 * e / (T+273.15)
    """
    T_c = np.asarray(T_c, dtype=float)
    RH_percent = np.asarray(RH_percent, dtype=float)
    e_s = 6.112 * np.exp((17.67 * T_c) / (T_c + 243.5))
    e = (RH_percent / 100.0) * e_s
    ah = 216.7 * e / (T_c + 273.15)
    return ah

def main():
    task_name = "absolute_humidity_estimation"
    task_description = "Estimate absolute humidity (g/m^3) per reading using temperature_c and humidity_percent via saturation vapor pressure-based calculation."
    data_type = "temp_humidity"
    data_path = os.path.join("data", data_type, "raw_data.csv")
    out_dir = os.path.join("output", data_type)
    os.makedirs(out_dir, exist_ok=True)
    result_path = os.path.join(out_dir, f"{task_name}_result.json")

    try:
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at {data_path}")

        df = pd.read_csv(data_path)
        if "timestamp" not in df.columns:
            raise ValueError("Missing 'timestamp' column in data.")
        if "temperature_c" not in df.columns or "humidity_percent" not in df.columns:
            raise ValueError("Missing 'temperature_c' or 'humidity_percent' column in data.")

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "temperature_c", "humidity_percent"]).copy()
        df = df.sort_values("timestamp").reset_index(drop=True)

        if len(df) == 0:
            now_iso = iso_now()
            result = {
                "task_name": task_name,
                "description": task_description,
                "result_summary": [
                    {
                        "name": "status",
                        "value": "no_valid_rows",
                        "description": "No valid rows to compute absolute humidity.",
                        "timestamp": now_iso
                    }
                ],
                "result_generated_at": now_iso
            }
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print(f"Saved result to {result_path}")
            return

        df["absolute_humidity_g_m3"] = compute_absolute_humidity(df["temperature_c"].astype(float).values,
                                                                  df["humidity_percent"].astype(float).values)
        now_iso = iso_now()

        avg_ah = float(np.mean(df["absolute_humidity_g_m3"]))
        min_idx = int(df["absolute_humidity_g_m3"].idxmin())
        max_idx = int(df["absolute_humidity_g_m3"].idxmax())
        min_row = df.loc[min_idx]
        max_row = df.loc[max_idx]
        last_row = df.iloc[-1]

        result_summary = [
            {
                "name": "average_absolute_humidity_g_per_m3",
                "value": round(avg_ah, 3),
                "description": "Average absolute humidity across all records.",
                "timestamp": now_iso
            },
            {
                "name": "minimum_absolute_humidity_g_per_m3",
                "value": round(float(min_row["absolute_humidity_g_m3"]), 3),
                "description": "Minimum absolute humidity observed.",
                "timestamp": pd.to_datetime(min_row["timestamp"]).isoformat()
            },
            {
                "name": "maximum_absolute_humidity_g_per_m3",
                "value": round(float(max_row["absolute_humidity_g_m3"]), 3),
                "description": "Maximum absolute humidity observed.",
                "timestamp": pd.to_datetime(max_row["timestamp"]).isoformat()
            },
            {
                "name": "latest_absolute_humidity_g_per_m3",
                "value": round(float(last_row["absolute_humidity_g_m3"]), 3),
                "description": "Latest absolute humidity value.",
                "timestamp": pd.to_datetime(last_row["timestamp"]).isoformat()
            }
        ]

        result = {
            "task_name": task_name,
            "description": task_description,
            "result_summary": result_summary,
            "result_generated_at": now_iso
        }

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"Saved result to {result_path}")

    except Exception as e:
        now_iso = iso_now()
        err = {
            "task_name": task_name,
            "description": task_description,
            "result_summary": [
                {
                    "name": "error",
                    "value": str(e),
                    "description": "Task execution failed.",
                    "timestamp": now_iso
                }
            ],
            "result_generated_at": now_iso
        }
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(err, f, ensure_ascii=False, indent=2)
        print(json.dumps(err, ensure_ascii=False, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()