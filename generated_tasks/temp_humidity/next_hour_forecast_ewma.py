#!/usr/bin/env python3
import os
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np


def iso_now():
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()


def safe_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return default


def read_and_clean(input_path):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)

    # Normalize column names (strip spaces, lower-case)
    df.columns = [c.strip() for c in df.columns]

    # Parse timestamp and coerce to numeric for sensor columns
    if 'timestamp' not in df.columns:
        raise ValueError("'timestamp' column missing from input data")

    # Try to map common variants if needed
    temp_col = 'temperature_c'
    humid_col = 'humidity_percent'

    if temp_col not in df.columns:
        raise ValueError("'temperature_c' column missing from input data")
    if humid_col not in df.columns:
        raise ValueError("'humidity_percent' column missing from input data")

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df[temp_col] = pd.to_numeric(df[temp_col], errors='coerce')
    df[humid_col] = pd.to_numeric(df[humid_col], errors='coerce')

    # Drop rows with invalid timestamp or sensor values
    df = df.dropna(subset=['timestamp', temp_col, humid_col])
    if df.empty:
        raise ValueError("No valid rows after cleaning (timestamp/temperature/humidity)")

    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def infer_sampling_seconds(ts_series):
    if len(ts_series) < 2:
        return 300  # default to 5 minutes if insufficient data
    deltas = ts_series.diff().dt.total_seconds().dropna()
    if deltas.empty:
        return 300
    med = np.median(deltas.values)
    # Fallback sanity
    if not np.isfinite(med) or med <= 0:
        return 300
    return int(round(med))


def compute_N_for_next_hour(sampling_seconds):
    # Number of readings in ~60 minutes
    if sampling_seconds <= 0:
        return 12
    return max(1, int(round(3600 / sampling_seconds)))


def ewma_forecast_last_N(series: pd.Series, N: int, alpha: float):
    # Use ONLY last N readings per validation feedback
    s = series.tail(N).dropna()
    count = int(s.shape[0])
    if count == 0:
        return np.nan, np.nan, 0
    # EWMA (simple exponential smoothing)
    ema = s.ewm(alpha=alpha, adjust=False).mean()
    forecast = float(ema.iloc[-1])
    resid = s - ema
    resid_std = float(resid.std(ddof=1)) if len(resid) > 1 else np.nan
    return forecast, resid_std, count


def clamp(val, lo, hi):
    if not np.isfinite(val):
        return val
    return max(lo, min(hi, val))


def main():
    DATA_TYPE = os.environ.get('DATA_TYPE', 'environment')
    TASK_NAME = 'next_hour_forecast_ewma'
    DESCRIPTION = 'Predict the next 60-minute average temperature and humidity using simple exponential smoothing (EWMA) over the last N readings.'

    input_path = f"data/{DATA_TYPE}/raw_data.csv"
    output_dir = f"output/{DATA_TYPE}"
    os.makedirs(output_dir, exist_ok=True)

    result_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")

    try:
        df = read_and_clean(input_path)

        sampling_seconds = infer_sampling_seconds(df['timestamp'])
        default_N = compute_N_for_next_hour(sampling_seconds)

        # N is configurable via EWMA_N; default to cover next hour
        N_env = os.environ.get('EWMA_N')
        if N_env is not None:
            try:
                N = max(1, int(N_env))
            except Exception:
                N = default_N
        else:
            N = default_N

        # Alpha is configurable via EWMA_ALPHA; default from span=N -> alpha = 2/(N+1)
        alpha_env = os.environ.get('EWMA_ALPHA')
        if alpha_env is not None:
            try:
                alpha = float(alpha_env)
            except Exception:
                alpha = 2.0 / (N + 1.0)
        else:
            alpha = 2.0 / (N + 1.0)
        # Bound alpha strictly within (0,1)
        alpha = min(0.9999, max(0.0001, alpha))

        temp_forecast, temp_resid_std, temp_count = ewma_forecast_last_N(df['temperature_c'], N, alpha)
        hum_forecast, hum_resid_std, hum_count = ewma_forecast_last_N(df['humidity_percent'], N, alpha)

        # For next 60-min average, we use the one-step EWMA level as representative (constant level assumption)
        # Clamp predictions to plausible ranges per metadata
        temp_pred = clamp(temp_forecast, 15.0, 40.0)
        hum_pred = clamp(hum_forecast, 20.0, 100.0)

        last_ts = df['timestamp'].iloc[-1]
        now_iso = iso_now()

        result_summary = []
        result_summary.append({
            'name': 'predicted_next_hour_avg_temperature_c',
            'value': None if not np.isfinite(temp_pred) else round(float(temp_pred), 2),
            'description': f"EWMA forecast using only the last {N} readings (alpha={alpha:.4f}).",
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'predicted_next_hour_avg_humidity_percent',
            'value': None if not np.isfinite(hum_pred) else round(float(hum_pred), 2),
            'description': f"EWMA forecast using only the last {N} readings (alpha={alpha:.4f}).",
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'alpha_used',
            'value': round(float(alpha), 6),
            'description': 'Smoothing parameter used for EWMA.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'N_readings_used',
            'value': int(N),
            'description': 'Number of most recent readings used for smoothing (slice applied before EWMA).',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'sampling_interval_seconds',
            'value': int(sampling_seconds),
            'description': 'Median inferred sampling interval from timestamps.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'data_points_used_temperature',
            'value': int(temp_count),
            'description': 'Count of valid temperature points in the last N readings.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'data_points_used_humidity',
            'value': int(hum_count),
            'description': 'Count of valid humidity points in the last N readings.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'last_observation_timestamp',
            'value': (last_ts.tz_localize(timezone.utc).isoformat() if last_ts.tzinfo is None else last_ts.astimezone(timezone.utc).isoformat()),
            'description': 'Timestamp of the most recent input observation.',
            'timestamp': now_iso
        })

        result_obj = {
            'task_name': TASK_NAME,
            'description': DESCRIPTION,
            'result_summary': result_summary,
            'result_generated_at': now_iso
        }

        with open(result_path, 'w') as f:
            json.dump(result_obj, f, indent=2)

        # Print concise console output
        print(f"Task: {TASK_NAME}")
        print(f"Input: {input_path}")
        print(f"Used last N readings: {N}, alpha: {alpha:.4f}, sampling interval (s): {sampling_seconds}")
        print(f"Predicted next-hour average temperature (C): {result_summary[0]['value']}")
        print(f"Predicted next-hour average humidity (%): {result_summary[1]['value']}")
        print(f"Result saved to: {result_path}")

    except Exception as e:
        now_iso = iso_now()
        # On error, still emit a result file with the error info
        result_obj = {
            'task_name': 'next_hour_forecast_ewma',
            'description': 'Predict the next 60-minute average temperature and humidity using simple exponential smoothing (EWMA) over the last N readings.',
            'result_summary': [
                {
                    'name': 'error',
                    'value': str(e),
                    'description': 'An error occurred while computing EWMA forecast.',
                    'timestamp': now_iso
                }
            ],
            'result_generated_at': now_iso
        }
        os.makedirs(os.path.dirname(result_path), exist_ok=True)
        with open(result_path, 'w') as f:
            json.dump(result_obj, f, indent=2)
        print(f"Error: {e}")
        print(f"Partial result saved to: {result_path}")


if __name__ == '__main__':
    main()
