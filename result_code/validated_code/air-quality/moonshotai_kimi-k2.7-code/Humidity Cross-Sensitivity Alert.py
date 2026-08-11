"""
Task: Humidity Cross-Sensitivity Alert
Description: Flag time intervals where relative humidity or absolute humidity exceeds a configurable threshold and the associated sensor-reference residual simultaneously increases, indicating likely humidity-driven cross-sensitivity.
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
import sys
from datetime import datetime
from pathlib import Path

TASK_NAME = 'Humidity Cross-Sensitivity Alert'
DESCRIPTION = 'Flag time intervals where relative humidity or absolute humidity exceeds a configurable threshold and the associated sensor-reference residual simultaneously increases, indicating likely humidity-driven cross-sensitivity.'

MISSING = {'', 'NA', 'N/A', 'None', 'NULL', 'None', '-200'}
NUMERIC_COLS = [
    'co(gt)', 'pt08.s1(co)', 'nmhc(gt)', 'pt08.s2(nmhc)',
    'nox(gt)', 'pt08.s3(nox)', 'no2(gt)', 'pt08.s4(no2)',
    'pt08.s5(o3)', 't', 'rh', 'ah'
]
PAIRS = [
    ('CO', 'co(gt)', 'pt08.s1(co)'),
    ('NMHC', 'nmhc(gt)', 'pt08.s2(nmhc)'),
    ('NOx', 'nox(gt)', 'pt08.s3(nox)'),
    ('NO2', 'no2(gt)', 'pt08.s4(no2)'),
]


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for fname in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'air-quality' / fname
        if candidate.exists():
            return candidate
    return None


def to_float(value, col_name):
    if value is None:
        return None
    s = str(value).strip()
    if s in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print('Warning: invalid numeric value in column ' + col_name + ': ' + str(value), file=sys.stderr)
        return None


def load_rows(path, strict=False):
    required = ['date', 'time'] + NUMERIC_COLS
    rows = []
    dropped = 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            missing_cols = [c for c in required if c not in row]
            if missing_cols:
                if strict:
                    print('Error: missing columns ' + ', '.join(missing_cols), file=sys.stderr)
                    return []
                dropped += 1
                continue
            parsed = {
                'date': row.get('date', '').strip(),
                'time': row.get('time', '').strip(),
            }
            row_ok = True
            for col in NUMERIC_COLS:
                val = to_float(row.get(col), col)
                parsed[col] = val
                if val is None:
                    row_ok = False
            if not row_ok:
                dropped += 1
                if strict:
                    continue
            rows.append(parsed)
    print('Loaded ' + str(len(rows)) + ' rows, dropped ' + str(dropped) + ' rows due to missing/invalid data.')
    return rows


def compute_residuals(row):
    residuals = {}
    for name, ref_col, sens_col in PAIRS:
        ref = row.get(ref_col)
        sens = row.get(sens_col)
        if ref is not None and sens is not None:
            residuals[name] = sens - ref
    return residuals


def main():
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument('--rh-threshold', type=float, default=70.0, help='Relative humidity threshold (%)')
    parser.add_argument('--ah-threshold', type=float, default=0.8, help='Absolute humidity threshold')
    parser.add_argument('--residual-threshold', type=float, default=500.0, help='Minimum residual magnitude to flag')
    parser.add_argument('--strict', action='store_true', help='Require complete rows')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv or raw_data.txt not found under data/air-quality/', file=sys.stderr)
        sys.exit(1)

    rows = load_rows(data_file, strict=args.strict)
    if not rows:
        print('No data loaded.', file=sys.stderr)
        sys.exit(1)

    flagged = []
    prev_residuals = {}
    for row in rows:
        rh = row.get('rh')
        ah = row.get('ah')
        high_humidity = (rh is not None and rh > args.rh_threshold) or (ah is not None and ah > args.ah_threshold)
        residuals = compute_residuals(row)
        if high_humidity:
            for name, ref_col, sens_col in PAIRS:
                resid = residuals.get(name)
                if resid is None:
                    continue
                prev = prev_residuals.get(name)
                if abs(resid) > args.residual_threshold and (prev is None or abs(resid) > abs(prev)):
                    flagged.append({
                        'datetime': row['date'] + ' ' + row['time'],
                        'pollutant': name,
                        'rh': rh,
                        'ah': ah,
                        'residual': round(resid, 2),
                        'previous_residual': round(prev, 2) if prev is not None else None,
                        'reference': row.get(ref_col),
                        'sensor': row.get(sens_col),
                    })
        prev_residuals = residuals

    summary = flagged[:200]

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': summary,
        'result_generated_at': datetime.utcnow().isoformat() + 'Z',
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / (TASK_NAME.lower().replace(' ', '_').replace('-', '_') + '_result.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print('Saved ' + str(len(flagged)) + ' flagged intervals to ' + str(out_file))


if __name__ == '__main__':
    main()