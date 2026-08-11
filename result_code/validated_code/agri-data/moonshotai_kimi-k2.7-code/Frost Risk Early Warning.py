"""
Task: Frost Risk Early Warning
Description: Monitor the Frost_Risk index and generate an early warning alert when the probability of frost exceeds a critical safety threshold.
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
import sys
from pathlib import Path
from datetime import datetime

def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ['raw_data.csv', 'raw_data.txt']:
        p = root / 'data' / 'agri-data' / name
        if p.exists():
            return p
    return None

def to_float(val, col):
    if val is None:
        return None
    s = str(val).strip()
    if s == '' or s.upper() in ('NA', 'N/A', 'NULL', 'NONE'):
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{col}': {val}")
        return None

def main():
    threshold = 0.5
    if len(sys.argv) > 1:
        try:
            threshold = float(sys.argv[1])
        except ValueError:
            print("Usage: python frost_risk_warning.py [threshold]")
            sys.exit(1)

    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/agri-data/")
        sys.exit(1)

    alerts = []
    total = 0
    valid = 0
    missing = 0
    values = []

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            if 'frost_risk' not in row:
                print("Error: required column 'Frost_Risk' missing")
                return

            fr = to_float(row.get('frost_risk'), 'frost_risk')
            label = row.get('label', 'unknown')

            if fr is None:
                missing += 1
                continue

            valid += 1
            values.append(fr)

            if fr > threshold:
                alerts.append({'row': idx, 'crop': label, 'frost_risk': fr})

    avg = sum(values) / len(values) if values else 0.0
    maxv = max(values) if values else 0.0
    status = 'CRITICAL' if alerts else 'NORMAL'

    summary = {
        'threshold': threshold,
        'total_rows': total,
        'valid_rows': valid,
        'missing_rows': missing,
        'max_frost_risk': maxv,
        'mean_frost_risk': round(avg, 4),
        'alert_count': len(alerts),
        'status': status,
        'alerts': alerts[:10]
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'frost_risk_early_warning_result.json'

    result = {
        'task_name': 'Frost Risk Early Warning',
        'description': 'Monitor Frost_Risk and generate early warning when probability exceeds threshold.',
        'result_summary': [summary],
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"Frost risk status: {status}. Alerts: {len(alerts)}. Output: {out_path}")

if __name__ == '__main__':
    main()