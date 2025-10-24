#!/usr/bin/env python3
import os
import sys
import pandas as pd
import numpy as np


def main():
    path = 'data/temp_humidity/raw_data.csv'
    if not os.path.exists(path):
        print(f'ERROR: File not found: {path}')
        sys.exit(1)

    try:
        df = pd.read_csv(path)
    except Exception as e:
        print('ERROR: Failed to read CSV:', e)
        sys.exit(1)

    required_cols = ['timestamp', 'temperature_c', 'humidity_percent']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        print('ERROR: Missing required columns:', missing_cols)
        sys.exit(1)

    # Parse and enforce types
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['temperature_c'] = pd.to_numeric(df['temperature_c'], errors='coerce').astype('float64')
    df['humidity_percent'] = pd.to_numeric(df['humidity_percent'], errors='coerce').astype('float64')

    # Basic stats and NaN checks
    null_counts = df[required_cols].isna().sum()
    total_rows = len(df)

    # Range validation (from metadata)
    temp_range = (15.0, 40.0)
    rh_range = (20.0, 100.0)
    out_of_range_temp = (~df['temperature_c'].between(temp_range[0], temp_range[1], inclusive='both')).sum()
    out_of_range_rh = (~df['humidity_percent'].between(rh_range[0], rh_range[1], inclusive='both')).sum()

    # Time order and interval checks
    dft = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    is_monotonic = dft['timestamp'].is_monotonic_increasing if len(dft) > 0 else True
    duplicate_ts = dft['timestamp'].duplicated().sum() if len(dft) > 0 else 0

    gaps = []
    non5_count = 0
    if len(dft) >= 2:
        diffs_min = dft['timestamp'].diff().dropna().dt.total_seconds().div(60)
        non5 = diffs_min[diffs_min != 5]
        non5_count = int(non5.size)
        if non5_count:
            # Collect up to first 5 offending gaps
            idxs = list(non5.index[:5])
            for i in idxs:
                gaps.append({
                    'from': str(dft.loc[i - 1, 'timestamp']),
                    'to': str(dft.loc[i, 'timestamp']),
                    'gap_min': float(diffs_min.loc[i])
                })
    else:
        print('WARNING: Not enough rows to verify 5-minute intervals.')

    # Print report
    print('=== CSV Schema & Interval Validation Report ===')
    print(f'File: {path}')
    print(f'Rows: {total_rows}')
    if len(dft) > 0:
        print(f'Time range: {dft["timestamp"].iloc[0]} to {dft["timestamp"].iloc[-1]}')
    # Convert null_counts to plain ints for readability
    null_counts_dict = {k: int(v) for k, v in null_counts.items()}
    print('Null counts:', null_counts_dict)
    print(f'Out-of-range temperature rows: {int(out_of_range_temp)} (expected 15-40 C)')
    print(f'Out-of-range humidity rows: {int(out_of_range_rh)} (expected 20-100 %)')
    print(f'Timestamps monotonic increasing: {bool(is_monotonic)}')
    print(f'Duplicate timestamps: {int(duplicate_ts)}')
    print(f'Non-5-minute gaps: {int(non5_count)}')
    if gaps:
        print('Examples of non-5-minute gaps (up to 5):')
        for g in gaps:
            print(f"  {g['from']} -> {g['to']}: {g['gap_min']} min")

    all_ok = (
        (not missing_cols)
        and (int(null_counts.sum()) == 0)
        and (int(out_of_range_temp) == 0)
        and (int(out_of_range_rh) == 0)
        and bool(is_monotonic)
        and (int(duplicate_ts) == 0)
        and (int(non5_count) == 0)
    )
    print('Result:', 'VALIDATION PASSED' if all_ok else 'VALIDATION COMPLETED WITH WARNINGS/ERRORS')


if __name__ == '__main__':
    main()
