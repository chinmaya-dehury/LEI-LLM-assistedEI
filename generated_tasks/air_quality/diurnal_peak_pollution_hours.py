import os
import json
from datetime import datetime, timezone
import pandas as pd

DATA_FILE = 'data/air_quality/raw_data.csv'
OUTPUT_DIR = 'output/air_quality'
TASK_NAME = 'diurnal_peak_pollution_hours'
DESCRIPTION = 'Aggregate by hour-of-day over the last 24–48 hours and report the peak hour for PM2.5 and O3 (handles sparse data gracefully).'


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_output_dir(path):
    os.makedirs(path, exist_ok=True)


def load_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f'Input CSV not found at {path}')
    df = pd.read_csv(path)
    # Unify timestamp column name
    ts_col = None
    for cand in ['timestamp_utc', 'timestamp', 'time', 'datetime']:
        if cand in df.columns:
            ts_col = cand
            break
    if ts_col is None:
        raise ValueError('No timestamp column found (expected one of timestamp_utc, timestamp, time, datetime)')
    df['timestamp'] = pd.to_datetime(df[ts_col], errors='coerce')
    df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    # Ensure pollutant columns exist (create if missing to avoid KeyError)
    for c in ['pm2_5', 'o3']:
        if c not in df.columns:
            df[c] = pd.NA
        else:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def select_window(df):
    # Try last 24h, else 48h, else full dataset
    if df.empty:
        return df.copy(), 'no_data', 0
    latest = df['timestamp'].max()
    for hours in [24, 48]:
        cutoff = latest - pd.Timedelta(hours=hours)
        dfx = df[df['timestamp'] >= cutoff]
        if len(dfx) >= 3:  # minimal sample count to be somewhat meaningful
            return dfx.copy(), f'{hours}h', hours
    return df.copy(), 'full_data', None


def pick_peak_hour(dfw, col):
    if dfw[col].dropna().empty:
        return None
    tmp = dfw.copy()
    tmp['hour'] = tmp['timestamp'].dt.hour
    agg_median = tmp.groupby('hour')[col].median()
    agg_count = tmp.groupby('hour')[col].count()
    df_agg = pd.DataFrame({'median': agg_median, 'n': agg_count}).dropna(subset=['median'])
    if df_agg.empty:
        return None
    # Sort by highest median, then by most samples, then by earliest hour
    df_agg_sorted = df_agg.sort_values(by=['median', 'n',], ascending=[False, False])
    peak_hour = int(df_agg_sorted.index[0])
    peak_val = float(df_agg_sorted.iloc[0]['median'])
    peak_n = int(df_agg_sorted.iloc[0]['n'])
    coverage_hours = int((tmp['hour'].nunique()))
    samples = int(tmp[col].notna().sum())
    return {
        'hour': peak_hour,
        'median_value': round(peak_val, 3),
        'n_samples_at_peak_hour': peak_n,
        'unique_hours_observed': coverage_hours,
        'total_samples_in_window': samples,
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
        dfw, window_label, window_hours = select_window(df)

        # Base info
        base_info = {
            'name': 'data_window',
            'value': {
                'window_used': window_label,
                'row_count_in_window': int(len(dfw)),
                'first_timestamp': dfw['timestamp'].min().isoformat() if not dfw.empty else None,
                'last_timestamp': dfw['timestamp'].max().isoformat() if not dfw.empty else None,
            },
            'description': 'Time window used for diurnal aggregation and basic coverage.',
            'tiemstamp': iso_now(),
        }
        result['result_summary'].append(base_info)

        # PM2.5 peak hour
        pm25_peak = pick_peak_hour(dfw, 'pm2_5')
        if pm25_peak is None:
            result['result_summary'].append({
                'name': 'peak_hour_pm2_5',
                'value': None,
                'description': 'Insufficient PM2.5 data to determine peak hour.',
                'tiemstamp': iso_now(),
            })
        else:
            result['result_summary'].append({
                'name': 'peak_hour_pm2_5',
                'value': pm25_peak,
                'description': 'Hour-of-day with highest median PM2.5 over the selected window.',
                'tiemstamp': iso_now(),
            })

        # O3 peak hour
        o3_peak = pick_peak_hour(dfw, 'o3')
        if o3_peak is None:
            result['result_summary'].append({
                'name': 'peak_hour_o3',
                'value': None,
                'description': 'Insufficient O3 data to determine peak hour.',
                'tiemstamp': iso_now(),
            })
        else:
            result['result_summary'].append({
                'name': 'peak_hour_o3',
                'value': o3_peak,
                'description': 'Hour-of-day with highest median O3 over the selected window.',
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
