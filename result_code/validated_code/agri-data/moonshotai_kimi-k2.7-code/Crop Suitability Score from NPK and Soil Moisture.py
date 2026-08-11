import json
import sys
import math
"""
Task: Crop Suitability Score from NPK and Soil Moisture
Description: Compute a lightweight crop suitability score for the recorded crop label by comparing soil Nitrogen, Phosphorus, Potassium, and Soil_Moisture against simple ideal ranges, producing a single suitability rating per record.
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

import csv, json, math, sys
from pathlib import Path
from datetime import datetime, timezone

TASK_NAME = 'Crop Suitability Score from NPK and Soil Moisture'

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

def to_float(value, column):
    if value is None:
        return None
    s = str(value).strip()
    if s == '' or s.upper() in ('NA', 'N/A', 'NULL', 'NONE'):
        return None
    try:
        return float(s)
    except ValueError:
        print(f'Invalid numeric value in column {column}: {s!r}', file=sys.stderr)
        return None

def suitability_score(n, p, k, soil_moisture):
    checks = (
        (50.0, 150.0, n),
        (30.0, 100.0, p),
        (30.0, 150.0, k),
        (30.0, 70.0, soil_moisture),
    )
    total = 0.0
    for lo, hi, val in checks:
        if val is None or math.isnan(val):
            continue
        if lo <= val <= hi:
            total += 25.0
        else:
            mid = (lo + hi) / 2.0
            half_range = (hi - lo) / 2.0
            distance = abs(val - mid)
            total += max(0.0, 25.0 * (1.0 - distance / (half_range * 2.0)))
    return round(max(0.0, min(100.0, total)), 2)

def rating(score):
    if score >= 80.0:
        return 'Excellent'
    if score >= 60.0:
        return 'Good'
    if score >= 40.0:
        return 'Fair'
    return 'Poor'

def main():
    strict = '--strict' in sys.argv
    data_file = find_data_file()
    if data_file is None:
        print('Data file not found under data/agri-data/raw_data.csv or raw_data.txt', file=sys.stderr)
        sys.exit(1)

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'crop_suitability_score_result.json'

    required = ('n', 'p', 'k', 'soil_moisture', 'label')
    records = []
    dropped = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            row = {k.lower(): v for k, v in row.items()}
            missing_cols = [c for c in required if c not in row or row[c].strip() == '']
            if missing_cols:
                if strict:
                    dropped += 1
                    print(f'Row {idx} dropped: missing columns {missing_cols}', file=sys.stderr)
                    continue
            n = to_float(row.get('n'), 'N')
            p = to_float(row.get('p'), 'P')
            k = to_float(row.get('k'), 'K')
            sm = to_float(row.get('soil_moisture'), 'Soil_Moisture')
            label = row.get('label', '').strip()
            if None in (n, p, k, sm) or not label:
                dropped += 1
                continue
            score = suitability_score(n, p, k, sm)
            records.append({
                'row': idx,
                'label': label,
                'N': n,
                'P': p,
                'K': k,
                'Soil_Moisture': sm,
                'suitability_score': score,
                'rating': rating(score)
            })

    rating_counts = {}
    for r in records:
        rating_counts[r['rating']] = rating_counts.get(r['rating'], 0) + 1

    result = {
        'task_name': TASK_NAME,
        'description': 'Lightweight crop suitability score from NPK and Soil_Moisture against ideal ranges.',
        'result_summary': [
            {
                'total_records': len(records),
                'dropped_rows': dropped,
                'rating_distribution': rating_counts,
                'sample_records': records[:10]
            }
        ],
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_file}; processed={len(records)}, dropped={dropped}')

if __name__ == '__main__':
    main()