#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

try:
    import pandas as pd
    import numpy as np
except Exception as e:
    print('Error: pandas and numpy are required to run this task. Install them and retry.')
    raise

DATA_TYPE = 'air_quality'
TASK_NAME = 'pm25_no2_rolling_correlation'
DESCRIPTION = 'Calculate Pearson correlation between PM2.5 and NO2 over the last K readings (default K=12, require K>=6); label coupling strength as strong (|r|>=0.7), moderate (0.4–0.7), or weak.'


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def main():
    # Parse window K from argv (optional)
    K = 12
    if len(sys.argv) > 1:
        try:
            K = int(sys.argv[1])
        except Exception:
            pass
    # Enforce minimum requirement K>=6
    if K < 6:
        K = 6

    data_path = os.path.join('data', DATA_TYPE, 'raw_data.csv')
    if not os.path.exists(data_path):
        print(json.dumps({'error': f'Data file not found at {data_path}'}))
        sys.exit(1)

    df = pd.read_csv(data_path)

    # Create a unified timestamp column for sorting
    if 'timestamp_utc' in df.columns:
        df['__ts'] = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
    elif 'timestamp_unix' in df.columns:
        df['__ts'] = pd.to_datetime(df['timestamp_unix'], unit='s', errors='coerce', utc=True)
    else:
        df['__ts'] = pd.NaT

    # Validate required columns
    for col in ['pm2_5', 'no2']:
        if col not in df.columns:
            print(json.dumps({'error': f'Missing required column: {col}'}))
            sys.exit(1)

    df = df.sort_values('__ts').reset_index(drop=True)
    df_clean = df[['__ts', 'pm2_5', 'no2']].dropna()
    df_window = df_clean.tail(K)

    n = len(df_window)
    now_iso = iso_now()

    start_ts = df_window['__ts'].iloc[0].isoformat() if n > 0 else None
    end_ts = df_window['__ts'].iloc[-1].isoformat() if n > 0 else None

    result_summary = []

    if n < 6:
        result_summary.append({
            'name': 'status',
            'value': 'insufficient_data',
            'description': f'Need at least 6 paired observations; found {n}.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'sample_size_used',
            'value': n,
            'description': 'Number of valid paired observations in the analysis window.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'window_requested',
            'value': K,
            'description': 'Requested window size K.',
            'timestamp': now_iso
        })
        if start_ts and end_ts:
            result_summary.append({
                'name': 'time_range_analyzed',
                'value': f'{start_ts} to {end_ts}',
                'description': 'Time coverage of the analyzed window.',
                'timestamp': now_iso
            })
    else:
        x = df_window['pm2_5'].astype(float).values
        y = df_window['no2'].astype(float).values
        # Handle zero variance cases
        if np.std(x) == 0 or np.std(y) == 0:
            r = float('nan')
        else:
            r = float(np.corrcoef(x, y)[0, 1])

        if np.isnan(r):
            label = 'undefined'
        else:
            ar = abs(r)
            if ar >= 0.7:
                label = 'strong'
            elif ar >= 0.4:
                label = 'moderate'
            else:
                label = 'weak'

        result_summary.append({
            'name': 'correlation_coefficient',
            'value': None if np.isnan(r) else round(r, 4),
            'description': 'Pearson correlation r between PM2.5 and NO2 over the last K readings.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'coupling_strength_label',
            'value': label,
            'description': 'Coupling strength based on |r|: strong (>=0.7), moderate (0.4–0.7), weak (<0.4), undefined if variance is zero.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'sample_size_used',
            'value': n,
            'description': 'Number of valid paired observations in the analysis window.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'window_requested',
            'value': K,
            'description': 'Requested window size K.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'time_range_analyzed',
            'value': f'{start_ts} to {end_ts}',
            'description': 'Time coverage of the analyzed window.',
            'timestamp': now_iso
        })

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': result_summary,
        'result_generated_at': now_iso
    }

    out_dir = os.path.join('output', DATA_TYPE)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{TASK_NAME}_result.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()