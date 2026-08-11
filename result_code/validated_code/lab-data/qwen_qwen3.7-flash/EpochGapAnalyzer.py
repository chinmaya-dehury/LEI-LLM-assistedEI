from datetime import datetime
"""
Task: EpochGapAnalyzer
Description: Identify missing or delayed readings by calculating differences between consecutive epoch values per mote to assess network synchronization health.
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

def safe_int(value):
    """Safely convert a value to integer."""
    if not value or str(value).strip() in ('', 'NA', 'N/A', 'None'):
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None

def main():
    # Resolve input file path dynamically
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
        print('Error: No data file found in data/lab-data/')
        sys.exit(1)

    print(f'Reading data from: {data_file}')

    # Collect epochs per mote
    mote_epochs = defaultdict(list)
    dropped_rows = 0
    total_rows = 0

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                # Normalize column names to lowercase
                row = {k.lower(): v for k, v in row.items()}

                # Extract moteid and epoch
                moteid = safe_int(row.get('moteid'))
                epoch = safe_int(row.get('epoch'))

                if moteid is None or epoch is None:
                    dropped_rows += 1
                    continue

                mote_epochs[moteid].append(epoch)
    except Exception as e:
        print(f'Error reading data file: {e}')
        sys.exit(1)

    print(f'Processed {total_rows} rows, dropped {dropped_rows} invalid rows.')
    print(f'Found {len(mote_epochs)} unique motes.')

    # Analyze epoch gaps per mote
    results = []
    threshold = 5  # Gaps larger than this indicate potential issues

    for moteid in sorted(mote_epochs.keys()):
        epochs = sorted(mote_epochs[moteid])
        if len(epochs) < 2:
            continue

        gaps = [epochs[i + 1] - epochs[i] for i in range(len(epochs) - 1)]

        mean_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
        min_gap = min(gaps)
        large_gaps = [g for g in gaps if g > threshold]

        results.append({
            'moteid': moteid,
            'num_readings': len(epochs),
            'mean_epoch_gap': round(mean_gap, 2),
            'max_epoch_gap': max_gap,
            'min_epoch_gap': min_gap,
            'large_gap_count': len(large_gaps),
            'large_gap_threshold': threshold
        })

    # Build output result
    output_dir = Path('/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'EpochGapAnalyzer_result.json'

    result = {
        'task_name': 'EpochGapAnalyzer',
        'description': 'Identify missing or delayed readings by calculating differences between consecutive epoch values per mote to assess network synchronization health.',
        'result_summary': results,
        'result_generated_at': __import__('datetime').datetime.now().isoformat(),
        'metadata': {
            'total_rows_processed': total_rows,
            'dropped_rows': dropped_rows,
            'mot_analyzed': len(results),
            'gap_threshold': threshold
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f'Results saved to: {output_path}')
    print(f'Analyzed {len(results)} motes for epoch gap anomalies.')

if __name__ == '__main__':
    main()