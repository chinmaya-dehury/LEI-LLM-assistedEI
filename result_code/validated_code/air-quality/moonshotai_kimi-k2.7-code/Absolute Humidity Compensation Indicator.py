"""
Task: Absolute Humidity Compensation Indicator
Description: Quantify the correlation between absolute humidity and sensor-reference residuals for each sensor to assess whether humidity compensation is needed.
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

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

MISSING_TOKENS = {'', 'na', 'n/a', 'None', 'none'}
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2')

SENSOR_PAIRS = [
    ('pt08.s1(co)', 'co(gt)', 'PT08.S1(CO)', 'CO(GT)'),
    ('pt08.s2(nmhc)', 'nmhc(gt)', 'PT08.S2(NMHC)', 'NMHC(GT)'),
    ('pt08.s3(nox)', 'nox(gt)', 'PT08.S3(NOx)', 'NOx(GT)'),
    ('pt08.s4(no2)', 'no2(gt)', 'PT08.S4(NO2)', 'NO2(GT)'),
]

NO_REFERENCE_SENSOR = ('pt08.s5(o3)', 'PT08.S5(O3)')


def find_project_root():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    if not (root_dir / 'data').exists():
        print('Error: project root containing data/ directory not found.', file=sys.stderr)
        sys.exit(1)
    return root_dir


def find_data_file(root_dir):
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'air-quality' / name
        if candidate.exists():
            return candidate
    print('Error: raw_data.csv or raw_data.txt not found under data/air-quality/.', file=sys.stderr)
    sys.exit(1)


def to_float(value, column_name):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING_TOKENS:
        return None
    try:
        f = float(s)
    except ValueError:
        print(f'Warning: invalid numeric value in {column_name}: {value!r}', file=sys.stderr)
        return None
    # -200 is the dataset sentinel for missing/invalid measurements
    if f <= -200:
        return None
    return f


def pearson_correlation(x, y):
    n = len(x)
    if n < 2:
        return None
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = sum((xi - mean_x) ** 2 for xi in x)
    den_y = sum((yi - mean_y) ** 2 for yi in y)
    den = math.sqrt(den_x * den_y)
    if den == 0:
        return None
    return num / den


def parse_data(data_file, strict=False):
    ah_values = []
    residuals = {pair[0]: [] for pair in SENSOR_PAIRS}
    dropped_rows = 0
    cleaned_rows = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            ah = to_float(row.get('ah'), 'AH')

            if strict:
                required_cols = ['ah'] + [p[0] for p in SENSOR_PAIRS] + [p[1] for p in SENSOR_PAIRS]
                if any(to_float(row.get(col), col) is None for col in required_cols):
                    dropped_rows += 1
                    continue

            if ah is None:
                if not strict:
                    dropped_rows += 1
                continue

            valid_pair = False
            for sensor_key, ref_key, _, _ in SENSOR_PAIRS:
                sensor_val = to_float(row.get(sensor_key), sensor_key)
                ref_val = to_float(row.get(ref_key), ref_key)
                if sensor_val is not None and ref_val is not None:
                    residuals[sensor_key].append((ah, sensor_val - ref_val))
                    valid_pair = True

            if valid_pair:
                cleaned_rows += 1
            elif not strict:
                dropped_rows += 1

    return residuals, cleaned_rows, dropped_rows


def main():
    parser = argparse.ArgumentParser(description='Absolute humidity compensation indicator')
    parser.add_argument('--strict', action='store_true', help='Require complete rows for all sensor-reference pairs')
    args = parser.parse_args()

    root_dir = find_project_root()
    data_file = find_data_file(root_dir)

    residuals, cleaned_rows, dropped_rows = parse_data(data_file, strict=args.strict)

    result_summary = []
    for sensor_key, ref_key, sensor_label, ref_label in SENSOR_PAIRS:
        pairs = residuals[sensor_key]
        ah_vals = [p[0] for p in pairs]
        res_vals = [p[1] for p in pairs]
        corr = pearson_correlation(ah_vals, res_vals)
        mean_res = sum(res_vals) / len(res_vals) if res_vals else None
        mean_abs_res = sum(abs(r) for r in res_vals) / len(res_vals) if res_vals else None
        result_summary.append({
            'sensor': sensor_label,
            'reference': ref_label,
            'correlation_ah_residual': corr,
            'n': len(pairs),
            'mean_residual': mean_res,
            'mean_absolute_residual': mean_abs_res,
            'notes': 'Higher |correlation| suggests humidity compensation may be beneficial.'
        })

    # Sensor with no ground truth reference
    result_summary.append({
        'sensor': NO_REFERENCE_SENSOR[1],
        'reference': None,
        'correlation_ah_residual': None,
        'n': 0,
        'mean_residual': None,
        'mean_absolute_residual': None,
        'notes': 'No co-located ground truth reference available in dataset.'
    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        'task_name': 'Absolute Humidity Compensation Indicator',
        'description': 'Quantify the correlation between absolute humidity and sensor-reference residuals for each sensor to assess whether humidity compensation is needed.',
        'result_summary': result_summary,
        'result_generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    output_file = OUTPUT_DIR / 'absolute_humidity_compensation_indicator_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Cleaned rows used: {cleaned_rows}')
    print(f'Dropped/invalid rows: {dropped_rows}')
    print(f'Result saved to: {output_file}')
    for item in result_summary:
        print(f"{item['sensor']} vs {item['reference']}: r={item['correlation_ah_residual']}, n={item['n']}")


if __name__ == '__main__':
    main()