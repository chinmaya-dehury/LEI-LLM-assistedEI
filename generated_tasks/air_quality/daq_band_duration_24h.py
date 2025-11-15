import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np


def main():
    DATA_TYPE = "air_quality"
    TASK_NAME = "daq_band_duration_24h"
    DESCRIPTION = "Aggregate minutes spent in each UK DAQI band (Low/Moderate/High/Very High) over the last 24 hours from aqi_uk; output durations and percentages with coverage check."

    data_path = Path("data") / DATA_TYPE / "raw_data.csv"
    output_dir = Path("output") / DATA_TYPE
    output_dir.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    def write_and_exit(summary_items, code=0):
        result = {"task_name": TASK_NAME, "description": DESCRIPTION, "result_summary": summary_items, "result_generated_at": now_iso}
        out_file = output_dir / f"{TASK_NAME}_result.json"
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        sys.exit(code)

    if not data_path.exists():
        write_and_exit([
            {
                "name": "error",
                "value": f"Data file not found: {data_path}",
                "description": "Cannot compute DAQI band durations without data.",
                "timestamp": now_iso
            }
        ], code=1)

    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        write_and_exit([
            {
                "name": "error",
                "value": f"Failed to read CSV: {e}",
                "description": "CSV parsing error.",
                "timestamp": now_iso
            }
        ], code=1)

    if "timestamp_utc" not in df.columns or "aqi_uk" not in df.columns:
        write_and_exit([
            {
                "name": "error",
                "value": "Missing required columns: timestamp_utc and aqi_uk",
                "description": "Ensure CSV contains timestamp_utc and aqi_uk columns.",
                "timestamp": now_iso
            }
        ], code=1)

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp_utc"])
    if df.empty:
        write_and_exit([
            {
                "name": "error",
                "value": "No valid timestamps after parsing.",
                "description": "All timestamp_utc values are invalid.",
                "timestamp": now_iso
            }
        ], code=1)

    df = df.sort_values("timestamp_utc").reset_index(drop=True)
    end = df["timestamp_utc"].max()
    window_start = end - pd.Timedelta(hours=24)

    before = df[df["timestamp_utc"] < window_start]
    after = df[df["timestamp_utc"] >= window_start]
    if not before.empty:
        prev = before.iloc[[-1]]
        dfw = pd.concat([prev, after], ignore_index=True)
    else:
        dfw = after.copy()

    deltas = df["timestamp_utc"].diff().dropna()
    if deltas.empty:
        med_minutes = 10.0
    else:
        med_minutes = float(np.median(deltas.dt.total_seconds() / 60.0))
        med_minutes = float(np.clip(med_minutes, 5.0, 20.0))
    med_delta = pd.Timedelta(minutes=med_minutes)

    if dfw.empty:
        total_window_minutes = 24.0 * 60.0
        summary = [
            {
                "name": "window_end_utc",
                "value": end.isoformat(),
                "description": "End of the 24h window (latest data timestamp, UTC).",
                "timestamp": now_iso
            },
            {
                "name": "window_start_utc",
                "value": window_start.isoformat(),
                "description": "Start of the 24h window (UTC).",
                "timestamp": now_iso
            },
            {
                "name": "coverage_minutes_24h",
                "value": 0.0,
                "description": "Total minutes covered by data within the 24h window.",
                "timestamp": now_iso
            },
            {
                "name": "coverage_percent_of_24h",
                "value": 0.0,
                "description": "Coverage as a percentage of the 24h window.",
                "timestamp": now_iso
            }
        ]
        for b in ["Low", "Moderate", "High", "Very High", "Unknown"]:
            summary.append({"name": f"{b}_minutes", "value": 0.0, "description": f"Minutes in DAQI band {b} within the 24h window.", "timestamp": now_iso})
            summary.append({"name": f"{b}_percent_of_24h", "value": 0.0, "description": f"Percentage of the full 24h window spent in DAQI band {b}.", "timestamp": now_iso})
            summary.append({"name": f"{b}_percent_of_covered", "value": 0.0, "description": f"Percentage of covered minutes spent in DAQI band {b}.", "timestamp": now_iso})
        write_and_exit(summary, code=0)

    dfw["next_ts"] = dfw["timestamp_utc"].shift(-1)

    def compute_end(row):
        if pd.isna(row["next_ts"]):
            tentative_end = row["timestamp_utc"] + med_delta
        else:
            tentative_end = row["next_ts"]
        return min(tentative_end, end)

    dfw["period_start"] = dfw["timestamp_utc"].apply(lambda t: t if t > window_start else window_start)
    dfw["period_end"] = dfw.apply(compute_end, axis=1)
    dfw["period_start"] = dfw["period_start"].apply(lambda t: t if t < end else end)
    dfw["duration_min"] = (dfw["period_end"] - dfw["period_start"]).dt.total_seconds() / 60.0
    dfw = dfw[dfw["duration_min"] > 0].copy()

    def band_from_aqi(val):
        try:
            a = int(val)
        except Exception:
            return "Unknown"
        if 1 <= a <= 3:
            return "Low"
        elif 4 <= a <= 6:
            return "Moderate"
        elif 7 <= a <= 9:
            return "High"
        elif a >= 10:
            return "Very High"
        else:
            return "Unknown"

    dfw["band"] = dfw["aqi_uk"].apply(band_from_aqi)

    total_window_minutes = 24.0 * 60.0
    coverage_minutes = float(dfw["duration_min"].sum()) if not dfw.empty else 0.0
    coverage_pct = (coverage_minutes / total_window_minutes * 100.0) if total_window_minutes > 0 else 0.0

    band_minutes = dfw.groupby("band")["duration_min"].sum().to_dict() if not dfw.empty else {}
    bands = ["Low", "Moderate", "High", "Very High", "Unknown"]

    result_summary = []
    result_summary.append({
        "name": "window_end_utc",
        "value": end.isoformat(),
        "description": "End of the 24h window (latest data timestamp, UTC).",
        "timestamp": now_iso
    })
    result_summary.append({
        "name": "window_start_utc",
        "value": window_start.isoformat(),
        "description": "Start of the 24h window (UTC).",
        "timestamp": now_iso
    })
    result_summary.append({
        "name": "coverage_minutes_24h",
        "value": round(coverage_minutes, 2),
        "description": "Total minutes covered by data within the 24h window.",
        "timestamp": now_iso
    })
    result_summary.append({
        "name": "coverage_percent_of_24h",
        "value": round(coverage_pct, 2),
        "description": "Coverage as a percentage of the 24h window.",
        "timestamp": now_iso
    })

    for b in bands:
        minutes = float(band_minutes.get(b, 0.0))
        pct_24h = (minutes / total_window_minutes * 100.0) if total_window_minutes > 0 else 0.0
        pct_cov = (minutes / coverage_minutes * 100.0) if coverage_minutes > 0 else 0.0
        result_summary.append({
            "name": f"{b}_minutes",
            "value": round(minutes, 2),
            "description": f"Minutes in DAQI band {b} within the 24h window.",
            "timestamp": now_iso
        })
        result_summary.append({
            "name": f"{b}_percent_of_24h",
            "value": round(pct_24h, 2),
            "description": f"Percentage of the full 24h window spent in DAQI band {b}.",
            "timestamp": now_iso
        })
        result_summary.append({
            "name": f"{b}_percent_of_covered",
            "value": round(pct_cov, 2),
            "description": f"Percentage of covered minutes spent in DAQI band {b}.",
            "timestamp": now_iso
        })

    result = {"task_name": TASK_NAME, "description": DESCRIPTION, "result_summary": result_summary, "result_generated_at": now_iso}
    out_file = output_dir / f"{TASK_NAME}_result.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()