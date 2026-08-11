from datetime import datetime
"""
Task: Cross-Mote Calibration Comparison
Description: Compare simultaneous temperature and humidity readings across different motes during the same epoch to detect calibration discrepancies or faulty nodes requiring attention.
"""

# Programmatic path resolution pre-injected for reliability
import os
from pathlib import Path

_curr_dir = Path(__file__).resolve().parent
_root_dir = _curr_dir
while _root_dir.name and not (_root_dir / "data").exists():
    _parent = _root_dir.parent
    if _parent == _root_dir:
        break
    _root_dir = _parent

DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "lab-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import csv
import json
import math
import os
from pathlib import Path
from collections import defaultdict

def safe_float(value):
    if value is None:
        return None
    v = str(value).strip()
    if v == '' or v.upper() in ('NA', 'N/A', 'NULL', ''):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

def compute_mean_std(values):
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return None, None
    mean = sum(valid) / len(valid)
    variance = sum((x - mean) ** 2 for x in valid) / len(valid)
    std = math.sqrt(variance)
    return mean, std

def main():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = root_dir / "data" / "lab-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "lab-data" / "raw_data.txt"
    if not data_file.exists():
        print("ERROR: No input data file found.")
        return

    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run1")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "cross_mote_calibration_comparison_result.json"

    EPOCH_THRESHOLD = 2
    DEVIATION_FACTOR = 2.0

    epoch_groups = defaultdict(list)
    total_rows = 0
    skipped_rows = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                normalized = {k.lower(): v for k, v in row.items()}

                epoch_val = safe_float(normalized.get('epoch'))
                moteid_val = safe_float(normalized.get('moteid'))
                temp_val = safe_float(normalized.get('temperature'))
                hum_val = safe_float(normalized.get('humidity'))

                if epoch_val is None or moteid_val is None:
                    skipped_rows += 1
                    continue

                epoch_key = int(epoch_val)
                mote_id = int(moteid_val)

                epoch_groups[epoch_key].append({
                    'moteid': mote_id,
                    'temperature': temp_val,
                    'humidity': hum_val
                })
    except Exception as e:
        print(f"ERROR reading data: {e}")
        return

    anomalies = []
    stats_summary = []
    total_anomaly_count = 0
    total_epochs_analyzed = 0

    for epoch_key, readings in sorted(epoch_groups.items()):
        if len(readings) < EPOCH_THRESHOLD:
            continue

        total_epochs_analyzed += 1
        temps = [r['temperature'] for r in readings]
        hums = [r['humidity'] for r in readings]

        temp_mean, temp_std = compute_mean_std(temps)
        hum_mean, hum_std = compute_mean_std(hums)

        if temp_mean is None or temp_std is None:
            continue

        epoch_stats = {
            'epoch': epoch_key,
            'num_motes': len(readings),
            'temp_mean': round(temp_mean, 4),
            'temp_std': round(temp_std, 4),
            'hum_mean': round(hum_mean, 4) if hum_mean else None,
            'hum_std': round(hum_std, 4) if hum_std else None
        }
        stats_summary.append(epoch_stats)

        for r in readings:
            mote = r['moteid']
            temp = r['temperature']
            hum = r['humidity']

            if temp is not None and temp_std is not None and temp_std > 0:
                z_temp = abs(temp - temp_mean) / temp_std
                if z_temp > DEVIATION_FACTOR:
                    anomaly = {
                        'epoch': epoch_key,
                        'moteid': mote,
                        'metric': 'temperature',
                        'value': round(temp, 4),
                        'group_mean': round(temp_mean, 4),
                        'group_std': round(temp_std, 4),
                        'z_score': round(z_temp, 4)
                    }
                    anomalies.append(anomaly)
                    total_anomaly_count += 1

            if hum is not None and hum_std is not None and hum_std > 0:
                z_hum = abs(hum - hum_mean) / hum_std
                if z_hum > DEVIATION_FACTOR:
                    anomaly = {
                        'epoch': epoch_key,
                        'moteid': mote,
                        'metric': 'humidity',
                        'value': round(hum, 4),
                        'group_mean': round(hum_mean, 4),
                        'group_std': round(hum_std, 4),
                        'z_score': round(z_hum, 4)
                    }
                    anomalies.append(anomaly)
                    total_anomaly_count += 1

    # Aggregate per-mote anomaly counts
    mote_anomaly_counts = defaultdict(int)
    for a in anomalies:
        mote_anomaly_counts[a['moteid']] += 1

    top_flagged_motes = sorted(mote_anomaly_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    result = {
        'task_name': 'cross_mote_calibration_comparison',
        'description': 'Compare simultaneous temperature and humidity readings across different motes during the same epoch to detect calibration discrepancies or faulty nodes.',
        'result_summary': [
            f'Total rows processed: {total_rows}',
            f'Rows skipped (missing epoch/moteid): {skipped_rows}',
            f'Epochs analyzed (with >= {EPOCH_THRESHOLD} motes): {total_epochs_analyzed}',
            f'Total calibration anomalies detected: {total_anomaly_count}',
            f'Deviation threshold: {DEVIATION_FACTOR} standard deviations'
        ],
        'top_flagged_motes': [{'moteid': m, 'anomaly_count': c} for m, c in top_flagged_motes],
        'sample_anomalies': anomalies[:20],
        'result_generated_at': __import__('datetime').datetime.now().isoformat()
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f'Result saved to {output_path}')
    print(f'Anomalies detected: {total_anomaly_count}')
    if top_flagged_motes:
        print(f'Top flagged motes: {top_flagged_motes[:5]}')

if __name__ == '__main__':
    main()