import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

TASK_NAME = 'pollutant_24h_extremes_reporter'
TASK_DESC = 'Report 24-hour min/max values and their timestamps for key pollutants (PM2.5, PM10, NO2, O3); handles sparse data and includes sample count and coverage percentage.'
DATA_TYPE = 'air_quality'

KEY_POLLUTANTS = ['pm2_5', 'pm10', 'no2', 'o3']

def iso(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def read_data(path):
    df = pd.read_csv(path)
    ts = None
    if 'timestamp_utc' in df.columns:
        ts = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
    if ts is None or ts.isna().all():
        if 'timestamp_unix' in df.columns:
            ts = pd.to_datetime(df['timestamp_unix'], unit='s', utc=True, errors='coerce')
    if ts is None:
        raise ValueError('No usable timestamp column found.')
    df['ts'] = ts
    df = df.dropna(subset=['ts']).sort_values('ts').reset_index(drop=True)
    return df

def compute_expected_count(ts_series):
    if len(ts_series) < 2:
        return 96  # assume 15-minute cadence if insufficient data
    deltas = ts_series.sort_values().diff().dropna().dt.total_seconds() / 60.0
    med = np.median(deltas) if len(deltas) else np.nan
    if not np.isfinite(med) or med <= 0:
        return 96
    return max(1, int(round(24*60.0/med)))

def main():
    data_path = os.path.join('data', DATA_TYPE, 'raw_data.csv')
    out_dir = os.path.join('output', DATA_TYPE)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{TASK_NAME}_result.json")

    result_summary = []
    if not Path(data_path).exists():
        msg = f"Data file not found at {data_path}"
        print(msg)
        result_summary.append({
            'name': 'error',
            'value': {'message': msg},
            'description': 'Input CSV missing; cannot compute 24h extremes.',
            'timestamp': iso_now()
        })
        result = {
            'task_name': TASK_NAME,
            'description': TASK_DESC,
            'result_summary': result_summary,
            'result_generated_at': iso_now()
        }
        with open(out_path, 'w', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2)
        return

    try:
        df = read_data(data_path)
    except Exception as e:
        print(f"Failed to read/parse data: {e}")
        result_summary.append({
            'name': 'error',
            'value': {'message': str(e)},
            'description': 'Failed to parse timestamps from CSV.',
            'timestamp': iso_now()
        })
        result = {
            'task_name': TASK_NAME,
            'description': TASK_DESC,
            'result_summary': result_summary,
            'result_generated_at': iso_now()
        }
        with open(out_path, 'w', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2)
        return

    if df.empty:
        print('No data rows after parsing timestamps.')
        result_summary.append({
            'name': 'no_data',
            'value': {},
            'description': 'No valid timestamped rows.',
            'timestamp': iso_now()
        })
        result = {
            'task_name': TASK_NAME,
            'description': TASK_DESC,
            'result_summary': result_summary,
            'result_generated_at': iso_now()
        }
        with open(out_path, 'w', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2)
        return

    window_end = df['ts'].max()
    window_start = window_end - pd.Timedelta(hours=24)
    dfw = df[(df['ts'] > window_start) & (df['ts'] <= window_end)].copy()

    expected_count = compute_expected_count(dfw['ts'])
    total_samples = len(dfw)
    coverage_total = round(min(100.0, (total_samples/expected_count)*100.0), 2) if expected_count else 0.0

    # Overall window summary
    result_summary.append({
        'name': 'window_summary',
        'value': {
            'window_start': iso(window_start.to_pydatetime()),
            'window_end': iso(window_end.to_pydatetime()),
            'samples_in_window': int(total_samples),
            'expected_samples': int(expected_count),
            'coverage_percent': coverage_total
        },
        'description': '24h analysis window based on last available timestamp in data.',
        'timestamp': iso(window_end.to_pydatetime())
    })

    # Compute extremes per pollutant
    for pol in KEY_POLLUTANTS:
        if pol not in dfw.columns:
            result_summary.append({
                'name': f'{pol}_24h_extremes',
                'value': {'available': False, 'reason': 'column_missing'},
                'description': f'Column {pol} not found in data; skipped.',
                'timestamp': iso(window_end.to_pydatetime())
            })
            continue
        s = dfw[[pol, 'ts']].dropna(subset=[pol])
        count = int(len(s))
        if count == 0:
            result_summary.append({
                'name': f'{pol}_24h_extremes',
                'value': {'available': False, 'reason': 'no_values_in_window'},
                'description': 'No data points for this pollutant in the 24h window.',
                'timestamp': iso(window_end.to_pydatetime())
            })
            continue
        min_idx = s[pol].idxmin()
        max_idx = s[pol].idxmax()
        min_val = float(s.loc[min_idx, pol])
        max_val = float(s.loc[max_idx, pol])
        min_ts = s.loc[min_idx, 'ts'].to_pydatetime()
        max_ts = s.loc[max_idx, 'ts'].to_pydatetime()
        coverage = round(min(100.0, (count/expected_count)*100.0), 2) if expected_count else 0.0
        value_obj = {
            'min_value': min_val,
            'min_timestamp': iso(min_ts),
            'max_value': max_val,
            'max_timestamp': iso(max_ts),
            'sample_count': count,
            'coverage_percent': coverage
        }
        result_summary.append({
            'name': f'{pol}_24h_extremes',
            'value': value_obj,
            'description': f'24h extremes for {pol.upper()} with sample count and coverage.',
            'timestamp': iso(window_end.to_pydatetime())
        })
        print(f"{pol.upper()}: min={min_val} at {iso(min_ts)}, max={max_val} at {iso(max_ts)}, samples={count}, coverage={coverage}%")

    result = {
        'task_name': TASK_NAME,
        'description': TASK_DESC,
        'result_summary': result_summary,
        'result_generated_at': iso_now()
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()