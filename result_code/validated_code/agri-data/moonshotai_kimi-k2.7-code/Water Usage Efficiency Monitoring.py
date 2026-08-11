import json
import sys
import math
import csv
"""
Task: Water Usage Efficiency Monitoring
Description: Analyze Water_Usage_Efficiency (L/kg) in relation to Irrigation_Frequency and Rainfall to identify inefficient water use and support conservation decisions.
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

#!/usr/bin/env python3
import os, sys, csv, json, math, argparse
from pathlib import Path
from datetime import datetime, timezone

MISSING = {'', 'NA', 'N/A', 'None', 'NULL', 'None'}

def safe_float(value, col):
    if value is None:
        return None
    s = str(value).strip()
    if s in MISSING:
        return None
    try:
        return float(s)
    except Exception as e:
        print(f'Warning: invalid numeric value in {col}: {value!r}', file=sys.stderr)
        return None

def safe_int(value, col):
    f = safe_float(value, col)
    if f is None:
        return None
    return int(f)

def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    num = sum(a * b for a, b in zip(dx, dy))
    den = math.sqrt(sum(a * a for a in dx) * sum(b * b for b in dy))
    if den == 0:
        return None
    return num / den

def main():
    parser = argparse.ArgumentParser(description='Water Usage Efficiency Monitoring')
    parser.add_argument('--strict', action='store_true', help='Require complete WUE, Irrigation_Frequency, Rainfall rows')
    args = parser.parse_args()

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
        print(f'Input file not found under {root_dir / "data" / "agri-data"}', file=sys.stderr)
        sys.exit(1)

    required = {'water_usage_efficiency', 'irrigation_frequency', 'rainfall'}
    rows = []
    skipped = 0
    total = 0

    with data_file.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            if args.strict:
                if not required.issubset(row.keys()):
                    skipped += 1
                    continue
            wue = safe_float(row.get('water_usage_efficiency'), 'Water_Usage_Efficiency')
            irr = safe_int(row.get('irrigation_frequency'), 'Irrigation_Frequency')
            rain = safe_float(row.get('rainfall'), 'Rainfall')
            if wue is None or irr is None or rain is None:
                skipped += 1
                continue
            rows.append({'wue': wue, 'irr': irr, 'rain': rain, 'label': row.get('label', '')})

    if not rows:
        print('No valid rows found for analysis.', file=sys.stderr)
        sys.exit(1)

    wues = [r['wue'] for r in rows]
    n = len(wues)
    mean_wue = sum(wues) / n
    var = sum((x - mean_wue) ** 2 for x in wues) / n
    std_wue = math.sqrt(var)
    min_wue = min(wues)
    max_wue = max(wues)

    corr_rain = pearson(wues, [r['rain'] for r in rows])
    corr_irr = pearson(wues, [r['irr'] for r in rows])

    irr_groups = {}
    for r in rows:
        irr_groups.setdefault(r['irr'], []).append(r)
    irr_summary = {}
    for irr, g in sorted(irr_groups.items()):
        gwue = [x['wue'] for x in g]
        grat = [x['rain'] for x in g]
        irr_summary[str(irr)] = {
            'count': len(g),
            'mean_wue': round(sum(gwue) / len(gwue), 4),
            'mean_rainfall': round(sum(grat) / len(grat), 4)
        }

    sorted_wue = sorted(wues)
    q1 = sorted_wue[n // 4] if n >= 4 else sorted_wue[0]
    inefficient = [r for r in rows if r['wue'] < q1]
    inefficient_count = len(inefficient)

    result = {
        'task_name': 'Water Usage Efficiency Monitoring',
        'description': 'Analyze Water_Usage_Efficiency (L/kg) in relation to Irrigation_Frequency and Rainfall to identify inefficient water use and support conservation decisions.',
        'result_summary': [
            {'metric': 'total_rows', 'value': total},
            {'metric': 'valid_rows', 'value': n},
            {'metric': 'skipped_rows', 'value': skipped},
            {'metric': 'wue_mean', 'value': round(mean_wue, 4)},
            {'metric': 'wue_std', 'value': round(std_wue, 4)},
            {'metric': 'wue_min', 'value': round(min_wue, 4)},
            {'metric': 'wue_max', 'value': round(max_wue, 4)},
            {'metric': 'correlation_wue_rainfall', 'value': round(corr_rain, 4) if corr_rain is not None else None},
            {'metric': 'correlation_wue_irrigation_frequency', 'value': round(corr_irr, 4) if corr_irr is not None else None},
            {'metric': 'irrigation_frequency_summary', 'value': irr_summary},
            {'metric': 'inefficient_use_threshold_q1', 'value': round(q1, 4)},
            {'metric': 'inefficient_use_count', 'value': inefficient_count}
        ],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'Water Usage Efficiency Monitoring_result.json'
    with out_file.open('w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_file}')

if __name__ == '__main__':
    main()