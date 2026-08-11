from datetime import datetime
"""
Task: Sensor Synchronization Gap Analysis
Description: Track epoch sequence intervals per mote to calculate the average sampling interval and automatically detect missed readings or transmission delays in the network.
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
from collections import defaultdict

def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() in ('', 'na', 'n/a', 'None'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def resolve_input_path():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    data_file = root_dir / "data" / "lab-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "lab-data" / "raw_data.txt"
    if not data_file.exists():
        print("ERROR: No input data file found.")
        sys.exit(1)
    return data_file

def parse_csv(filepath):
    records = []
    dropped = 0
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            try:
                normalized = {k.lower(): v for k, v in row.items()}
                if 'moteid' not in normalized or 'epoch' not in normalized:
                    dropped += 1
                    continue
                moteid = safe_float(normalized.get('moteid'))
                epoch = safe_float(normalized.get('epoch'))
                if moteid is None or epoch is None:
                    dropped += 1
                    continue
                records.append({'moteid': int(moteid), 'epoch': int(epoch)})
            except Exception as e:
                dropped += 1
    return records, dropped

def analyze_gaps(records):
    mote_epochs = defaultdict(list)
    for rec in records:
        mote_epochs[rec['moteid']].append(rec['epoch'])
    results = []
    total_gaps_detected = 0
    for moteid in sorted(mote_epochs.keys()):
        epochs = sorted(mote_epochs[moteid])
        if len(epochs) < 2:
            continue
        gaps = []
        for i in range(1, len(epochs)):
            gap = epochs[i] - epochs[i-1]
            gaps.append(gap)
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0
        min_gap = min(gaps) if gaps else 0
        missed_readings = [g for g in gaps if g > 1]
        total_gaps_detected += len(missed_readings)
        results.append({
            'moteid': moteid,
            'reading_count': len(epochs),
            'avg_interval': round(avg_gap, 4),
            'max_interval': max_gap,
            'min_interval': min_gap,
            'missed_readings_count': len(missed_readings),
            'total_epoch_span': epochs[-1] - epochs[0] if len(epochs) > 1 else 0
        })
    overall_avg = sum(r['avg_interval'] for r in results) / len(results) if results else 0
    summary = {
        'total_motes_analyzed': len(results),
        'overall_avg_interval': round(overall_avg, 4),
        'total_missed_readings_detected': total_gaps_detected,
        'per_mote_analysis': results
    }
    return summary

def main():
    input_path = resolve_input_path()
    print(f"Reading data from: {input_path}")
    records, dropped = parse_csv(input_path)
    print(f"Parsed {len(records)} valid records ({dropped} dropped).")
    if not records:
        print("No valid records found. Exiting.")
        sys.exit(1)
    analysis_result = analyze_gaps(records)
    output_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run2")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "sensor_synchronization_gap_analysis_result.json"
    result_json = {
        'task_name': 'Sensor Synchronization Gap Analysis',
        'description': 'Track epoch sequence intervals per mote to calculate the average sampling interval and automatically detect missed readings or transmission delays in the network.',
        'result_summary': [
            f"Analyzed {analysis_result['total_motes_analyzed']} motes",
            f"Overall average interval: {analysis_result['overall_avg_interval']} epochs",
            f"Total missed readings detected: {analysis_result['total_missed_readings_detected']}"
        ],
        'result_generated_at': __import__('datetime').datetime.now().isoformat(),
        'detailed_results': analysis_result
    }
    with open(output_file, 'w') as f:
        json.dump(result_json, f, indent=2)
    print(f"Results saved to: {output_file}")
    for m in analysis_result['per_mote_analysis'][:5]:
        print(f"  Mote {m['moteid']}: avg={m['avg_interval']}, missed={m['missed_readings_count']}")
    if len(analysis_result['per_mote_analysis']) > 5:
        print(f"  ... and {len(analysis_result['per_mote_analysis']) - 5} more motes")

if __name__ == '__main__':
    main()