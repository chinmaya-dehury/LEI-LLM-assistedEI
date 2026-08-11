"""
Task: Fertilizer Overuse Indicator
Description: Compare Fertilizer_Usage against NPK levels and crop density to flag potential over-fertilization, helping reduce cost and environmental runoff.
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
import math
from datetime import datetime
from pathlib import Path

TASK_NAME = "Fertilizer Overuse Indicator"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1")
OUTPUT_FILE = OUTPUT_DIR / "fertilizer_overuse_indicator_result.json"

REQUIRED_COLS = {"n", "p", "k", "fertilizer_usage", "crop_density", "label"}
MISSING_MARKERS = {"", "na", "n/a", "None", "none"}
OVERUSE_THRESHOLD = 1.5


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
    if s.lower() in MISSING_MARKERS:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Row {row_idx}: invalid numeric value '{value}' in column '{col_name}', skipping field.", file=sys.stderr)
        return None


def main():
    data_file = find_data_file()
    if data_file is None:
        print("Error: raw_data.csv or raw_data.txt not found under data/agri-data/", file=sys.stderr)
        sys.exit(1)

    rows = []
    skipped_rows = 0
    with data_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            row = {k.lower(): v for k, v in row.items()}
            if not REQUIRED_COLS.issubset(row.keys()):
                print(f"Row {idx}: missing required columns, skipping.", file=sys.stderr)
                skipped_rows += 1
                continue
            n = to_float(row.get("n"), "N", idx)
            p = to_float(row.get("p"), "P", idx)
            k = to_float(row.get("k"), "K", idx)
            fert = to_float(row.get("fertilizer_usage"), "Fertilizer_Usage", idx)
            density = to_float(row.get("crop_density"), "Crop_Density", idx)
            label = (row.get("label") or "").strip()
            if None in (n, p, k, fert, density) or not label:
                skipped_rows += 1
                continue
            if density <= 0 or (n + p + k) <= 0:
                skipped_rows += 1
                continue
            expected = (n + p + k) / density
            ratio = fert / expected if expected > 0 else math.nan
            rows.append({
                "row_index": idx,
                "label": label,
                "n": n,
                "p": p,
                "k": k,
                "npk_sum": n + p + k,
                "crop_density": density,
                "fertilizer_usage": fert,
                "expected_usage": expected,
                "ratio": ratio,
            })

    if not rows:
        print("No valid rows to analyze.", file=sys.stderr)
        sys.exit(1)

    # Per-crop median ratios for relative flagging
    label_ratios = {}
    for r in rows:
        label_ratios.setdefault(r["label"], []).append(r["ratio"])
    label_median = {
        label: sorted(vals)[len(vals) // 2] if vals else 0.0
        for label, vals in label_ratios.items()
    }

    flagged = []
    for r in rows:
        absolute_flag = r["ratio"] > OVERUSE_THRESHOLD
        relative_flag = r["ratio"] > label_median.get(r["label"], 0.0) * OVERUSE_THRESHOLD
        if absolute_flag or relative_flag:
            reasons = []
            if absolute_flag:
                reasons.append(f"ratio {r['ratio']:.2f} exceeds global threshold {OVERUSE_THRESHOLD}")
            if relative_flag:
                reasons.append(f"ratio {r['ratio']:.2f} exceeds crop median x {OVERUSE_THRESHOLD}")
            flagged.append({
                "row_index": r["row_index"],
                "label": r["label"],
                "npk_sum": round(r["npk_sum"], 2),
                "crop_density": round(r["crop_density"], 2),
                "fertilizer_usage": round(r["fertilizer_usage"], 2),
                "expected_usage": round(r["expected_usage"], 2),
                "ratio": round(r["ratio"], 2),
                "reasons": reasons,
            })

    per_label_summary = []
    for label in sorted(label_ratios.keys()):
        vals = label_ratios[label]
        flagged_count = sum(1 for f in flagged if f["label"] == label)
        per_label_summary.append({
            "label": label,
            "row_count": len(vals),
            "median_ratio": round(sorted(vals)[len(vals) // 2], 2),
            "flagged_count": flagged_count,
        })

    result = {
        "task_name": TASK_NAME,
        "description": "Compare Fertilizer_Usage against NPK levels and crop density to flag potential over-fertilization, helping reduce cost and environmental runoff.",
        "result_summary": [
            {"metric": "total_rows", "value": len(rows)},
            {"metric": "skipped_rows", "value": skipped_rows},
            {"metric": "global_overuse_threshold", "value": OVERUSE_THRESHOLD},
            {"metric": "flagged_rows", "value": len(flagged)},
            {"metric": "flagged_fraction", "value": round(len(flagged) / len(rows), 4) if rows else 0.0},
            {"metric": "per_label_summary", "value": per_label_summary},
            {"metric": "top_flagged", "value": flagged[:10]},
        ],
        "result_generated_at": datetime.utcnow().isoformat() + "Z",
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved result to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()