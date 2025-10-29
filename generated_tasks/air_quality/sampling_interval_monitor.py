#!/usr/bin/env python3
import os
import json
import pandas as pd
from datetime import datetime, timezone

DATA_PATH = 'data/air_quality/raw_data.csv'
OUTPUT_DIR = 'output/air_quality'
TASK_NAME = 'sampling_interval_monitor'
DESCRIPTION = 'Verify actual sampling gaps against the expected 10\u201315 minute interval; flag missing/late data and compute basic uptime metrics.'

NOMINAL_MIN = 12.5   # target interval in minutes
ON_TIME_MIN = 10.0   # lower bound of expected window
ON_TIME_MAX = 15.0   # upper bound of expected window


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def load_data():
    if not os.path.exists(DATA_PATH):
        print(f'Input file not found: {DATA_PATH}')
        return None
    df = pd.read_csv(DATA_PATH)

    if 'timestamp_utc' in df.columns:
        df['ts'] = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
    elif 'timestamp' in df.columns:
        df['ts'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
    elif 'timestamp_unix' in df.columns:
        df['ts'] = pd.to_datetime(df['timestamp_unix'], unit='s', utc=True)
    else:
        print('No timestamp column found (expected one of: timestamp_utc, timestamp, timestamp_unix).')
        return None

    df = df.dropna(subset=['ts']).sort_values('ts').reset_index(drop=True)
    return df


def main():
    ensure_dir(OUTPUT_DIR)
    ts_gen = now_iso()

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': [],
        'result_generated_at': ts_gen
    }

    df = load_data()
    if df is None or len(df) == 0:
        result['result_summary'].append({
            'name': 'data_status',
            'value': 'no_data',
            'description': 'No valid data rows available for analysis.',
            'tiemstamp': ts_gen
        })
        out_path = os.path.join(OUTPUT_DIR, f'{TASK_NAME}_result.json')
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
        print('No data. Results saved to', out_path)
        return

    # Compute gaps in minutes
    df['gap_min'] = df['ts'].diff().dt.total_seconds().div(60)

    total_readings = int(len(df))
    valid_gaps = df['gap_min'].dropna()

    on_time = int(((valid_gaps >= ON_TIME_MIN) & (valid_gaps <= ON_TIME_MAX)).sum())
    early = int(((valid_gaps > 0) & (valid_gaps < ON_TIME_MIN)).sum())
    late = int((valid_gaps > ON_TIME_MAX).sum())
    nonpositive = int((df['gap_min'] <= 0).sum())  # includes first NaN and any non-monotonic issues

    median_gap = float(valid_gaps.median()) if len(valid_gaps) > 0 else float('nan')
    worst_gap = float(valid_gaps.max()) if len(valid_gaps) > 0 else float('nan')

    # Estimate missing samples from long gaps
    est_missing = 0
    for g in valid_gaps:
        if g > NOMINAL_MIN:
            missing = int(g // NOMINAL_MIN) - 1
            if missing > 0:
                est_missing += missing

    gap_based_uptime = 100.0 * total_readings / max(1, total_readings + est_missing)

    # Span-based uptime estimation
    if total_readings > 1:
        span_min = (df['ts'].iloc[-1] - df['ts'].iloc[0]).total_seconds() / 60.0
    else:
        span_min = 0.0
    expected_readings_span = int(span_min / NOMINAL_MIN) + 1 if span_min > 0 else 1
    span_based_uptime = 100.0 * total_readings / max(1, expected_readings_span)

    def add_item(name, value, desc):
        result['result_summary'].append({
            'name': name,
            'value': value,
            'description': desc,
            'tiemstamp': ts_gen
        })

    add_item('total_readings', total_readings, 'Total number of valid sensor rows.')
    add_item('median_gap_min', round(median_gap, 3) if median_gap == median_gap else None, 'Median sampling gap in minutes.')
    add_item('on_time_gaps', on_time, 'Count of gaps within expected 10\u201315 minutes.')
    add_item('early_gaps', early, 'Count of gaps shorter than 10 minutes.')
    add_item('late_gaps', late, 'Count of gaps longer than 15 minutes.')
    add_item('nonpositive_gaps', nonpositive, 'Count of non-positive/undefined gaps (includes first row).')
    add_item('worst_gap_min', round(worst_gap, 3) if worst_gap == worst_gap else None, 'Largest observed gap in minutes.')
    add_item('estimated_missing_samples', est_missing, 'Estimated missing readings inferred from long gaps.')
    add_item('uptime_pct_gap_based', round(gap_based_uptime, 2), 'Uptime percentage based on gaps-derived missing samples.')
    add_item('uptime_pct_span_based', round(span_based_uptime, 2), 'Uptime percentage based on coverage over total time span.')

    out_path = os.path.join(OUTPUT_DIR, f'{TASK_NAME}_result.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Print concise summary
    print(f'{TASK_NAME} results:')
    print(f'- total_readings: {total_readings}')
    print(f'- median_gap_min: {round(median_gap,3) if median_gap == median_gap else None}')
    print(f'- on_time/early/late: {on_time}/{early}/{late}')
    print(f'- estimated_missing_samples: {est_missing}')
    print(f'- uptime_pct_gap_based: {round(gap_based_uptime,2)}%')
    print(f'- uptime_pct_span_based: {round(span_based_uptime,2)}%')
    print('Saved to', out_path)


if __name__ == '__main__':
    main()
