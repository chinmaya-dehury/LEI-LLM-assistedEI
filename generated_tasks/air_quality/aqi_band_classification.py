#!/usr/bin/env python3
import os
import json
from datetime import datetime, timezone
import pandas as pd

DATA_PATH = 'data/air_quality/raw_data.csv'
OUTPUT_DIR = os.path.join('output', 'air_quality')
RESULT_FILE = os.path.join(OUTPUT_DIR, 'aqi_band_classification_result.json')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def map_band_and_risk(aqi):
    if pd.isna(aqi):
        return 'Unknown', 'No AQI value.'
    try:
        aqi = float(aqi)
    except Exception:
        return 'Unknown', 'Invalid AQI value.'
    if 1 <= aqi <= 3:
        return 'Low', 'Low risk: Enjoy normal activities.'
    elif 4 <= aqi <= 6:
        return 'Moderate', 'Moderate risk: Sensitive groups reduce prolonged exertion.'
    elif 7 <= aqi <= 9:
        return 'High', 'High risk: Reduce prolonged outdoor exertion; sensitive groups avoid.'
    elif aqi == 10:
        return 'Very High', 'Very high risk: Everyone should reduce outdoor activities.'
    else:
        return 'Unknown', 'AQI out of expected 1–10 range.'


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(DATA_PATH):
        print(f'Input file not found: {DATA_PATH}')
        result = {
            'task_name': 'aqi_band_classification',
            'description': 'Map aqi_uk to UK DAQI bands and attach a simple risk label.',
            'result_summary': [
                {'name': 'error', 'value': f'Input file not found: {DATA_PATH}', 'description': 'Cannot proceed', 'tiemstamp': now_iso()}
            ],
            'result_generated_at': now_iso()
        }
        with open(RESULT_FILE, 'w') as f:
            json.dump(result, f, indent=2)
        return

    df = pd.read_csv(DATA_PATH)
    df['aqi_uk'] = pd.to_numeric(df.get('aqi_uk'), errors='coerce')
    # Parse timestamp
    if 'timestamp_utc' in df.columns:
        ts = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
    elif 'timestamp_unix' in df.columns:
        ts = pd.to_datetime(df['timestamp_unix'], unit='s', errors='coerce', utc=True)
    else:
        ts = pd.NaT
    df['__ts'] = ts

    # Map bands & risk labels
    mapped = df['aqi_uk'].apply(lambda x: map_band_and_risk(x))
    df['band'] = mapped.apply(lambda t: t[0])
    df['risk'] = mapped.apply(lambda t: t[1])

    valid = df[df['aqi_uk'].notna()].copy()
    result_summary = []
    now = now_iso()

    total_records = int(valid.shape[0])
    result_summary.append({'name': 'total_records', 'value': total_records, 'description': 'Number of valid aqi_uk readings.', 'tiemstamp': now})

    # Counts per band
    band_order = ['Low', 'Moderate', 'High', 'Very High', 'Unknown']
    counts = df['band'].value_counts(dropna=False).to_dict()
    for b in band_order:
        c = int(counts.get(b, 0))
        desc = f'Number of readings in {b} band.'
        result_summary.append({'name': f'count_{b.lower().replace(" ", "_")}', 'value': c, 'description': desc, 'tiemstamp': now})

    # Percentages for valid readings
    if total_records > 0:
        for b in ['Low', 'Moderate', 'High', 'Very High']:
            perc = round(100.0 * counts.get(b, 0) / total_records, 2)
            result_summary.append({'name': f'percent_{b.lower().replace(" ", "_")}', 'value': perc, 'description': f'Percentage of valid readings in {b} band.', 'tiemstamp': now})

    # Worst observed band (by severity)
    severity = {'Unknown': 0, 'Low': 1, 'Moderate': 2, 'High': 3, 'Very High': 4}
    if df.shape[0] > 0:
        worst_band = max(counts.keys(), key=lambda k: severity.get(k, 0)) if counts else 'Unknown'
        result_summary.append({'name': 'worst_observed_band', 'value': worst_band, 'description': 'Worst DAQI band observed in the dataset.', 'tiemstamp': now})

    # Last observation
    df_sorted = df.sort_values('__ts')
    last_row = df_sorted.dropna(subset=['__ts']).tail(1)
    if not last_row.empty:
        last_band = last_row.iloc[0]['band']
        last_risk = last_row.iloc[0]['risk']
        last_ts = last_row.iloc[0]['__ts']
        result_summary.append({'name': 'last_observation_band', 'value': last_band, 'description': f'Band at last timestamp. Risk: {last_risk}', 'tiemstamp': pd.to_datetime(last_ts).isoformat()})
        result_summary.append({'name': 'last_observation_aqi_uk', 'value': float(last_row.iloc[0]['aqi_uk']) if pd.notna(last_row.iloc[0]['aqi_uk']) else None, 'description': 'Latest aqi_uk value.', 'tiemstamp': pd.to_datetime(last_ts).isoformat()})

    # Time coverage
    if df['__ts'].notna().any():
        start_ts = df['__ts'].min()
        end_ts = df['__ts'].max()
        value = {
            'start_utc': pd.to_datetime(start_ts).isoformat() if pd.notna(start_ts) else None,
            'end_utc': pd.to_datetime(end_ts).isoformat() if pd.notna(end_ts) else None
        }
        result_summary.append({'name': 'time_range_utc', 'value': value, 'description': 'Time coverage of the dataset.', 'tiemstamp': now})

    result = {
        'task_name': 'aqi_band_classification',
        'description': 'Map aqi_uk (1–10) to UK DAQI bands (Low:1–3, Moderate:4–6, High:7–9, Very High:10) and attach a simple risk label.',
        'result_summary': result_summary,
        'result_generated_at': now
    }

    print('AQI Band Classification Summary:')
    for item in result_summary:
        print(f"- {item['name']}: {item['value']}")

    with open(RESULT_FILE, 'w') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    main()
