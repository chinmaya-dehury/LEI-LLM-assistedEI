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

def main():
    data_file = 'data/air_quality/raw_data.csv'
    output_dir = 'output/air_quality'
    os.makedirs(output_dir, exist_ok=True)
    result_path = os.path.join(output_dir, 'dominant_pollutant_exceedance_result.json')

    # Read data
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

    # WHO 2021 short-term guideline limits in ug/m3
    guidelines = {
        'pm2_5': 15.0,
        'pm10': 45.0,
        'no2': 25.0,
        'so2': 40.0,
        'o3': 100.0,
        'co': 4000.0
    }
    # Ensure required columns exist
    pollutant_cols = [c for c in ['pm2_5', 'pm10', 'no2', 'so2', 'o3', 'co'] if c in df.columns]
    if not pollutant_cols:
        print('No pollutant columns found. Expected any of pm2_5, pm10, no2, so2, o3, co')
        return

    # Compute exceedance ratios
    limits = pd.Series({k: v for k, v in guidelines.items() if k in pollutant_cols})
    ratio_df = df[pollutant_cols].apply(pd.to_numeric, errors='coerce').divide(limits, axis=1)

    # Identify dominant pollutant per timestamp
    dominant = ratio_df.idxmax(axis=1)
    max_ratio = ratio_df.max(axis=1)
    status = np.where(max_ratio > 1.0, 'exceedance', 'within_guideline')

    pretty_names = {
         'pm2_5': 'PM2.5',
         'pm10': 'PM10',
         'no2': 'NO2',
         'so2': 'SO2',
         'o3': 'O3',
         'co': 'CO'
    }

    result_summary = []
    exceed_count = 0
    for i in range(len(df)):
        ts_iso = iso_z(df.loc[i, '__ts'])
        dom = dominant.iloc[i] if pd.notna(dominant.iloc[i]) else None
        mr = float(max_ratio.iloc[i]) if pd.notna(max_ratio.iloc[i]) else None
        st = status[i] if dom is not None else 'insufficient_data'
        if st == 'exceedance':
            exceed_count += 1
        val = pretty_names.get(dom, str(dom)) if dom is not None else 'N/A'
        desc = f'Dominant pollutant by exceedance ratio; status={st}; ratio={mr:.3f}' if mr is not None else 'Insufficient data to compute exceedance ratio'
        result_summary.append({
            'name': 'dominant_pollutant',
            'value': val,
            'description': desc,
            'tiemstamp': ts_iso
        })

    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    result = {
        'task_name': 'dominant_pollutant_exceedance',
        'description': 'Calculate exceedance ratios against WHO 2021 short-term guidelines (e.g., PM2.5:15, PM10:45, NO2:25, SO2:40, O3:100, CO:4000 ug/m3) and identify the dominant pollutant per timestamp.',
        'result_summary': result_summary,
        'result_generated_at': now_iso
    }

    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    total = len(result_summary)
    print(f'Saved results to {result_path}')
    print(f'Total records: {total}; Exceedances: {exceed_count}; Within guideline: {total - exceed_count}')

if __name__ == '__main__':
    main()
