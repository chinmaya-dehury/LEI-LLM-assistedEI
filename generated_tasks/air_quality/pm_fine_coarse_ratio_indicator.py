#!/usr/bin/env python3
import os
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np

def iso_z(ts):
    if pd.isna(ts):
        return None
    if isinstance(ts, pd.Timestamp):
        ts = ts.tz_convert('UTC') if ts.tzinfo is not None else ts.tz_localize('UTC')
        return ts.strftime('%Y-%m-%dT%H:%M:%SZ')
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return str(ts)

def classify_ratio(r):
    if pd.isna(r) or r < 0:
        return 'insufficient_data'
    if r > 0.6:
        return 'fine/combustion'
    if r >= 0.3:
        return 'mixed'
    return 'coarse dust'

def main():
    data_file = 'data/air_quality/raw_data.csv'
    output_dir = 'output/air_quality'
    os.makedirs(output_dir, exist_ok=True)
    result_path = os.path.join(output_dir, 'pm_fine_coarse_ratio_indicator_result.json')

    try:
        df = pd.read_csv(data_file)
    except FileNotFoundError:
        print(f'Input file not found: {data_file}')
        return

    # Parse timestamp
    ts_col = None
    for c in ['timestamp_utc', 'timestamp']:
        if c in df.columns:
            ts_col = c
            break
    if ts_col is None and 'timestamp_unix' in df.columns:
        df['__ts'] = pd.to_datetime(df['timestamp_unix'], unit='s', utc=True)
    elif ts_col is not None:
        df['__ts'] = pd.to_datetime(df[ts_col], errors='coerce', utc=True)
    else:
        now = datetime.now(timezone.utc)
        df['__ts'] = pd.Series([now] * len(df))

    # Compute ratio
    if 'pm2_5' not in df.columns or 'pm10' not in df.columns:
        print('Required columns pm2_5 and/or pm10 not found.')
        return

    pm25 = pd.to_numeric(df['pm2_5'], errors='coerce')
    pm10 = pd.to_numeric(df['pm10'], errors='coerce')

    ratio = pm25 / pm10.replace(0, np.nan)
    classification = ratio.apply(classify_ratio)

    result_summary = []
    counts = classification.value_counts(dropna=False).to_dict()

    for i in range(len(df)):
        r = ratio.iloc[i]
        cls = classification.iloc[i]
        ts_iso = iso_z(df.loc[i, '__ts'])
        val = None if pd.isna(r) else float(r)
        desc = f'Source mix classification: {cls}'
        result_summary.append({
            'name': 'pm_fine_coarse_ratio',
            'value': val,
            'description': desc,
            'tiemstamp': ts_iso
        })

    # Add a compact aggregate summary entry
    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    agg_desc = 'Counts by class: ' + ', '.join([f"{k}={v}" for k, v in counts.items()])
    result_summary.append({
        'name': 'aggregate_class_counts',
        'value': counts,
        'description': agg_desc,
        'tiemstamp': now_iso
    })

    result = {
        'task_name': 'pm_fine_coarse_ratio_indicator',
        'description': 'Compute PM2.5/PM10 ratio and classify likely particle source mix: >0.6 (fine/combustion), 0.3–0.6 (mixed), <0.3 (coarse dust).',
        'result_summary': result_summary,
        'result_generated_at': now_iso
    }

    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'Saved results to {result_path}')
    print(agg_desc)

if __name__ == '__main__':
    main()
