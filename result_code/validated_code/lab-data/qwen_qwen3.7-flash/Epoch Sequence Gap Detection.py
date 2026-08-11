"""
Task: Epoch Sequence Gap Detection
Description: Scan the monotonically increasing epoch values for each mote to identify missing sequence numbers or transmission delays, ensuring data integrity for time-series analysis with minimal processing overhead.
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
from pathlib import Path
from collections import defaultdict

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
        print('Error: Input data file not found.')
        exit(1)

    mote_epochs = defaultdict(list)
    rows_processed = 0
    rows_skipped = 0

    try:
        with open(data_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.lower(): v for k, v in row.items()}
                try:
                    moteid_raw = row.get('moteid', '')
                    epoch_raw = row.get('epoch', '')
                    if not moteid_raw or not epoch_raw:
                        rows_skipped += 1
                        continue
                    moteid = safe_int(moteid_raw.strip())
                    epoch = safe_int(epoch_raw.strip())
                    if moteid is None or epoch is None:
                        rows_skipped += 1
                        continue
                    mote_epochs[moteid].append(epoch)
                    rows_processed += 1
                except Exception as e:
                    rows_skipped += 1
                    continue
    except Exception as e:
        print(f'Error reading file: {e}')
        exit(1)

    gaps_found = []
    total_gaps = 0
    max_gap_per_mote = {}

    for moteid in sorted(mote_epochs.keys()):
        epochs = sorted(set(mote_epochs[moteid]))
        mote_gaps = []
        for i in range(1, len(epochs)):
            expected = epochs[i - 1] + 1
            actual = epochs[i]
            if actual != expected:
                gap_size = actual - expected - 1
                if gap_size > 0:
                    gap_entry = {
                        'moteid': moteid,
                        'last_seen_epoch': epochs[i - 1],
                        'next_seen_epoch': actual,
                        'missing_count': gap_size
                    }
                    mote_gaps.append(gap_entry)
                    total_gaps += gap_size
        if mote_gaps:
            gaps_found.extend(mote_gaps)
            max_gap_per_mote[moteid] = max(g['missing_count'] for g in mote_gaps)

    summary_lines = [
        f'Total rows processed: {rows_processed}',
        f'Rows skipped due to invalid data: {rows_skipped}',
        f'Total motes analyzed: {len(mote_epochs)}',
        f'Motes with gaps: {len(max_gap_per_mote)}',
        f'Total missing epochs detected: {total_gaps}'
    ]

    top_gaps = sorted(gaps_found, key=lambda x: x['missing_count'], reverse=True)[:10]

    result = {
        'task_name': 'Epoch_Sequence_Gap_Detection',
        'description': 'Scan the monotonically increasing epoch values for each mote to identify missing sequence numbers or transmission delays.',
        'result_summary': summary_lines,
        'top_10_largest_gaps': top_gaps,
        'max_gap_per_mote': max_gap_per_mote,
        'result_generated_at': '2024-01-01T00:00:00Z'
    }

    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run1')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'Epoch_Sequence_Gap_Detection_result.json'

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f'Results saved to {output_file}')
    for line in summary_lines:
        print(line)

if __name__ == '__main__':
    main()