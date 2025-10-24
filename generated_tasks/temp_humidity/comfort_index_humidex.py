#!/usr/bin/env python3
import os
import sys
import math
import numpy as np
import pandas as pd


def compute_humidex(temp_c, rh_percent):
    # Vapor pressure approximation (Magnus formula), e in hPa
    e = (rh_percent / 100.0) * 6.112 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    # Humidex formula: H = T + (5/9)*(e - 10)
    h = temp_c + (5.0 / 9.0) * (e - 10.0)
    return h


def category(h):
    if h < 30:
        return 'comfortable'
    elif h < 40:
        return 'some discomfort'
    elif h < 45:
        return 'great discomfort'
    else:
        return 'dangerous'


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
    for c in required_cols:
        if c not in df.columns:
            print('ERROR: Missing required column:', c)
            sys.exit(1)

    # Parse types
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['temperature_c'] = pd.to_numeric(df['temperature_c'], errors='coerce')
    df['humidity_percent'] = pd.to_numeric(df['humidity_percent'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=required_cols).reset_index(drop=True)
    if df.empty:
        print('No valid rows to compute Humidex.')
        sys.exit(0)

    # Compute Humidex
    df['humidex'] = compute_humidex(df['temperature_c'].values, df['humidity_percent'].values)
    df['comfort_category'] = df['humidex'].apply(category)

    # Summary
    h_min = float(df['humidex'].min())
    h_mean = float(df['humidex'].mean())
    h_max = float(df['humidex'].max())

    counts = df['comfort_category'].value_counts().to_dict()

    # Latest reading
    dft = df.sort_values('timestamp')
    last = dft.iloc[-1]

    print('=== Humidex Comfort Report ===')
    print(f"Rows computed: {len(df)}")
    print(f"Time range: {dft['timestamp'].iloc[0]} to {dft['timestamp'].iloc[-1]}")
    print('Humidex stats (min/mean/max): {:.1f} / {:.1f} / {:.1f}'.format(h_min, h_mean, h_max))
    print('Category counts:', {k: int(v) for k, v in counts.items()})
    print('Latest reading:')
    print('  Timestamp:', last['timestamp'])
    print('  Temp (C):', round(float(last['temperature_c']), 1))
    print('  RH (%):', round(float(last['humidity_percent']), 1))
    print('  Humidex:', round(float(last['humidex']), 1))
    print('  Comfort category:', last['comfort_category'])

    # Optional: list timestamps where comfort is not "comfortable"
    non_ok = dft[dft['comfort_category'] != 'comfortable']
    if not non_ok.empty:
        print('Periods with discomfort:')
        for _, r in non_ok.iterrows():
            print('  {} -> Humidex {:.1f} ({})'.format(r['timestamp'], r['humidex'], r['comfort_category']))


if __name__ == '__main__':
    main()
