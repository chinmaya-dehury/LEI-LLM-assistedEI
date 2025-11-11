#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime
import pandas as pd
import numpy as np

def iso_now():
    return datetime.now().isoformat()

def ses_forecast_mean_and_sigma(values, alpha=0.3):
    """
    Simple Exponential Smoothing (SES) to estimate next-step level and residual sigma.
    Returns (forecast_mean, residual_sigma).
    """
    vals = [float(v) for v in values if pd.notnull(v)]
    if len(vals) == 0:
        raise ValueError("Empty series for SES forecast")
    level = vals[0]
    residuals = []
    for t in range(1, len(vals)):
        pred = level
        residuals.append(vals[t] - pred)
        level = alpha * vals[t] + (1.0 - alpha) * level
    sigma = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
    return float(level), sigma

def main():
    task_name = "next_hour_forecast_ses"
    task_description = "Predict next 60-minute average temperature and humidity using simple exponential smoothing (alpha=0.3) on 5-minute data; output mean forecast and an approximate ±1σ uncertainty from residuals."
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

        if len(df) < 1:
            now_iso = iso_now()
            result = {
                "task_name": task_name,
                "description": task_description,
                "result_summary": [
                    {
                        "name": "status",
                        "value": "no_valid_rows",
                        "description": "No valid rows available for SES forecasting.",
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

        alpha = 0.3
        horizon_minutes = 60
        step_minutes = 5
        steps_ahead = max(1, horizon_minutes // step_minutes)

        temp_forecast, temp_sigma = ses_forecast_mean_and_sigma(df["temperature_c"].values, alpha=alpha)
        hum_forecast, hum_sigma = ses_forecast_mean_and_sigma(df["humidity_percent"].values, alpha=alpha)

        # For SES with constant level, all horizons share the same forecast; the 60-min average equals that level
        now_iso = iso_now()
        result_summary = [
            {
                "name": "next_60min_temperature_mean_forecast_c",
                "value": round(float(temp_forecast), 2),
                "description": f"SES(alpha={alpha}) forecast for the next {horizon_minutes}-minute average temperature.",
                "timestamp": now_iso
            },
            {
                "name": "next_60min_temperature_sigma_c",
                "value": round(float(temp_sigma), 2),
                "description": "Approximate ±1σ from in-sample SES residuals (one-step-ahead).",
                "timestamp": now_iso
            },
            {
                "name": "next_60min_humidity_mean_forecast_percent",
                "value": round(float(hum_forecast), 2),
                "description": f"SES(alpha={alpha}) forecast for the next {horizon_minutes}-minute average humidity.",
                "timestamp": now_iso
            },
            {
                "name": "next_60min_humidity_sigma_percent",
                "value": round(float(hum_sigma), 2),
                "description": "Approximate ±1σ from in-sample SES residuals (one-step-ahead).",
                "timestamp": now_iso
            },
            {
                "name": "config_horizon_minutes",
                "value": horizon_minutes,
                "description": "Prediction window length in minutes.",
                "timestamp": now_iso
            },
            {
                "name": "config_alpha",
                "value": alpha,
                "description": "SES smoothing parameter used.",
                "timestamp": now_iso
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