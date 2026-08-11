"""
Task: EpochSequenceGapAnalyzer
Description: Track the monotonically increasing epoch counter per mote to identify missing sequence numbers, indicating potential packet loss or transmission dropouts.
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

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def main():
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
    if not data_file.exists():
        print('ERROR: No raw_data.csv or raw_data.txt found under data/lab-data/')
        sys.exit(1)

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run2')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'EpochSequenceGapAnalyzer_result.json'

    mote_epochs = {}
    total_rows = 0
    skipped_rows = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                row_lower = {k.lower(): v for k, v in row.items()}
                moteid_raw = row_lower.get('moteid', '').strip()
                epoch_raw = row_lower.get('epoch', '').strip()
                if not moteid_raw or not epoch_raw:
                    skipped_rows += 1
                    continue
                moteid = safe_int(moteid_raw)
                epoch = safe_int(epoch_raw)
                if moteid is None or epoch is None:
                    skipped_rows += 1
                    continue
                if moteid not in mote_epochs:
                    mote_epochs[moteid] = []
                mote_epochs[moteid].append(epoch)
    except Exception as e:
        print(f'ERROR reading data file: {e}')
        sys.exit(1)

    gap_results = {}
    total_gaps_found = 0
    max_gap_mote = None
    max_gap_count = 0

    for moteid in sorted(mote_epochs.keys()):
        epochs = sorted(set(mote_epochs[moteid]))
        if len(epochs) < 2:
            gap_results[str(moteid)] = {'gaps': [], 'gap_count': 0, 'min_epoch': epochs[0] if epochs else None, 'max_epoch': epochs[0] if epochs else None}
            continue
        gaps = []
        for i in range(1, len(epochs)):
            expected = epochs[i - 1] + 1
            actual = epochs[i]
            if actual > expected:
                missing = list(range(expected, actual))
                gaps.extend(missing)
        gap_count = len(gaps)
        total_gaps_found += gap_count
        if gap_count > max_gap_count:
            max_gap_count = gap_count
            max_gap_mote = moteid
        gap_results[str(moteid)] = {
            'gaps': gaps[:100],
            'gap_count': gap_count,
            'min_epoch': epochs[0],
            'max_epoch': epochs[-1],
            'unique_epochs_read': len(epochs),
            'expected_range_size': epochs[-1] - epochs[0] + 1
        }

    summary = [
        f'Total rows processed: {total_rows}',
        f'Skipped rows (missing/invalid): {skipped_rows}',
        f'Total motes analyzed: {len(mote_epochs)}',
        f'Total gaps detected across all motes: {total_gaps_found}',
        f'Most affected mote: {max_gap_mote} with {max_gap_count} gaps'
    ]

    result = {
        'task_name': 'EpochSequenceGapAnalyzer',
        'description': 'Track the monotonically increasing epoch counter per mote to identify missing sequence numbers, indicating potential packet loss or transmission dropouts.',
        'result_summary': summary,
        'result_generated_at': datetime.utcnow().isoformat() + 'Z',
        'per_mote_analysis': gap_results
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as out_f:
            json.dump(result, out_f, indent=2)
        print(f'Result saved to {output_path}')
    except Exception as e:
        print(f'ERROR writing output: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()