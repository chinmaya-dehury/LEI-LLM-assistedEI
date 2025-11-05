import os
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'


def fit_linear_forecast(t_minutes, values, future_t_minutes):
    """
    Fit a simple linear model y = a*t + b. If less than 2 points, use last value as constant.
    Returns predictions for future_t_minutes, slope_per_minute, intercept.
    """
    t = np.asarray(t_minutes, dtype=float)
    y = np.asarray(values, dtype=float)

    if len(t) >= 2 and np.isfinite(t).all() and np.isfinite(y).all():
        try:
            a, b = np.polyfit(t, y, 1)
        except Exception:
            # Fallback to constant if polyfit fails
            a, b = 0.0, float(y[-1])
    elif len(t) == 1:
        a, b = 0.0, float(y[0])
    else:
        a, b = 0.0, np.nan

    preds = a * np.asarray(future_t_minutes, dtype=float) + b
    return preds.tolist(), float(a), float(b)


def clamp(values, vmin, vmax):
    return [float(max(vmin, min(vmax, v))) if pd.notna(v) else None for v in values]


def main():
    # Configuration
    DATA_TYPE = 'temp_humidity'
    TASK_NAME = 'simple_linear_forecast_next_hour'
    TASK_DESC = 'Fit a lightweight linear model on recent readings and forecast temperature_c and humidity_percent for the next 12 five-minute intervals (next hour).'

    input_path = os.path.join('data', DATA_TYPE, 'raw_data.csv')
    output_dir = os.path.join('output', DATA_TYPE)
    os.makedirs(output_dir, exist_ok=True)

    result = {
        'task_name': TASK_NAME,
        'description': TASK_DESC,
        'result_summary': [],
        'result_generated_at': iso_now(),
    }

    if not os.path.exists(input_path):
        msg = f'Input file not found: {input_path}'
        print(msg)
        result['result_summary'].append({
            'name': 'error',
            'value': msg,
            'description': 'The expected input CSV file was not found.',
            'tiemstamp': iso_now()
        })
        with open(os.path.join(output_dir, f'{TASK_NAME}_result.json'), 'w') as f:
            json.dump(result, f, indent=2)
        return

    # Read and clean data
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        msg = f'Failed to read CSV: {e}'
        print(msg)
        result['result_summary'].append({
            'name': 'error',
            'value': msg,
            'description': 'Error reading input CSV.',
            'tiemstamp': iso_now()
        })
        with open(os.path.join(output_dir, f'{TASK_NAME}_result.json'), 'w') as f:
            json.dump(result, f, indent=2)
        return

    required_cols = ['timestamp', 'temperature_c', 'humidity_percent']
    for col in required_cols:
        if col not in df.columns:
            msg = f'Missing required column: {col}'
            print(msg)
            result['result_summary'].append({
                'name': 'error',
                'value': msg,
                'description': 'Input CSV missing required columns.',
                'tiemstamp': iso_now()
            })
            with open(os.path.join(output_dir, f'{TASK_NAME}_result.json'), 'w') as f:
                json.dump(result, f, indent=2)
            return

    # Parse datetime, sort, drop duplicates and NaNs
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp'], keep='last')
    df = df.dropna(subset=['temperature_c', 'humidity_percent'])

    if len(df) == 0:
        msg = 'No valid rows after cleaning.'
        print(msg)
        result['result_summary'].append({
            'name': 'error',
            'value': msg,
            'description': 'Dataset became empty after cleaning.',
            'tiemstamp': iso_now()
        })
        with open(os.path.join(output_dir, f'{TASK_NAME}_result.json'), 'w') as f:
            json.dump(result, f, indent=2)
        return

    # Build time axis in minutes from first timestamp
    t0 = df['timestamp'].iloc[0]
    t_minutes = (df['timestamp'] - t0).dt.total_seconds() / 60.0

    # Future horizon: next 12 steps of 5 minutes each
    last_ts = df['timestamp'].iloc[-1]
    step = timedelta(minutes=5)
    future_timestamps = [last_ts + step * (i + 1) for i in range(12)]
    future_t_minutes = [(ft - t0).total_seconds() / 60.0 for ft in future_timestamps]

    # Fit and forecast temperature
    temp_preds, temp_slope_per_min, temp_intercept = fit_linear_forecast(t_minutes, df['temperature_c'].values, future_t_minutes)
    # Fit and forecast humidity
    hum_preds, hum_slope_per_min, hum_intercept = fit_linear_forecast(t_minutes, df['humidity_percent'].values, future_t_minutes)

    # Clamp to plausible ranges from metadata
    temp_preds = clamp(temp_preds, 15.0, 40.0)
    hum_preds = clamp(hum_preds, 20.0, 100.0)

    # Assemble forecast points
    forecast_points = []
    for ts, t_val, h_val in zip(future_timestamps, temp_preds, hum_preds):
        forecast_points.append({
            'timestamp': ts.replace(microsecond=0).isoformat(),
            'temperature_c': None if t_val is None else round(float(t_val), 2),
            'humidity_percent': None if h_val is None else round(float(h_val), 2)
        })

    # Last observation
    last_row = df.iloc[-1]
    last_obs = {
        'timestamp': last_row['timestamp'].replace(microsecond=0).isoformat(),
        'temperature_c': float(last_row['temperature_c']),
        'humidity_percent': float(last_row['humidity_percent'])
    }

    # Trend per hour
    temp_trend_per_hour = float(temp_slope_per_min * 60.0)
    hum_trend_per_hour = float(hum_slope_per_min * 60.0)

    # Summaries
    result['result_summary'].append({
        'name': 'data_points_used',
        'value': int(len(df)),
        'description': 'Number of valid data points used for fitting.',
        'tiemstamp': iso_now()
    })

    result['result_summary'].append({
        'name': 'last_observation',
        'value': last_obs,
        'description': 'Most recent observed temperature and humidity.',
        'tiemstamp': iso_now()
    })

    result['result_summary'].append({
        'name': 'trend_per_hour_temperature_c',
        'value': round(temp_trend_per_hour, 4),
        'description': 'Estimated linear temperature trend per hour (deg C/hour).',
        'tiemstamp': iso_now()
    })

    result['result_summary'].append({
        'name': 'trend_per_hour_humidity_percent',
        'value': round(hum_trend_per_hour, 4),
        'description': 'Estimated linear humidity trend per hour (%RH/hour).',
        'tiemstamp': iso_now()
    })

    result['result_summary'].append({
        'name': 'forecast_points',
        'value': forecast_points,
        'description': 'Next 12 five-minute forecast points for temperature and humidity.',
        'tiemstamp': iso_now()
    })

    result['result_summary'].append({
        'name': 'end_of_next_hour_prediction',
        'value': forecast_points[-1] if len(forecast_points) > 0 else None,
        'description': 'Forecast at the end of the next hour.',
        'tiemstamp': iso_now()
    })

    # Write result JSON
    output_path = os.path.join(output_dir, f'{TASK_NAME}_result.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Print concise summary to stdout
    print(f'Task: {TASK_NAME}')
    print(f'Input: {input_path}')
    print(f'Data points used: {len(df)}')
    print('Last observed:', last_obs)
    if forecast_points:
        print('First forecast point:', forecast_points[0])
        print('End-of-next-hour forecast:', forecast_points[-1])
    print(f'Results saved to: {output_path}')


if __name__ == '__main__':
    main()
