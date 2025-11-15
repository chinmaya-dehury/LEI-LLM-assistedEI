import os
import json
import pandas as pd
import numpy as np
import datetime
from pathlib import Path


def iso_now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def main():
    data_type = "air_quality"
    task_name = "timestamp_crossfield_consistency_check"
    description = (
        "Cross-validate timestamp_unix against timestamp_utc (convert UTC to epoch and ensure |diff| <= 1s) and verify timestamps are monotonically non-decreasing; report indices and counts of mismatches."
    )
    data_path = os.path.join("data", data_type, "raw_data.csv")
    out_dir = os.path.join("output", data_type)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    result_path = os.path.join(out_dir, f"{task_name}_result.json")

    result_summary = []

    def add_result(name, value, desc):
        result_summary.append({
            "name": name,
            "value": value,
            "description": desc,
            "timestamp": iso_now(),
        })

    try:
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at {data_path}")

        df = pd.read_csv(data_path)
        required_cols = ["timestamp_unix", "timestamp_utc"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            add_result("missing_columns", missing, "Required columns not found in CSV.")
        else:
            # Parse fields
            unix = pd.to_numeric(df["timestamp_unix"], errors="coerce")
            utc_ts = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
            # Convert UTC timestamp to epoch seconds
            epoch_utc = (utc_ts - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()

            # Parsing diagnostics
            add_result("parse_nan_unix_count", int(unix.isna().sum()), "Rows where timestamp_unix could not be parsed to numeric.")
            add_result("parse_nan_utc_count", int(utc_ts.isna().sum()), "Rows where timestamp_utc could not be parsed to datetime.")

            # Cross-field consistency within 1 second
            diff = (epoch_utc - unix).abs()
            valid_diff_mask = diff.notna()
            mismatch_mask = valid_diff_mask & (diff > 1.0)
            mismatch_indices = df.index[mismatch_mask].tolist()
            add_result("crossfield_mismatch_count", int(mismatch_mask.sum()), "Count of rows where |epoch(UTC) - timestamp_unix| > 1 second.")
            add_result("crossfield_mismatch_indices", mismatch_indices, "Row indices with |epoch(UTC) - timestamp_unix| > 1 second.")

            # Rows where either field was not parseable
            unparseable_mask = unix.isna() | epoch_utc.isna()
            unparseable_indices = df.index[unparseable_mask].tolist()
            add_result("unparseable_timestamp_rows_count", int(unparseable_mask.sum()), "Rows where either timestamp_unix or timestamp_utc failed to parse.")
            add_result("unparseable_timestamp_rows_indices", unparseable_indices, "Indices of rows with unparseable timestamps.")

            # Monotonicity checks (non-decreasing)
            unix_diff = unix.diff()
            utc_epoch_diff = epoch_utc.diff()
            unix_viol_mask = unix_diff < 0
            utc_viol_mask = utc_epoch_diff < 0
            unix_viol_indices = df.index[unix_viol_mask.fillna(False)].tolist()
            utc_viol_indices = df.index[utc_viol_mask.fillna(False)].tolist()
            add_result("monotonic_violations_unix_count", int(np.nansum(unix_viol_mask.astype(float))), "Count of positions where timestamp_unix decreased vs previous row.")
            add_result("monotonic_violations_unix_indices", unix_viol_indices, "Row indices where timestamp_unix decreased.")
            add_result("monotonic_violations_utc_count", int(np.nansum(utc_viol_mask.astype(float))), "Count of positions where epoch(UTC) decreased vs previous row.")
            add_result("monotonic_violations_utc_indices", utc_viol_indices, "Row indices where epoch(UTC) decreased.")

            # Time range info
            if len(df) > 0:
                try:
                    tmin = utc_ts.min()
                    tmax = utc_ts.max()
                    add_result("utc_time_range", {"start": None if pd.isna(tmin) else tmin.isoformat(), "end": None if pd.isna(tmax) else tmax.isoformat()}, "Minimum and maximum timestamp_utc observed.")
                except Exception:
                    pass

        output_obj = {
            "task_name": task_name,
            "description": description,
            "result_summary": result_summary,
            "result_generated_at": iso_now(),
        }
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(output_obj, f, ensure_ascii=False, indent=2)
        # Also print a concise console summary
        print(json.dumps(output_obj, ensure_ascii=False))
    except Exception as e:
        err_obj = {
            "task_name": task_name,
            "description": description,
            "result_summary": [{
                "name": "error",
                "value": str(e),
                "description": "Unhandled exception during task execution.",
                "timestamp": iso_now(),
            }],
            "result_generated_at": iso_now(),
        }
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(err_obj, f, ensure_ascii=False, indent=2)
        print(json.dumps(err_obj, ensure_ascii=False))


if __name__ == "__main__":
    main()
