import os
import json
import argparse
from datetime import datetime, timezone
import pandas as pd
import numpy as np

TASK_NAME = "coarse_dust_event_detector"


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def detect_coarse_dust_events(df, pm10_threshold=80.0, ratio_threshold=0.3, min_consec=2):
    # Ensure required columns exist
    required_cols = ["timestamp_utc", "pm10", "pm2_5"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")

    # Sort by timestamp and drop rows with missing required values
    df = df.copy()
    df = df.dropna(subset=["timestamp_utc"]).sort_values("timestamp_utc").reset_index(drop=True)

    # Compute ratio safely
    df["pm10"] = pd.to_numeric(df["pm10"], errors="coerce")
    df["pm2_5"] = pd.to_numeric(df["pm2_5"], errors="coerce")
    df["ratio"] = np.where(df["pm10"] > 0, df["pm2_5"] / df["pm10"], np.nan)

    cond = (df["pm10"] > pm10_threshold) & (df["ratio"] < ratio_threshold)

    # Identify consecutive True runs
    grp_id = (cond != cond.shift(fill_value=False)).cumsum()
    df["_grp"] = grp_id

    events = []
    for gid, g in df.groupby("_grp"):
        if not cond.loc[g.index].any():
            continue
        if len(g) >= min_consec:
            event_rows = g.loc[cond.loc[g.index]]
            start_ts = event_rows["timestamp_utc"].iloc[0]
            end_ts = event_rows["timestamp_utc"].iloc[-1]
            peak_idx = event_rows["pm10"].idxmax()
            peak_pm10 = float(df.loc[peak_idx, "pm10"]) if pd.notna(peak_idx) else float("nan")
            peak_ts = df.loc[peak_idx, "timestamp_utc"].isoformat() if pd.notna(peak_idx) else None
            events.append({
                "start": start_ts.isoformat(),
                "end": end_ts.isoformat(),
                "peak_pm10": peak_pm10,
                "peak_time": peak_ts,
                "count": int(len(event_rows))
            })

    return events


def main():
    parser = argparse.ArgumentParser(description="Detect coarse dust events from PM10 and PM2.5 ratios.")
    parser.add_argument("--data-type", default="air_quality", help="Data type directory under data/ and output/.")
    parser.add_argument("--pm10-threshold", type=float, default=80.0, help="PM10 threshold (ug/m3)")
    parser.add_argument("--ratio-threshold", type=float, default=0.3, help="PM2.5/PM10 ratio threshold")
    parser.add_argument("--min-consec", type=int, default=int(os.environ.get("MIN_CONSEC", 2)), help="Minimum consecutive readings")
    args = parser.parse_args()

    data_path = os.path.join("data", args.data_type, "raw_data.csv")
    output_dir = os.path.join("output", args.data_type)
    ensure_dir(output_dir)
    out_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")

    if not os.path.isfile(data_path):
        print(f"Data file not found: {data_path}")
        result = {
            "task_name": TASK_NAME,
            "description": "Detect coarse dust episodes when PM10 is high and PM2.5/PM10 is low.",
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
            "description": "Detect coarse dust episodes when PM10 is high and PM2.5/PM10 is low.",
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

    events = []
    try:
        events = detect_coarse_dust_events(df, pm10_threshold=args.pm10_threshold, ratio_threshold=args.ratio_threshold, min_consec=args.min_consec)
    except Exception as e:
        print(f"Detection error: {e}")
        events = []
        err = str(e)
    else:
        err = None

    result_summary = []
    result_summary.append({
        "name": "number_of_events",
        "value": int(len(events)),
        "description": "Total detected coarse dust episodes.",
        "timestamp": iso_now()
    })

    for i, ev in enumerate(events, start=1):
        result_summary.append({
            "name": f"coarse_dust_event_{i}",
            "value": ev,
            "description": "Episode with start/end, peak PM10, and count of consecutive readings.",
            "timestamp": ev.get("start", iso_now())
        })

    if err is not None:
        result_summary.append({
            "name": "error",
            "value": err,
            "description": "Error encountered during detection.",
            "timestamp": iso_now()
        })

    result = {
        "task_name": TASK_NAME,
        "description": "Detect coarse dust episodes when PM10 is high (>80 ug/m3) and PM2.5/PM10 < 0.3 for at least N consecutive readings.",
        "result_summary": result_summary,
        "result_generated_at": iso_now()
    }

    with open(out_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Print concise summary
    print(f"Detected {len(events)} coarse dust event(s).")
    for i, ev in enumerate(events, start=1):
        print(f"Event {i}: {ev}")


if __name__ == "__main__":
    main()