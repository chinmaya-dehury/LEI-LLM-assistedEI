"""
Task: Invalid Reading and Outage Monitor
Description: Count -200 sentinel values per column within rolling 24-hour windows and report the fraction of invalid readings per sensor or reference channel. This flags sensor outages and data-quality problems in near real time.
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

#!/usr/bin/env python3
import csv
import json
import math
import os
from pathlib import Path
from collections import deque
from datetime import datetime, timezone

TASK_NAME = 'Invalid Reading and Outage Monitor'
DESCRIPTION = 'Count -200 sentinel values per column within rolling 24-hour windows and report the fraction of invalid readings per sensor or reference channel.'
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1')
WINDOW_SIZE = 24
HIGH_OUTAGE_THRESHOLD = 0.2
MISSING = {'', 'na', 'n/a', 'None', 'none'}


def find_data_file():
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


def is_invalid(value):
    if value is None:
        return True
    s = str(value).strip()
    if s.lower() in MISSING:
        return True
    try:
        f = float(s)
    except ValueError:
        return True
    if math.isclose(f, -200.0):
        return True
    return False


def main():
    data_file = find_data_file()
    if data_file is None:
        print('Data file not found under data/air-quality/raw_data.csv or .txt')
        return

    numeric_cols = [
        'co(gt)', 'pt08.s1(co)', 'nmhc(gt)', 'c6h6(gt)', 'pt08.s2(nmhc)',
        'nox(gt)', 'pt08.s3(nox)', 'no2(gt)', 'pt08.s4(no2)', 'pt08.s5(o3)',
        't', 'rh', 'ah'
    ]

    counts = {c: {'invalid': 0, 'total': 0} for c in numeric_cols}
    windows = {c: deque(maxlen=WINDOW_SIZE) for c in numeric_cols}
    rolling_stats = {c: {'fractions': [], 'high_outage_count': 0} for c in numeric_cols}
    dropped = 0
    total_rows = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower().strip(): (v.strip() if v else '') for k, v in row.items()}
            date = row.get('date', '')
            time = row.get('time', '')
            if not date or not time:
                dropped += 1
                continue
            for col in numeric_cols:
                raw = row.get(col)
                invalid = is_invalid(raw)
                counts[col]['total'] += 1
                if invalid:
                    counts[col]['invalid'] += 1
                flag = 1 if invalid else 0
                dq = windows[col]
                dq.append(flag)
                if len(dq) == WINDOW_SIZE:
                    frac = sum(dq) / WINDOW_SIZE
                    rolling_stats[col]['fractions'].append(frac)
                    if frac > HIGH_OUTAGE_THRESHOLD:
                        rolling_stats[col]['high_outage_count'] += 1

    summary = []
    for col in numeric_cols:
        total = counts[col]['total']
        invalid = counts[col]['invalid']
        overall_frac = invalid / total if total else None
        fractions = rolling_stats[col]['fractions']
        avg_frac = sum(fractions) / len(fractions) if fractions else None
        max_frac = max(fractions) if fractions else None
        summary.append({
            'column': col,
            'total_readings': total,
            'invalid_readings': invalid,
            'overall_invalid_fraction': overall_frac,
            'rolling_24h_avg_invalid_fraction': avg_frac,
            'rolling_24h_max_invalid_fraction': max_frac,
            'rolling_24h_high_outage_windows': rolling_stats[col]['high_outage_count']
        })

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': summary,
        'result_generated_at': datetime.now(timezone.utc).isoformat()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f'{TASK_NAME}_result.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'Result saved to {out_path}')
    print(f'Rows processed: {total_rows}, dropped: {dropped}')


if __name__ == '__main__':
    main()