"""
Task: NOx_NO2_Ratio_Monitor
Description: Compute the ratio of valid NOx(GT) to NO2(GT) concentrations and flag ratios that fall outside expected physical bounds.
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
import sys
from datetime import datetime
from pathlib import Path

MISSING = {'', 'na', 'n/a', 'None', 'none', '-200'}


def to_float(value, column, row_num):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        f = float(s)
    except ValueError:
        print(f'Row {row_num}: cannot parse {column} value {s!r}', file=sys.stderr)
        return None
    if math.isnan(f) or f < 0:
        return None
    return f


def resolve_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'air-quality' / name
        if candidate.exists():
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser(description='NOx/NO2 ratio monitor')
    parser.add_argument('--strict', action='store_true', help='require both NOx and NO2 on every row')
    args = parser.parse_args()

    data_file = resolve_data_file()
    if data_file is None:
        print('Data file not found under data/air-quality/raw_data.csv or .txt', file=sys.stderr)
        sys.exit(1)

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'NOx_NO2_Ratio_Monitor_result.json'

    nox_col = 'nox(gt)'
    no2_col = 'no2(gt)'
    lower_bound = 1.0
    upper_bound = 10.0

    total_rows = 0
    missing_target = 0
    invalid_parse = 0
    valid_pairs = 0
    flagged_low = 0
    flagged_high = 0
    ratios = []
    sample_flags = []
    dropped = 0

    try:
        with open(data_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                total_rows += 1
                row = {k.lower(): v for k, v in row.items()}
                if nox_col not in row or no2_col not in row:
                    if args.strict:
                        dropped += 1
                        continue
                    missing_target += 1
                    continue
                nox = to_float(row.get(nox_col), nox_col, row_num)
                no2 = to_float(row.get(no2_col), no2_col, row_num)
                if nox is None or no2 is None:
                    missing_target += 1
                    continue
                if no2 == 0:
                    invalid_parse += 1
                    continue
                ratio = nox / no2
                valid_pairs += 1
                ratios.append(ratio)
                flag = None
                if ratio < lower_bound:
                    flagged_low += 1
                    flag = 'below_lower_bound'
                elif ratio > upper_bound:
                    flagged_high += 1
                    flag = 'above_upper_bound'
                if flag and len(sample_flags) < 5:
                    sample_flags.append({
                        'row': row_num,
                        'date': row.get('date', ''),
                        'time': row.get('time', ''),
                        'nox_gt': nox,
                        'no2_gt': no2,
                        'ratio': round(ratio, 4),
                        'flag': flag
                    })
    except Exception as e:
        print(f'Error reading {data_file}: {e}', file=sys.stderr)
        sys.exit(1)

    mean_ratio = sum(ratios) / len(ratios) if ratios else None
    result = {
        'task_name': 'NOx_NO2_Ratio_Monitor',
        'description': 'Compute the ratio of valid NOx(GT) to NO2(GT) concentrations and flag ratios outside expected physical bounds.',
        'result_summary': [
            {'metric': 'data_file', 'value': str(data_file)},
            {'metric': 'total_rows_read', 'value': total_rows},
            {'metric': 'rows_missing_target_values', 'value': missing_target},
            {'metric': 'rows_with_invalid_parse_or_zero_no2', 'value': invalid_parse},
            {'metric': 'rows_dropped_strict_mode', 'value': dropped},
            {'metric': 'valid_nox_no2_pairs', 'value': valid_pairs},
            {'metric': 'mean_nox_no2_ratio', 'value': round(mean_ratio, 4) if mean_ratio is not None else None},
            {'metric': 'ratio_lower_bound', 'value': lower_bound},
            {'metric': 'ratio_upper_bound', 'value': upper_bound},
            {'metric': 'flagged_below_lower_bound', 'value': flagged_low},
            {'metric': 'flagged_above_upper_bound', 'value': flagged_high},
            {'metric': 'flagged_sample', 'value': sample_flags}
        ],
        'result_generated_at': datetime.now().isoformat()
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Wrote {output_file}')
    print(f'Valid pairs: {valid_pairs}, flagged low: {flagged_low}, flagged high: {flagged_high}')


if __name__ == '__main__':
    main()