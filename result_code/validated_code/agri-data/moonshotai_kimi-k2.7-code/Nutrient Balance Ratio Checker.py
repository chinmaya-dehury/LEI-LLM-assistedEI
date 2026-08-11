"""
Task: Nutrient Balance Ratio Checker
Description: Evaluate the Nutrient Balance Ratio (NBR) between nitrogen, phosphorus, and potassium to detect nutrient imbalances that could limit yield.
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

#!/usr/bin/env python3
"""Nutrient Balance Ratio Checker for agri-data.

Evaluates NBR between N, P, K to detect nutrient imbalances.
NBR is computed as the ratio of the geometric mean to the arithmetic mean
of the three macronutrients, yielding a value between 0 and 1.
Values closer to 1 indicate better balance.
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = "Nutrient Balance Ratio Checker"
DESCRIPTION = "Evaluate the Nutrient Balance Ratio (NBR) between nitrogen, phosphorus, and potassium to detect nutrient imbalances that could limit yield."

OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2")

MISSING = {"", "na", "n/a", "None", "none"}


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ("raw_data.csv", "raw_data.txt"):
        candidate = root_dir / "data" / "agri-data" / name
        if candidate.exists():
            return candidate
    return None


def to_float(value, col_name, row_idx):
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Row {row_idx}: cannot convert {col_name}='{value}' to float; treating as missing.", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--strict", action="store_true", help="Skip rows with missing N, P, or K.")
    parser.add_argument("--threshold", type=float, default=0.75, help="NBR threshold below which a row is flagged imbalanced.")
    args = parser.parse_args()

    data_file = find_data_file()
    if data_file is None:
        print("Data file not found at data/agri-data/raw_data.csv or .txt", file=sys.stderr)
        sys.exit(1)

    required = {"n", "p", "k", "label"}
    rows_total = 0
    rows_dropped = 0
    rows_processed = 0
    imbalanced_count = 0
    per_crop = {}

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("CSV has no headers.", file=sys.stderr)
            sys.exit(1)
        fieldnames = [c.lower() for c in reader.fieldnames]
        missing_cols = required - set(fieldnames)
        if missing_cols:
            print(f"Missing required columns: {sorted(missing_cols)}", file=sys.stderr)
            sys.exit(1)

        for idx, raw_row in enumerate(reader, start=2):
            rows_total += 1
            row = {k.lower(): v for k, v in raw_row.items()}
            n = to_float(row.get("n"), "N", idx)
            p = to_float(row.get("p"), "P", idx)
            k = to_float(row.get("k"), "K", idx)
            label = (row.get("label") or "").strip()

            if None in (n, p, k) or label in MISSING:
                rows_dropped += 1
                if args.strict:
                    continue
                continue

            if n < 0 or p < 0 or k < 0:
                print(f"Row {idx}: negative nutrient value skipped.", file=sys.stderr)
                rows_dropped += 1
                continue

            arithmetic = (n + p + k) / 3.0
            if arithmetic <= 0:
                rows_dropped += 1
                continue

            product = n * p * k
            if product <= 0:
                nbr = 0.0
            else:
                nbr = math.pow(product, 1.0 / 3.0) / arithmetic

            rows_processed += 1
            imbalanced = nbr < args.threshold
            if imbalanced:
                imbalanced_count += 1

            if label not in per_crop:
                per_crop[label] = {"count": 0, "nbr_sum": 0.0, "imbalanced": 0}
            per_crop[label]["count"] += 1
            per_crop[label]["nbr_sum"] += nbr
            if imbalanced:
                per_crop[label]["imbalanced"] += 1

    if rows_processed == 0:
        print("No valid rows with N, P, K, and Label found.", file=sys.stderr)
        sys.exit(1)

    summary = []
    summary.append(f"Total rows read: {rows_total}")
    summary.append(f"Rows processed: {rows_processed}")
    summary.append(f"Rows dropped/invalid: {rows_dropped}")
    summary.append(f"Imbalance threshold: {args.threshold}")
    summary.append(f"Total imbalanced rows: {imbalanced_count} ({100.0 * imbalanced_count / rows_processed:.2f}%)")
    summary.append("Average NBR by crop:")
    for label in sorted(per_crop):
        stats = per_crop[label]
        avg_nbr = stats["nbr_sum"] / stats["count"]
        summary.append(f"  {label}: count={stats['count']}, avg_nbr={avg_nbr:.4f}, imbalanced={stats['imbalanced']}")
    overall_nbr = sum(per_crop[l]["nbr_sum"] for l in per_crop) / rows_processed
    summary.append(f"Overall average NBR: {overall_nbr:.4f}")

    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": summary,
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{TASK_NAME}_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved result to {out_path}")
    for line in summary:
        print(line)


if __name__ == "__main__":
    main()