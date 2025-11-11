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
    # Ensure required columns
    for col in ['temperature_c', 'humidity_percent']:
        if col not in df.columns:
            raise ValueError(f'Missing required column: {col}')
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def detect_ramps(df, value_col, diff_threshold, min_steps, metric_name):
    # Compute step-wise differences
    diffs = df[value_col].diff()
    mask = diffs >= diff_threshold

    events = []
    in_run = False
    run_len = 0
    start_read_idx = None

    for i in range(1, len(df)):
        if bool(mask.iloc[i]):
            if not in_run:
                in_run = True
                start_read_idx = i - 1  # event starts at previous reading
                run_len = 1
            else:
                run_len += 1
        else:
            if in_run:
                if run_len >= min_steps:
                    end_read_idx = i - 1
                    events.append({
                        'metric': metric_name,
                        'start_index': int(start_read_idx),
                        'end_index': int(end_read_idx),
                        'start_time': df['timestamp'].iloc[start_read_idx].isoformat(),
                        'end_time': df['timestamp'].iloc[end_read_idx].isoformat(),
                        'steps': int(run_len),
                        'total_change': float(df[value_col].iloc[end_read_idx] - df[value_col].iloc[start_read_idx])
                    })
                # reset
                in_run = False
                run_len = 0
                start_read_idx = None
    # Flush at end
    if in_run and run_len >= min_steps:
        end_read_idx = len(df) - 1
        events.append({
            'metric': metric_name,
            'start_index': int(start_read_idx),
            'end_index': int(end_read_idx),
            'start_time': df['timestamp'].iloc[start_read_idx].isoformat(),
            'end_time': df['timestamp'].iloc[end_read_idx].isoformat(),
            'steps': int(run_len),
            'total_change': float(df[value_col].iloc[end_read_idx] - df[value_col].iloc[start_read_idx])
        })

    return events


def main():
    task_name = 'monotonic_ramp_event_detector'
    data_type = 'temp_humidity'
    description = 'Detect monotonic ramp events where temperature_c increases by \u22650.2\u00b0C per step for \u22653 consecutive readings or humidity_percent increases by \u22651.0% per step; output start/end timestamps and total change.'

    df = read_data(data_type)

    temp_events = detect_ramps(df, 'temperature_c', diff_threshold=0.2, min_steps=3, metric_name='temperature_c')
    humid_events = detect_ramps(df, 'humidity_percent', diff_threshold=1.0, min_steps=3, metric_name='humidity_percent')

    all_events = temp_events + humid_events
    all_events_sorted = sorted(all_events, key=lambda e: e['start_time'])

    # Prepare results
    result_summary = []
    if not all_events_sorted:
        result_summary.append({
            'name': 'no_ramp_events',
            'value': 'none',
            'description': 'No monotonic ramp events detected for configured thresholds.',
            'timestamp': iso_now()
        })
    else:
        # Add counts per metric
        result_summary.append({
            'name': 'temperature_ramp_event_count',
            'value': int(len(temp_events)),
            'description': 'Number of temperature monotonic ramp events detected.',
            'timestamp': iso_now()
        })
        result_summary.append({
            'name': 'humidity_ramp_event_count',
            'value': int(len(humid_events)),
            'description': 'Number of humidity monotonic ramp events detected.',
            'timestamp': iso_now()
        })
        # Append each event
        for idx, ev in enumerate(all_events_sorted, start=1):
            result_summary.append({
                'name': f"{ev['metric']}_ramp_event_{idx}",
                'value': {
                    'metric': ev['metric'],
                    'start_time': ev['start_time'],
                    'end_time': ev['end_time'],
                    'steps': ev['steps'],
                    'total_change': ev['total_change']
                },
                'description': 'Monotonic ramp event details.',
                'timestamp': ev['end_time']
            })

    result = {
        'task_name': task_name,
        'description': description,
        'result_summary': result_summary,
        'result_generated_at': iso_now()
    }

    # Output
    out_dir = os.path.join('output', data_type)
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, f'{task_name}_result.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps({
        'events_detected': len(all_events_sorted),
        'output_file': out_path,
        'sample_events': all_events_sorted[:3]
    }, indent=2))


if __name__ == '__main__':
    main()