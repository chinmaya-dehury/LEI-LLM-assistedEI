"""
Task: LightTransitionCounter
Description: Detect and timestamp significant jumps in light intensity readings per mote to identify lighting state changes or environmental disturbances with O(1) space complexity.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "lab-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1')

def resolve_data_path():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / 'data').exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    data_file = root_dir / 'data' / 'lab-data' / 'raw_data.csv'
    if not data_file.exists():
        data_file = root_dir / 'data' / 'lab-data' / 'raw_data.txt'
    return data_file

def safe_float(value):
    if value is None:
        return None
    val = str(value).strip()
    if val == '' or val.upper() in ('NA', 'N/A', 'NULL', ''):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def is_significant_transition(prev_light, curr_light):
    if prev_light is None or curr_light is None:
        return False
    if prev_light <= 0 and curr_light > 100:
        return True
    if curr_light <= 0 and prev_light > 100:
        return True
    if prev_light > 0:
        ratio = abs(curr_light - prev_light) / prev_light
        if ratio >= 0.5:
            return True
    if abs(curr_light - prev_light) >= 200:
        return True
    return False

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data_file = resolve_data_path()
    if not data_file.exists():
        print(f'ERROR: Data file not found at {data_file}', file=sys.stderr)
        result = {
            'task_name': 'LightTransitionCounter',
            'description': 'Detect and timestamp significant jumps in light intensity readings per mote.',
            'result_summary': [],
            'result_generated_at': datetime.now().isoformat(),
            'error': f'Data file not found: {data_file}'
        }
        out_path = OUTPUT_DIR / 'LightTransitionCounter_result.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
        return

    prev_light_per_mote = {}
    transitions = []
    total_rows = 0
    skipped_rows = 0
    motes_seen = set()

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row_lower = {k.lower(): v for k, v in row.items()}
                    total_rows += 1

                    if 'moteid' not in row_lower or 'light' not in row_lower:
                        skipped_rows += 1
                        continue

                    mote_id = row_lower.get('moteid', '').strip()
                    if not mote_id:
                        skipped_rows += 1
                        continue

                    light_val = safe_float(row_lower.get('light'))
                    date_val = row_lower.get('date', '').strip()
                    time_val = row_lower.get('time', '').strip()
                    timestamp = f'{date_val} {time_val}'.strip() if date_val else time_val

                    motes_seen.add(mote_id)

                    prev = prev_light_per_mote.get(mote_id)
                    if light_val is not None and prev is not None:
                        if is_significant_transition(prev, light_val):
                            transitions.append({
                                'moteid': int(mote_id) if mote_id.isdigit() else mote_id,
                                'timestamp': timestamp,
                                'previous_light': round(prev, 2),
                                'current_light': round(light_val, 2),
                                'change_percent': round(abs(light_val - prev) / max(abs(prev), 0.01) * 100, 2)
                            })

                    if light_val is not None:
                        prev_light_per_mote[mote_id] = light_val

                except Exception as e:
                    skipped_rows += 1
                    continue
    except Exception as e:
        print(f'ERROR reading file: {e}', file=sys.stderr)
        result = {
            'task_name': 'LightTransitionCounter',
            'description': 'Detect and timestamp significant jumps in light intensity readings per mote.',
            'result_summary': [],
            'result_generated_at': datetime.now().isoformat(),
            'error': str(e)
        }
        out_path = OUTPUT_DIR / 'LightTransitionCounter_result.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
        return

    summary = {
        'total_rows_processed': total_rows,
        'skipped_rows': skipped_rows,
        'unique_motes': len(motes_seen),
        'total_transitions_detected': len(transitions),
        'transitions_by_mote': {},
        'sample_transitions': transitions[:20]
    }

    for t in transitions:
        mid = str(t['moteid'])
        summary['transitions_by_mote'][mid] = summary['transitions_by_mote'].get(mid, 0) + 1

    result = {
        'task_name': 'LightTransitionCounter',
        'description': 'Detect and timestamp significant jumps in light intensity readings per mote to identify lighting state changes or environmental disturbances.',
        'result_summary': [summary],
        'result_generated_at': datetime.now().isoformat()
    }

    out_path = OUTPUT_DIR / 'LightTransitionCounter_result.json'
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f'Transitions detected: {len(transitions)} across {len(motes_seen)} motes')
    print(f'Result saved to: {out_path}')

if __name__ == '__main__':
    main()