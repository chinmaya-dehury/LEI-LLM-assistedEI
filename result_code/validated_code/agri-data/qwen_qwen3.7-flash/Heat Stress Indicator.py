"""
Task: Heat Stress Indicator
Description: Evaluates the Temperature-Humidity Index (THI) against a critical threshold to detect environmental stress conditions affecting crop yield.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "agri-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import csv
import json
import os
import math
from pathlib import Path
from datetime import datetime

def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'NaN'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def classify_thi(thi):
    if thi is None:
        return 'Unknown'
    if thi < 21:
        return 'No Stress'
    elif thi < 25:
        return 'Mild Stress'
    elif thi < 29:
        return 'Moderate Stress'
    elif thi < 33:
        return 'Severe Stress'
    else:
        return 'Extreme Stress'

def main():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = root_dir / 'data' / 'agri-data' / 'raw_data.csv'
    if not data_file.exists():
        data_file = root_dir / 'data' / 'agri-data' / 'raw_data.txt'
    if not data_file.exists():
        print('Error: No data file found in data/agri-data/')
        return

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'Heat Stress Indicator_result.json'

    rows = []
    dropped = 0
    total = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.lower(): v for k, v in row.items()}
                total += 1
                thi = safe_float(row.get('thi'))
                temp = safe_float(row.get('temperature'))
                humidity = safe_float(row.get('humidity'))
                label = row.get('label', 'unknown').strip().lower() if row.get('label') else 'unknown'

                if thi is None:
                    if temp is not None and humidity is not None:
                        temp_f = temp * 9.0 / 5.0 + 32.0
                        thi = temp_f - (0.55 - 0.0055 * humidity) * (temp_f - 58.0)
                    else:
                        dropped += 1
                        continue

                stress_level = classify_thi(thi)
                rows.append({
                    'thi': round(thi, 2),
                    'temperature': temp,
                    'humidity': humidity,
                    'label': label,
                    'stress_level': stress_level
                })
    except Exception as e:
        print(f'Error reading data: {e}')
        return

    if not rows:
        print('No valid data rows found.')
        return

    stress_counts = {}
    stress_by_crop = {}
    thi_values = []

    for r in rows:
        sl = r['stress_level']
        stress_counts[sl] = stress_counts.get(sl, 0) + 1
        crop = r['label']
        if crop not in stress_by_crop:
            stress_by_crop[crop] = {}
        stress_by_crop[crop][sl] = stress_by_crop[crop].get(sl, 0) + 1
        if r['thi'] is not None:
            thi_values.append(r['thi'])

    avg_thi = sum(thi_values) / len(thi_values) if thi_values else 0
    max_thi = max(thi_values) if thi_values else 0
    min_thi = min(thi_values) if thi_values else 0
    high_stress_count = stress_counts.get('Severe Stress', 0) + stress_counts.get('Extreme Stress', 0)
    high_stress_pct = (high_stress_count / len(rows)) * 100 if rows else 0

    result = {
        'task_name': 'Heat Stress Indicator',
        'description': 'Evaluates the Temperature-Humidity Index (THI) against a critical threshold to detect environmental stress conditions affecting crop yield.',
        'result_summary': [
            f'Total valid rows analyzed: {len(rows)}',
            f'Dropped rows (missing data): {dropped}',
            f'Average THI: {round(avg_thi, 2)}',
            f'Max THI: {round(max_thi, 2)}',
            f'Min THI: {round(min_thi, 2)}',
            f'High stress (Severe/Extreme) count: {high_stress_count} ({round(high_stress_pct, 1)}%)',
            f'Stress distribution: {json.dumps(stress_counts)}',
            f'Stress by crop: {json.dumps(stress_by_crop)}'
        ],
        'result_generated_at': datetime.now().isoformat()
    }

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {output_file}')

if __name__ == '__main__':
    main()