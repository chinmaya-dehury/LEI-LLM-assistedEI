import os
import json
from datetime import datetime, timezone
import pandas as pd

DATA_FILE = 'data/air_quality/raw_data.csv'
OUTPUT_DIR = 'output/air_quality'
TASK_NAME = 'duplicate_and_stuck_reading_check'
DESCRIPTION = 'Detect duplicate rows (identical timestamps/components) and stuck sensors (unchanged readings across N intervals) and report counts and percentages.'
N_CONSECUTIVE_INTERVALS = 3  # number of consecutive intervals with unchanged values to flag as stuck


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_output_dir(path):
    os.makedirs(path, exist_ok=True)


def load_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f'Input CSV not found at {path}')
    df = pd.read_csv(path)
    # Find timestamp column
    ts_col = None
    for cand in ['timestamp_utc', 'timestamp', 'time', 'datetime']:
        if cand in df.columns:
            ts_col = cand
            break
    if ts_col is None:
        raise ValueError('No timestamp column found (expected one of timestamp_utc, timestamp, time, datetime)')
    df['timestamp'] = pd.to_datetime(df[ts_col], errors='coerce')
    df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    # Convert numeric columns
    for c in ['aqi_uk', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def detect_duplicates(df):
    subset_cols = [c for c in ['timestamp_utc', 'timestamp', 'lat', 'lon', 'aqi_uk', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3'] if c in df.columns]
    # Prefer using the original timestamp column if available
    if 'timestamp_utc' in df.columns:
        key_ts = 'timestamp_utc'
    elif 'timestamp' in df.columns:
        key_ts = 'timestamp'
    else:
        key_ts = subset_cols[0]
    # Build subset with key timestamp and components
    subset = [c for c in subset_cols if c in ['lat','lon','aqi_uk','co','no','no2','o3','so2','pm2_5','pm10','nh3', key_ts]]
    dup_mask = df.duplicated(subset=subset, keep=False)
    dup_rows = int(dup_mask.sum())
    total = int(len(df))
    dup_pct = (dup_rows / total * 100.0) if total > 0 else 0.0
    dup_groups = int(df[dup_mask].drop_duplicates(subset=subset).shape[0])
    return {
        'duplicate_rows': dup_rows,
        'duplicate_percentage': round(dup_pct, 3),
        'duplicate_groups': dup_groups,
        'total_rows': total,
        'subset_used_for_detection': subset,
    }


def stuck_runs_stats(series, n_intervals=N_CONSECUTIVE_INTERVALS):
    s = series.copy()
    s = s.reset_index(drop=True)
    # Create group ids where value changes
    change = (s != s.shift(1))
    group_id = change.cumsum()
    run_lengths = s.groupby(group_id).size()
    # Exclude NaN-only groups from consideration
    # Identify groups where all values are NaN
    grp_non_null_counts = s.groupby(group_id).apply(lambda x: x.notna().sum())
    valid_runs = run_lengths[grp_non_null_counts > 0]
    if valid_runs.empty:
        return {'stuck_sequences': 0, 'points_in_stuck_runs': 0, 'max_stuck_run_length': 0, 'percent_points_in_stuck_runs': 0.0}
    threshold = n_intervals + 1  # N intervals => N+1 identical points
    stuck = valid_runs[valid_runs >= threshold]
    sequences = int(stuck.shape[0])
    points = int(stuck.sum()) if sequences > 0 else 0
    max_run = int(stuck.max()) if sequences > 0 else 0
    denom = int(s.notna().sum()) if int(s.notna().sum()) > 0 else 0
    pct = (points / denom * 100.0) if denom > 0 else 0.0
    return {
        'stuck_sequences': sequences,
        'points_in_stuck_runs': points,
        'max_stuck_run_length': max_run,
        'percent_points_in_stuck_runs': round(pct, 3),
    }


def main():
    ensure_output_dir(OUTPUT_DIR)
    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': [],
        'result_generated_at': iso_now(),
    }

    try:
        df = load_data(DATA_FILE)
        # Duplicate detection
        dup_info = detect_duplicates(df)
        result['result_summary'].append({
            'name': 'duplicate_rows_overview',
            'value': dup_info,
            'description': 'Count and percentage of duplicate rows (identical timestamp and component values).',
            'tiemstamp': iso_now(),
        })

        # Stuck sensor detection per component
        comp_cols = [c for c in ['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3', 'aqi_uk'] if c in df.columns]
        stuck_overview = {'stuck_components_detected': 0, 'components_evaluated': len(comp_cols), 'n_intervals_threshold': N_CONSECUTIVE_INTERVALS}
        for c in comp_cols:
            stats = stuck_runs_stats(df.sort_values('timestamp')[c])
            if stats['stuck_sequences'] > 0:
                stuck_overview['stuck_components_detected'] += 1
                result['result_summary'].append({
                    'name': f'stuck_runs_{c}',
                    'value': stats,
                    'description': f'Stuck run statistics for {c} (unchanged across ≥ {N_CONSECUTIVE_INTERVALS} intervals).',
                    'tiemstamp': iso_now(),
                })
        result['result_summary'].append({
            'name': 'stuck_runs_overview',
            'value': stuck_overview,
            'description': 'Summary across all components for stuck sensor behavior.',
            'tiemstamp': iso_now(),
        })

        # Print concise output
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Save
        out_path = os.path.join(OUTPUT_DIR, f'{TASK_NAME}_result.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    except Exception as e:
        err = {
            'task_name': TASK_NAME,
            'description': DESCRIPTION,
            'result_summary': [
                {
                    'name': 'error',
                    'value': str(e),
                    'description': 'Task execution failed.',
                    'tiemstamp': iso_now(),
                }
            ],
            'result_generated_at': iso_now(),
        }
        print(json.dumps(err, indent=2, ensure_ascii=False))
        out_path = os.path.join(OUTPUT_DIR, f'{TASK_NAME}_result.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(err, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
