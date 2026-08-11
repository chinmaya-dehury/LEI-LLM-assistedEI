"""
Task: Sensor_Response_Range_Check
Description: Validate each PT08 sensor response against configured minimum and maximum operational ranges and flag any out-of-range readings.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "air-quality")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SENSOR_RANGES = {
    'pt08.s1(co)': {'min': 500.0, 'max': 3500.0},
    'pt08.s2(nmhc)': {'min': 300.0, 'max': 3000.0},
    'pt08.s3(nox)': {'min': 400.0, 'max': 2700.0},
    'pt08.s4(no2)': {'min': 400.0, 'max': 2800.0},
    'pt08.s5(o3)': {'min': 200.0, 'max': 2600.0}
}

MISSING = {'', 'NA', 'N/A', 'None', 'NULL', 'None'}

def to_float(value, col_name):
    if value is None:
        return None
    s = str(value).strip()
    if s in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print(f'Warning: invalid numeric value {value} in column {col_name}, treating as missing', file=sys.stderr)
        return None

def resolve_input_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for ext in ('csv', 'txt'):
        data_file = root_dir / 'data' / 'air-quality' / f'raw_data.{ext}'
        if data_file.exists():
            return data_file
    return None

def main():
    data_file = resolve_input_file()
    if not data_file:
        print('Error: raw_data.csv or raw_data.txt not found under data/air-quality/', file=sys.stderr)
        sys.exit(1)

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = {key: {'total': 0, 'valid': 0, 'out_of_range': 0, 'values': []} for key in SENSOR_RANGES}
    flagged_rows = []
    rows_processed = 0
    rows_dropped = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            rows_processed += 1
            row = {k.lower().strip(): (v.strip() if v else '') for k, v in row.items()}
            try:
                for sensor, limits in SENSOR_RANGES.items():
                    stats[sensor]['total'] += 1
                    val = to_float(row.get(sensor), sensor)
                    if val is None:
                        continue
                    stats[sensor]['valid'] += 1
                    stats[sensor]['values'].append(val)
                    if val < limits['min'] or val > limits['max']:
                        stats[sensor]['out_of_range'] += 1
                        if len(flagged_rows) < 20:
                            flagged_rows.append({
                                'row_index': i,
                                'sensor': sensor,
                                'value': val,
                                'range_min': limits['min'],
                                'range_max': limits['max'],
                                'date': row.get('date', ''),
                                'time': row.get('time', '')
                            })
            except Exception as e:
                rows_dropped += 1
                print(f'Warning: error processing row {i}: {e}', file=sys.stderr)

    summary = []
    for sensor, data in stats.items():
        values = data['values']
        limits = SENSOR_RANGES[sensor]
        if values:
            avg = sum(values) / len(values)
            min_v = min(values)
            max_v = max(values)
        else:
            avg = None
            min_v = None
            max_v = None
        summary.append({
            'sensor': sensor,
            'configured_range_min': limits['min'],
            'configured_range_max': limits['max'],
            'total_readings': data['total'],
            'valid_readings': data['valid'],
            'out_of_range_count': data['out_of_range'],
            'valid_min': min_v,
            'valid_max': max_v,
            'valid_mean': round(avg, 4) if avg is not None else None
        })

    result = {
        'task_name': 'Sensor_Response_Range_Check',
        'description': 'Validate each PT08 sensor response against configured minimum and maximum operational ranges and flag any out-of-range readings.',
        'result_summary': summary + [
            {'rows_processed': rows_processed},
            {'rows_dropped_or_invalid': rows_dropped},
            {'flagged_sample': flagged_rows}
        ],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    out_file = out_dir / 'Sensor_Response_Range_Check_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_file}')

if __name__ == '__main__':
    main()