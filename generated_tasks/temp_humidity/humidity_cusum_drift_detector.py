import os
import json
from datetime import datetime
import pandas as pd


def iso_now():
    return datetime.utcnow().isoformat() + 'Z'


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def read_data(data_type):
    data_path = os.path.join('data', data_type, 'raw_data.csv')
    if not os.path.isfile(data_path):
        raise FileNotFoundError(f'Input data not found at {data_path}')
    df = pd.read_csv(data_path)
    if 'timestamp' not in df.columns:
        raise ValueError('CSV must contain a timestamp column')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    if 'humidity_percent' not in df.columns:
        raise ValueError('Missing required column: humidity_percent')
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def cusum_upward(series, timestamps, k=0.5, h=3.0, baseline_points=5):
    # Determine baseline mean (mu0)
    if len(series) >= baseline_points:
        mu0 = float(series.iloc[:baseline_points].mean())
    else:
        mu0 = float(series.median())

    C = 0.0
    eps = 1e-12
    events = []
    event_active = False
    event_start_idx = None
    event_flagged = False
    peak_c = 0.0

    for i, x in enumerate(series):
        inc = float(x) - mu0 - k
        C = max(0.0, C + inc)
        # Track peak within current active region
        if C > 0 and not event_active:
            event_active = True
            event_start_idx = i
            event_flagged = False
            peak_c = C
        elif event_active:
            if C > peak_c:
                peak_c = C

        if event_active and C >= h - eps:
            event_flagged = True

        # Close event when C resets to ~0
        if event_active and C <= eps:
            # Only record as drift event if threshold breached
            if event_flagged:
                end_idx = i
                events.append({
                    'metric': 'humidity_percent',
                    'start_index': int(event_start_idx),
                    'end_index': int(end_idx),
                    'start_time': timestamps.iloc[event_start_idx].isoformat(),
                    'end_time': timestamps.iloc[end_idx].isoformat(),
                    'peak_cusum': float(peak_c),
                    'parameters': {'k': float(k), 'h': float(h), 'baseline_mu0': mu0}
                })
            # Reset
            event_active = False
            event_start_idx = None
            event_flagged = False
            peak_c = 0.0

    # Flush any active event at end of data
    if event_active and event_flagged:
        end_idx = len(series) - 1
        events.append({
            'metric': 'humidity_percent',
            'start_index': int(event_start_idx),
            'end_index': int(end_idx),
            'start_time': timestamps.iloc[event_start_idx].isoformat(),
            'end_time': timestamps.iloc[end_idx].isoformat(),
            'peak_cusum': float(peak_c),
            'parameters': {'k': float(k), 'h': float(h), 'baseline_mu0': mu0}
        })

    return events, mu0


def main():
    task_name = 'humidity_cusum_drift_detector'
    data_type = 'temp_humidity'
    description = 'Apply one-sided CUSUM to humidity_percent to flag sustained upward drift (k=0.5, h=3.0 in % units); return drift start/end times and peak CUSUM.'

    df = read_data(data_type)
    series = df['humidity_percent']
    ts = df['timestamp']

    k = 0.5
    h = 3.0
    events, mu0 = cusum_upward(series, ts, k=k, h=h, baseline_points=5)

    result_summary = []
    # Parameters summary
    result_summary.append({
        'name': 'cusum_parameters',
        'value': {'k': k, 'h': h, 'baseline_mu0': mu0},
        'description': 'CUSUM configuration and baseline mean.',
        'timestamp': iso_now()
    })

    if not events:
        result_summary.append({
            'name': 'no_drift_events',
            'value': 'none',
            'description': 'No upward humidity drift events detected (CUSUM did not cross threshold).',
            'timestamp': iso_now()
        })
    else:
        result_summary.append({
            'name': 'drift_event_count',
            'value': int(len(events)),
            'description': 'Number of upward humidity drift events detected by CUSUM.',
            'timestamp': iso_now()
        })
        for i, ev in enumerate(events, start=1):
            result_summary.append({
                'name': f'humidity_drift_event_{i}',
                'value': {
                    'start_time': ev['start_time'],
                    'end_time': ev['end_time'],
                    'peak_cusum': ev['peak_cusum'],
                    'parameters': ev['parameters']
                },
                'description': 'CUSUM upward drift event details.',
                'timestamp': ev['end_time']
            })

    result = {
        'task_name': task_name,
        'description': description,
        'result_summary': result_summary,
        'result_generated_at': iso_now()
    }

    out_dir = os.path.join('output', data_type)
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, f'{task_name}_result.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps({
        'drift_events_detected': len([e for e in result_summary if e['name'].startswith('humidity_drift_event_')]),
        'baseline_mu0': mu0,
        'output_file': out_path
    }, indent=2))


if __name__ == '__main__':
    main()