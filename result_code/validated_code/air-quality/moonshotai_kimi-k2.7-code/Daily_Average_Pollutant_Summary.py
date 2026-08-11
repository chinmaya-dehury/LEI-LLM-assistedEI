"""
Task: Daily_Average_Pollutant_Summary
Description: Aggregate hourly CO, NMHC, C6H6, NOx, and NO2 ground-truth concentrations into daily averages and report day-over-day changes for trend monitoring.
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
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = 'Daily_Average_Pollutant_Summary'
OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2')
OUTPUT_FILE = OUTPUT_DIR / f'{TASK_NAME}_result.json'

POLLUTANTS = ['co(gt)', 'nmhc(gt)', 'c6h6(gt)', 'nox(gt)', 'no2(gt)']


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ['raw_data.csv', 'raw_data.txt']:
        candidate = root_dir / 'data' / 'air-quality' / name
        if candidate.exists():
            return candidate
    return None


def is_missing(raw):
    if raw is None:
        return True
    s = str(raw).strip()
    return s == '' or s.upper() in {'NA', 'N/A', 'NULL', 'NONE'}


def to_float(raw, col):
    if is_missing(raw):
        return None
    s = str(raw).strip()
    try:
        v = float(s)
    except Exception:
        print(f'Warning: invalid numeric value in {col}: {raw!r}', file=sys.stderr)
        return None
    # Treat the common -200 sentinel used in this dataset as missing.
    if v <= -199:
        return None
    return v


def parse_date(raw):
    s = str(raw).strip()
    for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y']:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def main():
    strict = '--strict' in sys.argv
    data_file = find_data_file()
    if data_file is None:
        print('Error: raw_data.csv/txt not found under data/air-quality/', file=sys.stderr)
        sys.exit(1)

    daily = defaultdict(lambda: {p: [] for p in POLLUTANTS})
    dropped = 0
    total = 0

    with open(data_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower().strip(): v for k, v in row.items() if k is not None}
            if 'date' not in row:
                dropped += 1
                print(f'Warning: row {total} missing Date; skipped', file=sys.stderr)
                continue
            d = parse_date(row.get('date'))
            if d is None:
                dropped += 1
                print('Warning: row %s has unparseable date %r; skipped' % (total, row.get('date')), file=sys.stderr)
                continue
            if strict:
                missing_any = False
                for p in POLLUTANTS:
                    if p not in row or to_float(row.get(p), p) is None:
                        missing_any = True
                        break
                if missing_any:
                    dropped += 1
                    continue
            for p in POLLUTANTS:
                v = to_float(row.get(p), p)
                if v is not None:
                    daily[d][p].append(v)

    if not daily:
        print('Error: no valid daily data found', file=sys.stderr)
        sys.exit(1)

    summary = []
    sorted_dates = sorted(daily.keys())
    prev = None
    for d in sorted_dates:
        avgs = {}
        for p in POLLUTANTS:
            vals = daily[d][p]
            avgs[p] = round(sum(vals) / len(vals), 4) if vals else None
        entry = {'date': d.isoformat(), 'averages': avgs}
        if prev is not None:
            changes = {}
            for p in POLLUTANTS:
                cur = avgs[p]
                pr = prev['averages'][p]
                if cur is not None and pr is not None:
                    changes[p] = round(cur - pr, 4)
                else:
                    changes[p] = None
            entry['changes_from_previous_day'] = changes
        summary.append(entry)
        prev = entry

    result = {
        'task_name': TASK_NAME,
        'description': 'Aggregate hourly CO, NMHC, C6H6, NOx, and NO2 ground-truth concentrations into daily averages and report day-over-day changes for trend monitoring.',
        'result_summary': summary,
        'result_generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f'Saved {len(summary)} daily summaries to {OUTPUT_FILE}')
    if dropped:
        print(f'Rows dropped/cleaned: {dropped}/{total}')


if __name__ == '__main__':
    main()