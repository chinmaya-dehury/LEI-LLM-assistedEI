import json
import csv
"""
Task: Low-Concentration Sensor Baseline Tracker
Description: Track the median resistance of each PT08 sensor during periods when its corresponding reference concentration is near its minimum valid value, providing a lightweight indicator of sensor baseline drift over time.
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
import sys, csv, json, argparse
from pathlib import Path
from datetime import datetime, timezone
from statistics import median

LOW_FRAC = 0.20
MAPPINGS = [
    ('co(gt)', 'pt08.s1(co)'),
    ('nmhc(gt)', 'pt08.s2(nmhc)'),
    ('nox(gt)', 'pt08.s3(nox)'),
    ('no2(gt)', 'pt08.s4(no2)'),
]

def find_project_root():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / 'data').exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    return root

def resolve_input(root):
    for name in ('raw_data.csv', 'raw_data.txt'):
        p = root / 'data' / 'air-quality' / name
        if p.exists():
            return p
    return None

def is_missing(value):
    if value is None:
        return True
    s = str(value).strip()
    if s == '':
        return True
    if s.upper() in ('NA', 'N/A', 'NULL', 'NONE'):
        return True
    if s == '-200':
        return True
    return False

def to_float(value, column):
    if is_missing(value):
        return None
    try:
        return float(value)
    except Exception as exc:
        print(f'Warning: bad numeric {column}={value!r}: {exc}', file=sys.stderr)
        return None

def month_key(date_str, time_str):
    try:
        dt = datetime.strptime(f'{date_str.strip()} {time_str.strip()}', '%d-%m-%Y %H:%M:%S')
        return dt.strftime('%Y-%m')
    except Exception:
        return 'unknown'

def main():
    parser = argparse.ArgumentParser(description='Track PT08 sensor baselines during low reference concentrations.')
    parser.add_argument('--strict', action='store_true', help='Require all mapped columns to be present and valid.')
    args = parser.parse_args()

    root = find_project_root()
    data_file = resolve_input(root)
    if not data_file:
        print('Error: raw_data.csv/txt not found under data/air-quality/', file=sys.stderr)
        sys.exit(1)

    out_dir = Path('/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2')
    out_dir.mkdir(parents=True, exist_ok=True)

    task_name = 'Low-Concentration Sensor Baseline Tracker'
    ref_values = {ref: [] for ref, _ in MAPPINGS}
    overall = {sens: [] for _, sens in MAPPINGS}
    monthly = {}
    total = 0
    dropped = 0

    with open(data_file, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            total += 1
            row = {k.lower().strip(): v for k, v in raw.items()}
            parsed = {}
            row_ok = True
            for ref, sens in MAPPINGS:
                if ref not in row or sens not in row:
                    if args.strict:
                        row_ok = False
                        break
                    continue
                rv = to_float(row[ref], ref)
                sv = to_float(row[sens], sens)
                if rv is None or sv is None:
                    if args.strict:
                        row_ok = False
                        break
                    continue
                parsed[(ref, sens)] = (rv, sv)
                ref_values[ref].append(rv)
            if not row_ok or not parsed:
                dropped += 1
                continue

            month = month_key(row.get('date', ''), row.get('time', ''))
            monthly.setdefault(month, {sens: [] for _, sens in MAPPINGS})
            for (ref, sens), (rv, sv) in parsed.items():
                monthly[month][sens].append((rv, sv))
                overall[sens].append((rv, sv))

    thresholds = {}
    for ref, vals in ref_values.items():
        if not vals:
            thresholds[ref] = None
            continue
        mn = min(vals)
        mx = max(vals)
        thresholds[ref] = mn + LOW_FRAC * (mx - mn)

    summary = []
    for ref, sens in MAPPINGS:
        thr = thresholds[ref]
        if thr is None:
            continue
        overall_low = [v for r, v in overall[sens] if r <= thr]
        overall_median = median(overall_low) if overall_low else None
        monthly_stats = []
        for m in sorted(monthly):
            vals = [v for r, v in monthly[m][sens] if r <= thr]
            if vals:
                monthly_stats.append({'month': m, 'count': len(vals), 'median': round(median(vals), 4)})
        summary.append({
            'sensor': sens,
            'reference': ref,
            'low_threshold': round(thr, 4),
            'overall_low_count': len(overall_low),
            'overall_low_median': round(overall_median, 4) if overall_median is not None else None,
            'monthly_low_medians': monthly_stats,
        })

    result = {
        'task_name': task_name,
        'description': 'Median PT08 sensor resistance during low reference-concentration periods, tracked monthly to expose baseline drift.',
        'result_summary': summary,
        'result_generated_at': datetime.now(timezone.utc).isoformat() + 'Z',
        'records_total': total,
        'records_dropped': dropped,
    }

    out_file = out_dir / f'{task_name}_result.json'
    with open(out_file, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=2)
    print(f'Saved {out_file}')
    print(f'Records: total={total}, dropped={dropped}')
    for item in summary:
        print(item['sensor'] + ': threshold=' + str(item['low_threshold']) + ', overall_median=' + str(item['overall_low_median']) + ', months=' + str(len(item['monthly_low_medians'])))

if __name__ == '__main__':
    main()