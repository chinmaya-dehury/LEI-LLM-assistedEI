"""
Task: Pest Pressure Growth-Stage Risk Flag
Description: Raise a pest risk alert when Pest_Pressure exceeds a growth-stage-specific threshold to enable timely intervention during vulnerable crop periods.
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

import os
import sys
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

MISSING = {'', 'na', 'n/a', 'None', 'none'}

GROWTH_STAGE_THRESHOLDS = {
    1: 1.0,   # Seedling
    2: 1.5,   # Vegetative
    3: 1.8    # Flowering
}

GROWTH_STAGE_NAME = {
    1: 'Seedling',
    2: 'Vegetative',
    3: 'Flowering'
}


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        candidate = root_dir / 'data' / 'agri-data' / name
        if candidate.exists():
            return candidate
    return None


def to_float(value, column_name):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print(f'Warning: invalid numeric value in {column_name}: {value!r}', file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description='Pest pressure growth-stage risk flag')
    parser.add_argument('--strict', action='store_true', help='require complete Pest_Pressure and Growth_Stage values')
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv or raw_data.txt not found under data/agri-data', file=sys.stderr)
        sys.exit(1)

    required_columns = ['pest_pressure', 'growth_stage']
    total_rows = 0
    dropped_rows = 0
    alerts = []
    counts_by_stage = {}
    risk_by_stage = {}

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print('Error: CSV has no header', file=sys.stderr)
            sys.exit(1)

        header = [h.lower() for h in reader.fieldnames]
        missing = [c for c in required_columns if c not in header]
        if missing:
            print(f'Error: missing required columns: {missing}', file=sys.stderr)
            sys.exit(1)

        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}

            pest = to_float(row.get('pest_pressure'), 'Pest_Pressure')
            growth = to_float(row.get('growth_stage'), 'Growth_Stage')

            if pest is None or growth is None:
                dropped_rows += 1
                continue

            stage_id = int(round(growth))
            stage = GROWTH_STAGE_NAME.get(stage_id, f'GrowthStage_{stage_id}')
            threshold = GROWTH_STAGE_THRESHOLDS.get(stage_id, 1.5)

            counts_by_stage[stage] = counts_by_stage.get(stage, 0) + 1

            if pest > threshold:
                risk_by_stage[stage] = risk_by_stage.get(stage, 0) + 1
                alerts.append({
                    'row': total_rows,
                    'growth_stage': stage,
                    'pest_pressure': pest,
                    'threshold': threshold,
                    'risk': 'HIGH'
                })

    summary = {
        'total_rows': total_rows,
        'dropped_rows': dropped_rows,
        'thresholds_by_stage': {GROWTH_STAGE_NAME.get(k, k): v for k, v in GROWTH_STAGE_THRESHOLDS.items()},
        'counts_by_stage': counts_by_stage,
        'high_risk_counts_by_stage': risk_by_stage,
        'high_risk_alerts': alerts[:100]
    }

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'pest_pressure_growth_stage_risk_flag_result.json'

    result = {
        'task_name': 'Pest Pressure Growth-Stage Risk Flag',
        'description': 'Raise a pest risk alert when Pest_Pressure exceeds a growth-stage-specific threshold to enable timely intervention during vulnerable crop periods.',
        'result_summary': [summary],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Saved {output_file}: {total_rows} rows processed, {len(alerts)} high-risk alerts')


if __name__ == '__main__':
    main()