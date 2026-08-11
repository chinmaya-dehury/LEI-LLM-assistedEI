"""
Task: Cross-Mote Spatial Temperature Variance
Description: Calculate the standard deviation of temperature readings across all currently reporting motes to identify localized thermal hotspots or cold zones.
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
from datetime import datetime

def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.upper() in ('NA', 'N/A', 'NULL', ''):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)

def std_dev(values):
    if len(values) < 2:
        return 0.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)

def main():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = root_dir / 'data' / 'lab-data' / 'raw_data.csv'
    if not data_file.exists():
        data_file = root_dir / 'data' / 'lab-data' / 'raw_data.txt'
    if not data_file.exists():
        print('ERROR: No raw_data.csv or raw_data.txt found under data/lab-data/')
        result = {
            'task_name': 'Cross-Mote_Spatial_Temperature_Variance',
            'description': 'Calculate the standard deviation of temperature readings across all currently reporting motes to identify localized thermal hotspots or cold zones.',
            'result_summary': [{'error': 'Input file not found'}],
            'result_generated_at': datetime.now().isoformat()
        }
        out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2')
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'Cross-Mote_Spatial_Temperature_Variance_result.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
        return

    mote_temps = {}
    total_rows = 0
    valid_rows = 0
    dropped_rows = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                row_lower = {k.lower(): v for k, v in row.items()}
                if 'moteid' not in row_lower or 'temperature' not in row_lower:
                    dropped_rows += 1
                    continue
                mote_id = row_lower.get('moteid', '').strip()
                temp = safe_float(row_lower.get('temperature'))
                if not mote_id or temp is None:
                    dropped_rows += 1
                    continue
                if mote_id not in mote_temps:
                    mote_temps[mote_id] = []
                mote_temps[mote_id].append(temp)
                valid_rows += 1
    except Exception as e:
        print(f'ERROR reading file: {e}')
        result = {
            'task_name': 'Cross-Mote_Spatial_Temperature_Variance',
            'description': 'Calculate the standard deviation of temperature readings across all currently reporting motes to identify localized thermal hotspots or cold zones.',
            'result_summary': [{'error': str(e)}],
            'result_generated_at': datetime.now().isoformat()
        }
        out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2')
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'Cross-Mote_Spatial_Temperature_Variance_result.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
        return

    if not mote_temps:
        print('No valid temperature data found.')
        result = {
            'task_name': 'Cross-Mote_Spatial_Temperature_Variance',
            'description': 'Calculate the standard deviation of temperature readings across all currently reporting motes to identify localized thermal hotspots or cold zones.',
            'result_summary': [{'error': 'No valid temperature data'}],
            'result_generated_at': datetime.now().isoformat()
        }
        out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2')
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'Cross-Mote_Spatial_Temperature_Variance_result.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
        return

    results = []
    for mote_id, temps in sorted(mote_temps.items(), key=lambda x: x[0]):
        m = mean(temps)
        sd = std_dev(temps)
        min_t = min(temps)
        max_t = max(temps)
        count = len(temps)
        results.append({
            'mote_id': int(mote_id),
            'reading_count': count,
            'mean_temperature': round(m, 4),
            'std_deviation': round(sd, 4),
            'min_temperature': round(min_t, 4),
            'max_temperature': round(max_t, 4),
            'range': round(max_t - min_t, 4)
        })

    overall_mean = mean([r['mean_temperature'] for r in results])
    overall_sd = std_dev([r['mean_temperature'] for r in results])
    hotspot_motes = [r for r in results if r['std_deviation'] > overall_sd * 1.5]
    stable_motes = [r for r in results if r['std_deviation'] <= overall_sd * 0.5]

    summary = [
        f'Total rows processed: {total_rows}',
        f'Valid rows: {valid_rows}',
        f'Dropped rows: {dropped_rows}',
        f'Motes analyzed: {len(results)}',
        f'Overall mean temperature across motes: {round(overall_mean, 4)} C',
        f'Overall SD of mote means: {round(overall_sd, 4)}',
        f'Hotspot motes (high variance): {len(hotspot_motes)}',
        f'Stable motes (low variance): {len(stable_motes)}'
    ]

    result = {
        'task_name': 'Cross-Mote_Spatial_Temperature_Variance',
        'description': 'Calculate the standard deviation of temperature readings across all currently reporting motes to identify localized thermal hotspots or cold zones.',
        'result_summary': summary,
        'per_mote_analysis': results,
        'summary_statistics': {
            'overall_mean_temperature': round(overall_mean, 4),
            'overall_std_deviation': round(overall_sd, 4),
            'hotspot_mote_ids': [r['mote_id'] for r in hotspot_motes],
            'stable_mote_ids': [r['mote_id'] for r in stable_motes]
        },
        'result_generated_at': datetime.now().isoformat()
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'Cross-Mote_Spatial_Temperature_Variance_result.json'
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_path}')
    print(f'Motes analyzed: {len(results)}, Hotspots: {len(hotspot_motes)}, Stable: {len(stable_motes)}')

if __name__ == '__main__':
    main()