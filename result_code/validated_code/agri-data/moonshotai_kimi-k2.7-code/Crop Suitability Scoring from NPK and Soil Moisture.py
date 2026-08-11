"""
Task: Crop Suitability Scoring from NPK and Soil Moisture
Description: Compute a lightweight crop-suitability score for the current crop label by comparing measured N, P, K, and Soil_Moisture against crop-specific reference ranges. Flags mismatches that may indicate poor crop-environment fit.
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
import csv
import json
import math
import sys
from pathlib import Path
from datetime import datetime

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ('raw_data.csv', 'raw_data.txt'):
        p = root_dir / 'data' / 'agri-data' / name
        if p.exists():
            return p
    return None

def to_float(value, column):
    if value is None:
        return None
    s = str(value).strip()
    if s == '' or s.lower() in ('na', 'n/a', 'None'):
        return None
    try:
        return float(s)
    except ValueError:
        print(f'Warning: invalid numeric value in {column}: {value!r}', file=sys.stderr)
        return None

def load_data(path):
    rows = []
    dropped = 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            n = to_float(row.get('n'), 'N')
            p = to_float(row.get('p'), 'P')
            k = to_float(row.get('k'), 'K')
            sm = to_float(row.get('soil_moisture'), 'Soil_Moisture')
            label = row.get('label')
            if None in (n, p, k, sm) or label is None or str(label).strip() == '':
                dropped += 1
                continue
            rows.append({'label': str(label).strip(), 'n': n, 'p': p, 'k': k, 'soil_moisture': sm})
    return rows, dropped

def compute_crop_stats(rows):
    grouped = {}
    for r in rows:
        grouped.setdefault(r['label'], []).append([r['n'], r['p'], r['k'], r['soil_moisture']])
    stats = {}
    for label, vals in grouped.items():
        count = len(vals)
        means = [sum(v[i] for v in vals) / count for i in range(4)]
        stds = []
        for i in range(4):
            if count > 1:
                variance = sum((v[i] - means[i]) ** 2 for v in vals) / (count - 1)
                stds.append(math.sqrt(variance))
            else:
                stds.append(0.0)
        stats[label] = {'mean': means, 'std': stds, 'count': count}
    return stats

def score_row(row, stats):
    label = row['label']
    if label not in stats:
        return None
    st = stats[label]
    means = st['mean']
    stds = st['std']
    variables = ['N', 'P', 'K', 'Soil_Moisture']
    scores = []
    flags = []
    total = 0.0
    for i, val in enumerate([row['n'], row['p'], row['k'], row['soil_moisture']]):
        mean = means[i]
        std = stds[i]
        if std == 0:
            distance = 0.0 if val == mean else 1.0
        else:
            distance = abs(val - mean) / std
        score = max(0.0, min(100.0, 100.0 - distance * 20.0))
        scores.append(round(score, 2))
        total += score
        if distance > 2.0:
            flags.append(f'{variables[i]} deviates by {distance:.2f} standard deviations')
    overall = round(total / 4.0, 2)
    return {
        'label': label,
        'overall_suitability': overall,
        'component_scores': dict(zip(variables, scores)),
        'flags': flags
    }

def main():
    data_file = find_data_file()
    if not data_file:
        print('Error: raw_data.csv or raw_data.txt not found under data/agri-data/', file=sys.stderr)
        sys.exit(1)
    rows, dropped = load_data(data_file)
    if not rows:
        print('Error: no valid rows after cleaning', file=sys.stderr)
        sys.exit(1)
    print(f'Loaded {len(rows)} rows, dropped {dropped} invalid rows.')
    stats = compute_crop_stats(rows)
    summaries = []
    for r in rows:
        sc = score_row(r, stats)
        if sc:
            summaries.append(sc)
    crop_avg = {}
    for s in summaries:
        crop_avg.setdefault(s['label'], []).append(s['overall_suitability'])
    avg_by_crop = {crop: round(sum(v) / len(v), 2) for crop, v in crop_avg.items()}
    result = {
        'task_name': 'Crop Suitability Scoring from NPK and Soil Moisture',
        'description': 'Lightweight crop-suitability score comparing measured N, P, K, and Soil_Moisture against per-crop reference ranges derived from the dataset; flags mismatches.',
        'result_summary': [
            {
                'total_rows_processed': len(rows),
                'dropped_rows': dropped,
                'average_suitability_by_crop': avg_by_crop,
                'row_scores_sample': summaries[:10]
            }
        ],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }
    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'Crop_Suitability_Scoring_from_NPK_and_Soil_Moisture_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_file}')

if __name__ == '__main__':
    main()