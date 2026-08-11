"""
Task: Nutrient Imbalance Detector
Description: Calculates the NPK ratio from soil Nitrogen, Phosphorus, and Potassium levels and flags significant deviations from optimal balance ranges to prevent nutrient deficiency or toxicity.
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

# Resolve input file path dynamically
curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / 'data').exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / 'data' / 'agri-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'agri-data' / 'raw_data.txt'

if not data_file.exists():
    print('ERROR: Input data file not found under data/agri-data/')
    sys.exit(1)

# Output path (CRITICAL: use specified path)
output_dir = Path('/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run1')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'Nutrient Imbalance Detector_result.json'

# Safe numeric conversion
def safe_float(val):
    if val is None:
        return None
    val = str(val).strip()
    if val == '' or val.upper() in ('NA', 'N/A', 'NULL', 'NONE'):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

# Optimal NPK balance ranges (based on common agricultural guidelines)
# N:P ratio: 2.0 to 4.0 (most crops)
# P:K ratio: 0.5 to 1.0
# N:K ratio: 1.5 to 2.5
OPTIMAL_NP_RATIO = (2.0, 4.0)
OPTIMAL_PK_RATIO = (0.5, 1.0)
OPTIMAL_NK_RATIO = (1.5, 2.5)

# Threshold for flagging imbalance
IMBALANCE_THRESHOLD = 0.1  # 10% deviation from optimal midpoint

def calculate_optimal_midpoint(low, high):
    return (low + high) / 2.0

def check_ratio_imbalance(value, opt_low, opt_high, threshold_pct=IMBALANCE_THRESHOLD):
    """Check if a ratio value deviates significantly from optimal range."""
    if value is None or value <= 0:
        return False, None
    midpoint = calculate_optimal_midpoint(opt_low, opt_high)
    range_width = opt_high - opt_low
    tolerance = range_width * threshold_pct
    if value < (opt_low - tolerance) or value > (opt_high + tolerance):
        deviation = abs(value - midpoint) / midpoint * 100 if midpoint != 0 else 0
        return True, round(deviation, 2)
    return False, None

def analyze_nutrient_imbalance():
    rows = []
    dropped_rows = 0
    total_rows = 0
    imbalance_count = 0
    imbalance_details = []

    try:
        with open(data_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys to lowercase
                row = {k.lower(): v for k, v in row.items()}
                total_rows += 1

                n_val = safe_float(row.get('n'))
                p_val = safe_float(row.get('p'))
                k_val = safe_float(row.get('k'))

                # Skip rows with missing N, P, or K
                if n_val is None or p_val is None or k_val is None:
                    dropped_rows += 1
                    continue

                # Calculate ratios
                np_ratio = n_val / p_val if p_val != 0 else None
                pk_ratio = p_val / k_val if k_val != 0 else None
                nk_ratio = n_val / k_val if k_val != 0 else None

                # Check for imbalances
                np_imbalanced, np_deviation = check_ratio_imbalance(np_ratio, *OPTIMAL_NP_RATIO)
                pk_imbalanced, pk_deviation = check_ratio_imbalance(pk_ratio, *OPTIMAL_PK_RATIO)
                nk_imbalanced, nk_deviation = check_ratio_imbalance(nk_ratio, *OPTIMAL_NK_RATIO)

                is_imbalanced = np_imbalanced or pk_imbalanced or nk_imbalanced
                if is_imbalanced:
                    imbalance_count += 1
                    details = {
                        'n_ppm': round(n_val, 2),
                        'p_ppm': round(p_val, 2),
                        'k_ppm': round(k_val, 2),
                        'np_ratio': round(np_ratio, 2) if np_ratio else None,
                        'pk_ratio': round(pk_ratio, 2) if pk_ratio else None,
                        'nk_ratio': round(nk_ratio, 2) if nk_ratio else None,
                        'imbalances': []
                    }
                    if np_imbalanced:
                        details['imbalances'].append(f'N:P ratio deviation: {np_deviation}%')
                    if pk_imbalanced:
                        details['imbalances'].append(f'P:K ratio deviation: {pk_deviation}%')
                    if nk_imbalanced:
                        details['imbalances'].append(f'N:K ratio deviation: {nk_deviation}%')
                    imbalance_details.append(details)

                rows.append({
                    'n_ppm': round(n_val, 2),
                    'p_ppm': round(p_val, 2),
                    'k_ppm': round(k_val, 2),
                    'np_ratio': round(np_ratio, 2) if np_ratio else None,
                    'pk_ratio': round(pk_ratio, 2) if pk_ratio else None,
                    'nk_ratio': round(nk_ratio, 2) if nk_ratio else None,
                    'is_imbalanced': is_imbalanced
                })

    except Exception as e:
        print(f'ERROR: Failed to read data file: {e}', file=sys.stderr)
        sys.exit(1)

    # Summary statistics
    np_ratios = [r['np_ratio'] for r in rows if r['np_ratio'] is not None]
    pk_ratios = [r['pk_ratio'] for r in rows if r['pk_ratio'] is not None]
    nk_ratios = [r['nk_ratio'] for r in rows if r['nk_ratio'] is not None]

    def calc_stats(values):
        if not values:
            return {'count': 0, 'min': None, 'max': None, 'mean': None, 'median': None}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mean_val = sum(sorted_vals) / n
        median_val = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        return {
            'count': n,
            'min': round(min(sorted_vals), 2),
            'max': round(max(sorted_vals), 2),
            'mean': round(mean_val, 2),
            'median': round(median_val, 2)
        }

    result = {
        'task_name': 'Nutrient Imbalance Detector',
        'description': 'Calculates the NPK ratio from soil Nitrogen, Phosphorus, and Potassium levels and flags significant deviations from optimal balance ranges to prevent nutrient deficiency or toxicity.',
        'result_summary': [
            f'Total rows analyzed: {total_rows}',
            f'Rows with complete NPK data: {len(rows)}',
            f'Dropped rows (missing N/P/K): {dropped_rows}',
            f'Imbalanced nutrient profiles detected: {imbalance_count} ({round(imbalance_count/max(len(rows),1)*100, 1)}%)',
            f'N:P ratio stats: {calc_stats(np_ratios)}',
            f'P:K ratio stats: {calc_stats(pk_ratios)}',
            f'N:K ratio stats: {calc_stats(nk_ratios)}',
            f'Optimal N:P range: {OPTIMAL_NP_RATIO[0]}-{OPTIMAL_NP_RATIO[1]}',
            f'Optimal P:K range: {OPTIMAL_PK_RATIO[0]}-{OPTIMAL_PK_RATIO[1]}',
            f'Optimal N:K range: {OPTIMAL_NK_RATIO[0]}-{OPTIMAL_NK_RATIO[1]}'
        ],
        'imbalance_details': imbalance_details[:50],
        'result_generated_at': datetime.now().isoformat()
    }

    try:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f'Results saved to: {output_file}')
    except Exception as e:
        print(f'ERROR: Failed to write output: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    analyze_nutrient_imbalance()