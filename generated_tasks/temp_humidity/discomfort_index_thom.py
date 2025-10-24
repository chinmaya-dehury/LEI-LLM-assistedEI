import os
import sys
import pandas as pd
import numpy as np

# Thom's Discomfort Index (DI) implementation
# DI = T - 0.55 * (1 - RH) * (T - 14.5), where RH in [0,1]

def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        print(f'ERROR: File not found: {path}', file=sys.stderr)
        sys.exit(1)
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f'ERROR: Failed to read CSV: {e}', file=sys.stderr)
        sys.exit(1)

    required = {'timestamp', 'temperature_c', 'humidity_percent'}
    if not required.issubset(df.columns):
        print(f'ERROR: Missing required columns. Found {list(df.columns)}, need {sorted(required)}', file=sys.stderr)
        sys.exit(1)

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['temperature_c'] = pd.to_numeric(df['temperature_c'], errors='coerce')
    df['humidity_percent'] = pd.to_numeric(df['humidity_percent'], errors='coerce')
    df = df.dropna(subset=['timestamp', 'temperature_c', 'humidity_percent'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def thom_di(temp_c, rh_percent):
    rh = np.clip(np.asarray(rh_percent, dtype=float), 0.0, 100.0) / 100.0
    t = np.asarray(temp_c, dtype=float)
    return t - 0.55 * (1.0 - rh) * (t - 14.5)


def di_label(di_value: float) -> str:
    # Commonly used DI comfort bands
    if di_value < 21.0:
        return 'comfortable'
    elif di_value < 24.0:
        return 'slight_discomfort'
    elif di_value < 27.0:
        return 'discomfort'
    elif di_value < 29.0:
        return 'severe_discomfort'
    elif di_value < 32.0:
        return 'very_severe_discomfort'
    else:
        return 'danger'


def main():
    # Use default path; allow override with TH_DATA_PATH env var
    path = os.environ.get('TH_DATA_PATH', 'data/temp_humidity/raw_data.csv')
    df = load_data(path)

    # Compute DI and risk labels
    df['di'] = thom_di(df['temperature_c'], df['humidity_percent'])
    df['risk'] = df['di'].apply(di_label)

    # Basic range checks vs metadata
    out_of_range = df[(df['temperature_c'] < 15) | (df['temperature_c'] > 40) |
                      (df['humidity_percent'] < 20) | (df['humidity_percent'] > 100)]
    if not out_of_range.empty:
        print(f'WARNING: {len(out_of_range)} rows outside recommended ranges (temp 15-40C, RH 20-100%).', file=sys.stderr)

    n = len(df)
    if n == 0:
        print('No valid records after parsing.')
        return

    start_ts = df['timestamp'].iloc[0]
    end_ts = df['timestamp'].iloc[-1]
    latest = df.iloc[-1]

    print(f"Computed Thom's Discomfort Index for {n} records from {start_ts:%Y-%m-%d %H:%M} to {end_ts:%Y-%m-%d %H:%M}.")
    print(f"Latest: {latest['timestamp']:%Y-%m-%d %H:%M}, T={latest['temperature_c']:.1f}C, RH={latest['humidity_percent']:.1f}%, DI={latest['di']:.1f}, risk={latest['risk']}")

    # Summary counts by risk level
    order = ['comfortable', 'slight_discomfort', 'discomfort', 'severe_discomfort', 'very_severe_discomfort', 'danger']
    counts = df['risk'].value_counts().reindex(order).fillna(0).astype(int)
    print('Counts by risk level:')
    for k in order:
        print(f'  {k}: {counts.get(k, 0)}')

    # Max DI
    idxmax = df['di'].idxmax()
    rmax = df.loc[idxmax]
    print(f"Max DI {rmax['di']:.1f} at {rmax['timestamp']:%Y-%m-%d %H:%M} (T={rmax['temperature_c']:.1f}C, RH={rmax['humidity_percent']:.1f}%)")

    # Alert for high discomfort (DI >= 27)
    alert_df = df[df['di'] >= 27.0]
    if not alert_df.empty:
        print('ALERT: High discomfort periods (DI >= 27):')
        for _, r in alert_df.iterrows():
            print(f"  {r['timestamp']:%Y-%m-%d %H:%M} -> DI={r['di']:.1f}, risk={r['risk']}")
    else:
        print('No high discomfort alerts (DI >= 27).')

    # Print last 10 computed records
    print('Last 10 computed records:')
    tail = df.tail(10)
    for _, r in tail.iterrows():
        print(f"{r['timestamp']:%Y-%m-%d %H:%M}, T={r['temperature_c']:.1f}C, RH={r['humidity_percent']:.1f}%, DI={r['di']:.1f}, {r['risk']}")


if __name__ == '__main__':
    main()
