#!/usr/bin/env python3
import os
import json
from datetime import datetime, timezone

try:
    import pandas as pd
    import numpy as np
except Exception as e:
    print('Error: pandas and numpy are required to run this task. Install them and retry.')
    raise

DATA_TYPE = 'air_quality'
TASK_NAME = 'aqi_gap_fill_estimator_from_components'
DESCRIPTION = 'When aqi_uk is missing, estimate a DAQI-like band by taking the maximum ratio of pollutant concentration to WHO short-term guideline (PM2.5:15, PM10:45, NO2:25, SO2:40, O3:100, CO:4000 µg/m3): ratio<=1 Low, 1–2 Moderate, 2–4 High, >4 Very High; report dominant pollutant.'

GUIDELINES = {
    'pm2_5': 15.0,
    'pm10': 45.0,
    'no2': 25.0,
    'so2': 40.0,
    'o3': 100.0,
    'co': 4000.0
}


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def band_for_ratio(r):
    if pd.isna(r):
        return 'unknown'
    if r <= 1:
        return 'Low'
    if r <= 2:
        return 'Moderate'
    if r <= 4:
        return 'High'
    return 'Very High'


def main():
    data_path = os.path.join('data', DATA_TYPE, 'raw_data.csv')
    if not os.path.exists(data_path):
        print(json.dumps({'error': f'Data file not found at {data_path}'}))
        raise SystemExit(1)

    df = pd.read_csv(data_path)

    now_iso = iso_now()

    present_cols = [c for c in GUIDELINES.keys() if c in df.columns]
    if len(present_cols) == 0:
        print(json.dumps({'error': 'No pollutant component columns available for estimation.'}))
        raise SystemExit(1)

    # Prepare ratio dataframe (clip negatives to 0)
    ratios = df[present_cols].astype(float)
    for c in present_cols:
        ratios[c] = ratios[c] / GUIDELINES[c]
    ratios = ratios.clip(lower=0)

    # Determine which rows need gap-filling
    if 'aqi_uk' in df.columns:
        missing_mask = df['aqi_uk'].isna()
    else:
        # If AQI column absent, treat all rows as missing
        missing_mask = pd.Series([True] * len(df), index=df.index)

    to_estimate_idx = df.index[missing_mask].tolist()

    result_summary = []

    # Always report counts
    result_summary.append({
        'name': 'rows_total',
        'value': int(len(df)),
        'description': 'Total number of rows in the dataset.',
        'timestamp': now_iso
    })

    result_summary.append({
        'name': 'rows_with_missing_aqi',
        'value': int(missing_mask.sum()),
        'description': 'Number of rows where aqi_uk is missing and eligible for estimation.',
        'timestamp': now_iso
    })

    if len(to_estimate_idx) > 0:
        sub = ratios.loc[to_estimate_idx]
        max_ratio = sub.max(axis=1)
        dominant = sub.idxmax(axis=1)
        bands = max_ratio.apply(band_for_ratio)

        # Clean up potential all-NaN rows
        dominant = dominant.fillna('unknown')
        bands = bands.fillna('unknown')

        dist = bands.value_counts(dropna=False).to_dict()
        dist = {str(k): int(v) for k, v in dist.items()}

        dom_counts = dominant.value_counts(dropna=False).to_dict()
        dom_counts = {str(k): int(v) for k, v in dom_counts.items()}

        # Determine overall dominant pollutant among estimated rows
        if len(dom_counts) > 0:
            top_dom = max(dom_counts.items(), key=lambda kv: kv[1])[0]
        else:
            top_dom = 'unknown'

        result_summary.append({
            'name': 'rows_estimated',
            'value': int(len(to_estimate_idx)),
            'description': 'Number of rows for which DAQI-like band was estimated.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'band_distribution',
            'value': dist,
            'description': 'Distribution of estimated DAQI-like bands across gap-filled rows.',
            'timestamp': now_iso
        })
        result_summary.append({
            'name': 'dominant_pollutants_count',
            'value': dom_counts,
            'description': 'Counts of dominant pollutants among estimated rows (by max ratio to guidelines).',
            'timestamp': now_iso
        })
        # Provide details for the latest estimated row
        last_idx = to_estimate_idx[-1]
        last_band = bands.loc[last_idx]
        last_dom = dominant.loc[last_idx]
        last_ratio = float(max_ratio.loc[last_idx]) if pd.notna(max_ratio.loc[last_idx]) else None
        result_summary.append({
            'name': 'latest_estimated_row_summary',
            'value': {
                'row_index': int(last_idx),
                'band': str(last_band),
                'dominant_pollutant': str(last_dom),
                'max_ratio': None if last_ratio is None else round(last_ratio, 4)
            },
            'description': 'Summary for the most recent row where AQI was estimated from components.',
            'timestamp': now_iso
        })
    else:
        # No estimation performed; provide an informational note
        result_summary.append({
            'name': 'estimation_status',
            'value': 'no_missing_aqi_no_estimation',
            'description': 'All rows have aqi_uk present; no gap-filling performed.',
            'timestamp': now_iso
        })
        # Provide an informational components-based band for the latest row
        if len(ratios) > 0:
            last_ratios = ratios.iloc[-1]
            last_max = float(last_ratios.max()) if pd.notna(last_ratios.max()) else None
            last_dom = str(last_ratios.idxmax()) if pd.notna(last_ratios.max()) else 'unknown'
            last_band = band_for_ratio(last_max)
            result_summary.append({
                'name': 'latest_components_band_info',
                'value': {
                    'band': str(last_band),
                    'dominant_pollutant': str(last_dom),
                    'max_ratio': None if last_max is None else round(last_max, 4)
                },
                'description': 'Informational DAQI-like band from components for the latest row.',
                'timestamp': now_iso
            })

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': result_summary,
        'result_generated_at': now_iso
    }

    out_dir = os.path.join('output', DATA_TYPE)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{TASK_NAME}_result.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()