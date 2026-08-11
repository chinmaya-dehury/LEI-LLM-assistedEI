"""
Task: Epoch Sequence Gap Detector
Description: Check consecutive epoch values per mote and report missing epoch numbers, helping identify delayed, dropped, or unsynchronized sensor transmissions.
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

import os
import sys
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

TASK_NAME = "Epoch Sequence Gap Detector"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run2")

MISSING_PLACEHOLDERS = {"", "na", "n/a", "None", "none", "nan", "-"}


def is_missing(value):
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_PLACEHOLDERS


def safe_int(value, field_name, row_num):
    if is_missing(value):
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError) as exc:
        print(f"[WARN] Row {row_num}: invalid {field_name} value {value!r}: {exc}", file=sys.stderr)
        return None


def find_project_root():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    return root_dir


def resolve_input_file(root_dir):
    candidates = [
        root_dir / "data" / "lab-data" / "raw_data.csv",
        root_dir / "data" / "lab-data" / "raw_data.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_epochs_by_mote(data_file, strict=False):
    epochs_by_mote = {}
    dropped_rows = 0
    total_rows = 0

    with open(data_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("[ERROR] Input file has no header row.", file=sys.stderr)
            return None, 0, 0

        required = {"moteid", "epoch"}
        lower_fields = {fn.lower() for fn in reader.fieldnames}
        if not required.issubset(lower_fields):
            print(f"[ERROR] Missing required columns: {required - lower_fields}", file=sys.stderr)
            return None, 0, 0

        for row_num, row in enumerate(reader, start=2):
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}

            moteid = safe_int(row.get("moteid"), "moteid", row_num)
            epoch = safe_int(row.get("epoch"), "epoch", row_num)

            if moteid is None or epoch is None:
                dropped_rows += 1
                if strict:
                    print(f"[WARN] Row {row_num}: dropped due to missing/invalid moteid or epoch.", file=sys.stderr)
                continue

            epochs_by_mote.setdefault(moteid, set()).add(epoch)

    return epochs_by_mote, total_rows, dropped_rows


def detect_gaps(sorted_epochs):
    gaps = []
    for i in range(1, len(sorted_epochs)):
        prev_epoch = sorted_epochs[i - 1]
        curr_epoch = sorted_epochs[i]
        if curr_epoch > prev_epoch + 1:
            gap_start = prev_epoch + 1
            gap_end = curr_epoch - 1
            gaps.append({
                "gap_start": gap_start,
                "gap_end": gap_end,
                "missing_count": gap_end - gap_start + 1
            })
    return gaps


def main():
    parser = argparse.ArgumentParser(description="Detect missing epoch sequences per mote.")
    parser.add_argument("--strict", action="store_true", help="Log every dropped row.")
    args = parser.parse_args()

    root_dir = find_project_root()
    data_file = resolve_input_file(root_dir)

    if data_file is None:
        print("[ERROR] Could not find data/lab-data/raw_data.csv or raw_data.txt.", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Reading input: {data_file}")

    epochs_by_mote, total_rows, dropped_rows = load_epochs_by_mote(data_file, strict=args.strict)
    if epochs_by_mote is None:
        sys.exit(1)

    per_mote_results = []
    total_missing_epochs = 0
    motes_with_gaps = 0
    max_sample_gaps = 5

    for moteid in sorted(epochs_by_mote.keys()):
        epochs = sorted(epochs_by_mote[moteid])
        gaps = detect_gaps(epochs)
        gap_count = len(gaps)
        missing_count = sum(g["missing_count"] for g in gaps)

        if gap_count > 0:
            motes_with_gaps += 1
            total_missing_epochs += missing_count

        sample_gaps = gaps[:max_sample_gaps]
        has_more = gap_count > max_sample_gaps

        per_mote_results.append({
            "moteid": moteid,
            "observed_epochs": len(epochs),
            "min_epoch": epochs[0] if epochs else None,
            "max_epoch": epochs[-1] if epochs else None,
            "gap_count": gap_count,
            "missing_epoch_count": missing_count,
            "sample_gaps": sample_gaps,
            "more_gaps": has_more
        })

    summary = {
        "input_file": str(data_file),
        "total_rows_read": total_rows,
        "dropped_rows": dropped_rows,
        "motes_processed": len(per_mote_results),
        "motes_with_gaps": motes_with_gaps,
        "total_missing_epochs": total_missing_epochs
    }

    result = {
        "task_name": TASK_NAME,
        "description": "Check consecutive epoch values per mote and report missing epoch numbers, helping identify delayed, dropped, or unsynchronized sensor transmissions.",
        "result_summary": [summary, {"per_mote": per_mote_results}],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{TASK_NAME}_result.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[INFO] Processed {len(per_mote_results)} motes, {motes_with_gaps} with gaps, {total_missing_epochs} missing epochs.")
    print(f"[INFO] Result saved to: {output_file}")


if __name__ == "__main__":
    main()