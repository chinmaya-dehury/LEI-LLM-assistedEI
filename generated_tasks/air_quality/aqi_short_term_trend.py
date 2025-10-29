#!/usr/bin/env python3
import os
import json
from datetime import datetime, timezone
import pandas as pd
import math

DATA_PATH = 'data/air_quality/raw_data.csv'
OUTPUT_DIR = os.path.join('output', 'air_quality')
RESULT_FILE = os.path.join(OUTPUT_DIR, 'aqi_short_term_trend_result.json')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def compute_trend_label(delta, threshold=0.3):
    if delta is None or isinstance(delta, float) and math.isnan(delta):
        return 'unknown'
    if abs(delta) <= threshold:
        return 'steady'
    return 'rising' if delta > 0 else 'falling'


def slope_per_hour(timestamps, values):
    # timestamps: pandas Series datetime64[ns, UTC], values: Series floats
    if len(values) < 2:
        return None
    x = pd.to_datetime(timestamps).astype('int64') / 1e9  # seconds since epoch
    xh = (x - x.mean()) / 3600.0
    y = pd.to_numeric(values, errors='coerce')
    xm2 = ((xh) ** 2).sum()
    if xm2 == 0 or y.isna().all():
        return None
    cov = (xh * (y - y.mean())).sum()
    return float(cov / xm2)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = now_iso()

    if not os.path.exists(DATA_PATH):
        result = {
            'task_name': 'aqi_short_term_trend',
            'description': 'Compute a short-term trend on aqi_uk using a lightweight last-value vs previous-mean comparison.',
            'result_summary': [
                {'name': 'error', 'value': f'Input file not found: {DATA_PATH}', 'description': 'Cannot compute trend.', 'tiemstamp': now}
            ],
            'result_generated_at': now
        }
        print(result['result_summary'][0]['value'])
        with open(RESULT_FILE, 'w') as f:
            json.dump(result, f, indent=2)
        return

    df = pd.read_csv(DATA_PATH)
    df['aqi_uk'] = pd.to_numeric(df.get('aqi_uk'), errors='coerce')
    if 'timestamp_utc' in df.columns:
        df['__ts'] = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
    elif 'timestamp_unix' in df.columns:
        df['__ts'] = pd.to_datetime(df['timestamp_unix'], unit='s', errors='coerce', utc=True)
    else:
        df['__ts'] = pd.NaT

    valid = df.dropna(subset=['aqi_uk', '__ts']).sort_values('__ts').reset_index(drop=True)

    result_summary = []

    if len(valid) == 0:
        result_summary.append({'name': 'status', 'value': 'no_valid_data', 'description': 'No valid aqi_uk/timestamp rows.', 'tiemstamp': now})
    else:
        window = valid.tail(3)
        last_value = float(window.iloc[-1]['aqi_uk'])
        last_ts = window.iloc[-1]['__ts']
        if len(window) >= 2:
            prev_mean = float(window.iloc[:-1]['aqi_uk'].mean())
            delta = round(last_value - prev_mean, 3)
            base = prev_mean if abs(prev_mean) > 1e-9 else float('nan')
            pct = round((delta / base) * 100.0, 2) if not (isinstance(base, float) and math.isnan(base)) else None
            label = compute_trend_label(delta, threshold=0.3)

            # Time span in minutes
            try:
                tspan_min = round(float((window.iloc[-1]['__ts'] - window.iloc[0]['__ts']).total_seconds()) / 60.0, 2)
            except Exception:
                tspan_min = None

            sph = slope_per_hour(window['__ts'], window['aqi_uk'])
            if sph is not None:
                sph = round(sph, 3)

            last_ts_iso = pd.to_datetime(last_ts).isoformat()
            result_summary.append({'name': 'short_term_trend_label', 'value': label, 'description': 'Trend based on last value vs mean of previous values in window. Threshold=0.3 AQI units.', 'tiemstamp': last_ts_iso})
            result_summary.append({'name': 'last_value', 'value': last_value, 'description': 'Latest aqi_uk value.', 'tiemstamp': last_ts_iso})
            result_summary.append({'name': 'previous_mean', 'value': prev_mean, 'description': 'Mean of previous values in the short window.', 'tiemstamp': last_ts_iso})
            result_summary.append({'name': 'delta', 'value': delta, 'description': 'Difference = last_value - previous_mean.', 'tiemstamp': last_ts_iso})
            result_summary.append({'name': 'percent_change', 'value': pct, 'description': 'Percent change relative to previous_mean.', 'tiemstamp': last_ts_iso})
            result_summary.append({'name': 'window_span_minutes', 'value': tspan_min, 'description': 'Time span covered by the short-term window.', 'tiemstamp': last_ts_iso})
            result_summary.append({'name': 'slope_per_hour', 'value': sph, 'description': 'Estimated linear slope across window (AQI units per hour).', 'tiemstamp': last_ts_iso})
        else:
            result_summary.append({'name': 'status', 'value': 'insufficient_data', 'description': 'At least 2 readings required to compute trend.', 'tiemstamp': pd.to_datetime(valid.iloc[-1]['__ts']).isoformat()})

        # Rolling trend counts across entire series (3-point windows)
        rising = falling = steady = 0
        if len(valid) >= 3:
            for i in range(2, len(valid)):
                prev2 = valid.iloc[i-2:i]['aqi_uk']
                lastv = float(valid.iloc[i]['aqi_uk'])
                pm = float(prev2.mean())
                d = lastv - pm
                lbl = compute_trend_label(d, threshold=0.3)
                if lbl == 'rising':
                    rising += 1
                elif lbl == 'falling':
                    falling += 1
                elif lbl == 'steady':
                    steady += 1
            agg_ts = pd.to_datetime(valid.iloc[-1]['__ts']).isoformat()
            result_summary.append({'name': 'rolling_rising_windows', 'value': rising, 'description': 'Count of rising 3-point windows across series.', 'tiemstamp': agg_ts})
            result_summary.append({'name': 'rolling_falling_windows', 'value': falling, 'description': 'Count of falling 3-point windows across series.', 'tiemstamp': agg_ts})
            result_summary.append({'name': 'rolling_steady_windows', 'value': steady, 'description': 'Count of steady 3-point windows across series.', 'tiemstamp': agg_ts})

    result = {
        'task_name': 'aqi_short_term_trend',
        'description': 'Compute a short-term trend on aqi_uk using a lightweight 3-point slope or last-value vs previous-mean comparison and label as rising/falling/steady.',
        'result_summary': result_summary,
        'result_generated_at': now
    }

    print('AQI Short-Term Trend Summary:')
    for item in result_summary:
        print(f"- {item['name']}: {item['value']}")

    with open(RESULT_FILE, 'w') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    main()
