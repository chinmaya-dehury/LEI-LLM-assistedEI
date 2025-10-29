#!/usr/bin/env python3
import os
import json
import pandas as pd
from datetime import datetime, timezone

DATA_PATH = 'data/air_quality/raw_data.csv'
OUTPUT_DIR = 'output/air_quality'
TASK_NAME = 'sudden_spike_alert_pm25'
DESCRIPTION = 'Trigger a lightweight alert when PM2.5 exhibits a sudden spike between consecutive readings (e.g., >10 \u00b5g/m3 absolute or >25% relative increase).'

ABS_THRESHOLD = 10.0  # \u00b5g/m3
REL_THRESHOLD = 0.25  # 25%


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

    if 'pm2_5' not in df.columns:
        print('pm2_5 column not found in data.')
        return None

    df = df.dropna(subset=['ts', 'pm2_5']).sort_values('ts').reset_index(drop=True)
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
    if df is None or len(df) < 2:
        result['result_summary'].append({
            'name': 'data_status',
            'value': 'insufficient_data',
            'description': 'Need at least two rows to check for spikes.',
            'tiemstamp': ts_gen
        })
        out_path = os.path.join(OUTPUT_DIR, f'{TASK_NAME}_result.json')
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
        print('Insufficient data. Results saved to', out_path)
        return

    df['pm2_5'] = pd.to_numeric(df['pm2_5'], errors='coerce')
    df = df.dropna(subset=['pm2_5']).reset_index(drop=True)

    # Compute differences
    df['pm2_5_prev'] = df['pm2_5'].shift(1)
    df['abs_increase'] = df['pm2_5'] - df['pm2_5_prev']

    # Avoid division by zero for relative increase
    df['rel_increase'] = df['abs_increase'] / df['pm2_5_prev'].replace(0, float('nan'))

    # Spike criteria: absolute > 10 OR relative > 25% (and positive increase)
    spikes = df[(df['abs_increase'] > ABS_THRESHOLD) | ((df['rel_increase'] > REL_THRESHOLD) & (df['abs_increase'] > 0))]
    spikes = spikes.dropna(subset=['pm2_5_prev', 'abs_increase'])

    spike_count = int(len(spikes))

    if spike_count == 0:
        result['result_summary'].append({
            'name': 'spike_count',
            'value': 0,
            'description': 'No PM2.5 spikes detected above thresholds.',
            'tiemstamp': ts_gen
        })
    else:
        max_abs = float(spikes['abs_increase'].max())
        max_rel = float(spikes['rel_increase'].max()) if spikes['rel_increase'].notna().any() else None
        first_spike_ts = spikes['ts'].iloc[0].isoformat()
        last_spike_ts = spikes['ts'].iloc[-1].isoformat()

        result['result_summary'].append({
            'name': 'spike_count',
            'value': spike_count,
            'description': 'Number of PM2.5 spike events detected.',
            'tiemstamp': ts_gen
        })
        result['result_summary'].append({
            'name': 'max_abs_increase_ugm3',
            'value': round(max_abs, 3),
            'description': 'Maximum absolute PM2.5 increase between consecutive readings (\u00b5g/m3).',
            'tiemstamp': ts_gen
        })
        result['result_summary'].append({
            'name': 'max_rel_increase_pct',
            'value': round(max_rel * 100, 2) if max_rel is not None else None,
            'description': 'Maximum relative PM2.5 increase between consecutive readings (%).',
            'tiemstamp': ts_gen
        })
        result['result_summary'].append({
            'name': 'first_spike_at',
            'value': first_spike_ts,
            'description': 'Timestamp of first detected spike (UTC).',
            'tiemstamp': ts_gen
        })
        result['result_summary'].append({
            'name': 'last_spike_at',
            'value': last_spike_ts,
            'description': 'Timestamp of last detected spike (UTC).',
            'tiemstamp': ts_gen
        })

        # Include up to 5 preview events
        preview_rows = spikes.head(5)
        preview_list = []
        for _, r in preview_rows.iterrows():
            preview_list.append({
                't': r['ts'].isoformat(),
                'prev': round(float(r['pm2_5_prev']), 3) if pd.notna(r['pm2_5_prev']) else None,
                'curr': round(float(r['pm2_5']), 3),
                'abs_inc': round(float(r['abs_increase']), 3),
                'rel_inc_pct': round(float(r['rel_increase'] * 100), 2) if pd.notna(r['rel_increase']) else None
            })
        result['result_summary'].append({
            'name': 'spike_events_preview',
            'value': json.dumps(preview_list),
            'description': 'Up to 5 spike events with previous/current PM2.5 and increases.',
            'tiemstamp': ts_gen
        })

    out_path = os.path.join(OUTPUT_DIR, f'{TASK_NAME}_result.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Print concise summary
    print(f'{TASK_NAME} results:')
    for item in result['result_summary']:
        print(f"- {item['name']}: {item['value']}")
    print('Saved to', out_path)


if __name__ == '__main__':
    main()
