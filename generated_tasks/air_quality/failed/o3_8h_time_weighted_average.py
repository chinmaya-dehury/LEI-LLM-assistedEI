import os
import json
import argparse
from datetime import datetime, timedelta, timezone
import pandas as pd

TASK_NAME = "o3_8h_time_weighted_average"


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def compute_8h_twa_o3(df, window_hours=8, coverage_min=0.75):
    # Prepare
    df = df.copy()
    if "timestamp_utc" not in df.columns or "o3" not in df.columns:
        raise ValueError("Required columns 'timestamp_utc' and 'o3' not found")
    df = df.dropna(subset=["timestamp_utc", "o3"])
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce")
    df["o3"] = pd.to_numeric(df["o3"], errors="coerce")
    df = df.dropna(subset=["timestamp_utc", "o3"]).sort_values("timestamp_utc").reset_index(drop=True)

    if len(df) < 2:
        return []  # cannot compute durations without at least two points

    times = df["timestamp_utc"].to_list()
    vals = df["o3"].to_list()
    window_seconds = window_hours * 3600.0

    windows = []
    for i, t0 in enumerate(times):
        t_end = t0 + timedelta(hours=window_hours)
        covered = 0.0
        weighted_sum = 0.0

        # Iterate segments j: [times[j], times[j+1])
        for j in range(i, len(times) - 1):
            s = times[j]
            e = times[j + 1]
            if s >= t_end:
                break
            seg_start = max(s, t0)
            seg_end = min(e, t_end)
            if seg_end > seg_start:
                dur = (seg_end - seg_start).total_seconds()
                covered += dur
                weighted_sum += vals[j] * dur
            if e >= t_end:
                break

        coverage_ratio = covered / window_seconds if window_seconds > 0 else 0.0
        if covered > 0 and coverage_ratio >= coverage_min:
            twa = weighted_sum / covered  # average over covered time only
            windows.append({
                "start": t0,
                "end": t_end,
                "twa": float(twa),
                "covered_seconds": covered,
                "coverage_ratio": float(coverage_ratio)
            })

    return windows


def main():
    parser = argparse.ArgumentParser(description="Compute time-weighted 8h mean of O3 with actual timestamp gaps.")
    parser.add_argument("--data-type", default="air_quality", help="Data type directory under data/ and output/.")
    parser.add_argument("--window-hours", type=float, default=8.0, help="Window size in hours")
    parser.add_argument("--coverage-min", type=float, default=0.75, help="Minimum coverage ratio (0-1)")
    parser.add_argument("--guideline", type=float, default=100.0, help="WHO 8h guideline for O3 (ug/m3)")
    args = parser.parse_args()

    data_path = os.path.join("data", args.data_type, "raw_data.csv")
    output_dir = os.path.join("output", args.data_type)
    ensure_dir(output_dir)
    out_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")

    if not os.path.isfile(data_path):
        print(f"Data file not found: {data_path}")
        result = {
            "task_name": TASK_NAME,
            "description": "Compute time-weighted 8h O3 mean with coverage requirement.",
            "result_summary": [{
                "name": "error",
                "value": f"missing file {data_path}",
                "description": "Input data file not found.",
                "timestamp": iso_now()
            }],
            "result_generated_at": iso_now()
        }
        with open(out_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    try:
        df = pd.read_csv(data_path, parse_dates=["timestamp_utc"], infer_datetime_format=True)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        result = {
            "task_name": TASK_NAME,
            "description": "Compute time-weighted 8h O3 mean with coverage requirement.",
            "result_summary": [{
                "name": "error",
                "value": str(e),
                "description": "CSV read/parse error.",
                "timestamp": iso_now()
            }],
            "result_generated_at": iso_now()
        }
        with open(out_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    try:
        windows = compute_8h_twa_o3(df, window_hours=float(args.window_hours), coverage_min=float(args.coverage_min))
    except Exception as e:
        print(f"Computation error: {e}")
        windows = []
        err = str(e)
    else:
        err = None

    result_summary = []
    result_summary.append({
        "name": "windows_evaluated",
        "value": int(len(df)),
        "description": "Number of starting timestamps considered for 8h windows.",
        "timestamp": iso_now()
    })
    result_summary.append({
        "name": "valid_windows",
        "value": int(len(windows)),
        "description": "Windows with coverage >= threshold.",
        "timestamp": iso_now()
    })

    if windows:
        # Max TWA window
        max_w = max(windows, key=lambda w: w["twa"])
        result_summary.append({
            "name": "max_8h_twa",
            "value": {
                "twa": max_w["twa"],
                "start": max_w["start"].isoformat(),
                "end": max_w["end"].isoformat(),
                "coverage_ratio": max_w["coverage_ratio"]
            },
            "description": "Window with highest 8h time-weighted mean O3.",
            "timestamp": max_w["start"].isoformat()
        })

        # Exceedances
        exceed = [w for w in windows if w["twa"] > float(args.guideline)]
        result_summary.append({
            "name": "exceedance_count",
            "value": int(len(exceed)),
            "description": f"Number of 8h windows exceeding guideline {args.guideline} ug/m3.",
            "timestamp": iso_now()
        })
        for i, w in enumerate(exceed, start=1):
            result_summary.append({
                "name": f"exceedance_window_{i}",
                "value": {
                    "twa": w["twa"],
                    "start": w["start"].isoformat(),
                    "end": w["end"].isoformat(),
                    "coverage_ratio": w["coverage_ratio"]
                },
                "description": "8h TWA O3 above guideline.",
                "timestamp": w["start"].isoformat()
            })
    else:
        result_summary.append({
            "name": "note",
            "value": "No valid 8h windows (coverage insufficient or data too sparse)",
            "description": "Try collecting more frequent readings or a longer time span.",
            "timestamp": iso_now()
        })

    if err is not None:
        result_summary.append({
            "name": "error",
            "value": err,
            "description": "Error encountered during computation.",
            "timestamp": iso_now()
        })

    result = {
        "task_name": TASK_NAME,
        "description": "Compute a time-weighted 8-hour mean of O3 using actual timestamp gaps; require >=75% coverage and flag exceedance of WHO 8h guideline (100 ug/m3).",
        "result_summary": result_summary,
        "result_generated_at": iso_now()
    }

    with open(out_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Print concise summary
    print(f"Valid windows: {len(windows)}")
    if windows:
        max_w = max(windows, key=lambda w: w["twa"])
        print(f"Max 8h TWA: {max_w['twa']:.2f} ug/m3, start: {max_w['start'].isoformat()}, end: {max_w['end'].isoformat()} (coverage={max_w['coverage_ratio']:.2%})")


if __name__ == "__main__":
    main()