"""
Task: Diurnal_Average_Tracker
Description: Maintain rolling hourly averages for each pollutant grouped by time-of-day to reveal daily concentration patterns without storing the full history.
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

import os
import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

POLLUTANTS = ['co(gt)', 'nmhc(gt)', 'c6h6(gt)', 'nox(gt)', 'no2(gt)']
MISSING_STRINGS = {'', 'NA', 'N/A', 'NULL', 'NONE'}


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for ext in ('csv', 'txt'):
        candidate = root_dir / 'data' / 'air-quality' / f'raw_data.{ext}'
        if candidate.exists():
            return candidate
    return None


def is_missing(value):
    if value is None:
        return True
    s = str(value).strip()
    return s.upper() in MISSING_STRINGS


def safe_float(value, column):
    if is_missing(value):
        return None
    s = str(value).strip()
    try:
        f = float(s)
        # The dataset uses -200 as a sentinel for missing readings.
        if f <= -200:
            return None
        return f
    except ValueError:
        print(f'Warning: invalid numeric value {repr(value)} in column {column}; skipping')
        return None


def extract_hour(time_value):
    if not time_value:
        return None
    s = str(time_value).strip()
    try:
        return datetime.strptime(s, '%H:%M:%S').hour
    except ValueError:
        parts = s.split(':')
        if parts:
            try:
                return int(parts[0])
            except ValueError:
                pass
    return None


def main():
    data_file = find_data_file()
    if data_file is None:
        print('Error: raw_data.csv or raw_data.txt not found under data/air-quality/')
        return

    sums = {p: defaultdict(float) for p in POLLUTANTS}
    counts = {p: defaultdict(int) for p in POLLUTANTS}
    total_rows = 0
    dropped_rows = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower().strip(): v for k, v in row.items()}
            hour = extract_hour(row.get('time'))
            if hour is None:
                dropped_rows += 1
                continue
            for p in POLLUTANTS:
                v = safe_float(row.get(p), p)
                if v is not None:
                    sums[p][hour] += v
                    counts[p][hour] += 1

    all_hours = set()
    for p in POLLUTANTS:
        all_hours.update(sums[p].keys())

    summary = []
    for h in sorted(all_hours):
        entry = {'hour': h}
        for p in POLLUTANTS:
            c = counts[p].get(h, 0)
            if c > 0:
                entry[p] = round(sums[p][h] / c, 4)
                entry[f'{p}_count'] = c
            else:
                entry[p] = None
                entry[f'{p}_count'] = 0
        summary.append(entry)

    result = {
        'task_name': 'Diurnal_Average_Tracker',
        'description': 'Rolling hourly averages for each pollutant grouped by time-of-day.',
        'result_summary': summary,
        'result_generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'Diurnal_Average_Tracker_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Saved {out_file}')
    print(f'Rows processed: {total_rows}, dropped: {dropped_rows}, hours covered: {len(summary)}')


if __name__ == '__main__':
    main()