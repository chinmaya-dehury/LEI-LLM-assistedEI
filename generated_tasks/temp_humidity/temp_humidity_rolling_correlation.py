import os
import json
import pandas as pd
import numpy as np
from datetime import datetime


def iso_ts(x):
    try:
        return pd.to_datetime(x).isoformat()
    except Exception:
        try:
            return datetime.now().astimezone().isoformat()
        except Exception:
            return str(x)


def main():
    data_type = "temp_humidity"
    data_path = os.path.join("data", data_type, "raw_data.csv")
    output_dir = os.path.join("output", data_type)
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(data_path):
        result = {
            "task_name": "temp_humidity_rolling_correlation",
            "description": "Calculate rolling Pearson correlation (window=6) and overall correlation between temperature_c and humidity_percent; flag windows where |corr| > 0.6 as strong coupling periods.",
            "result_summary": [
                {
                    "name": "error",
                    "value": f"Data file not found: {data_path}",
                    "description": "Input CSV missing",
                    "timestamp": iso_ts(datetime.now())
                }
            ],
            "result_generated_at": iso_ts(datetime.now())
        }
        out_path = os.path.join(output_dir, "temp_humidity_rolling_correlation_result.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        return

    df = pd.read_csv(data_path)
    if "timestamp" not in df.columns or "temperature_c" not in df.columns or "humidity_percent" not in df.columns:
        result = {
            "task_name": "temp_humidity_rolling_correlation",
            "description": "Calculate rolling Pearson correlation (window=6) and overall correlation between temperature_c and humidity_percent; flag windows where |corr| > 0.6 as strong coupling periods.",
            "result_summary": [
                {
                    "name": "error",
                    "value": "Required columns missing. Expect: timestamp, temperature_c, humidity_percent",
                    "description": "Schema validation failure",
                    "timestamp": iso_ts(datetime.now())
                }
            ],
            "result_generated_at": iso_ts(datetime.now())
        }
        out_path = os.path.join(output_dir, "temp_humidity_rolling_correlation_result.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    df["humidity_percent"] = pd.to_numeric(df["humidity_percent"], errors="coerce")

    # Rolling Pearson correlation with window=6 (e.g., 30 minutes at 5-min interval)
    rolling_corr = df["temperature_c"].rolling(window=6, min_periods=6).corr(df["humidity_percent"])
    df["rolling_corr"] = rolling_corr

    # Overall correlation
    if df[["temperature_c", "humidity_percent"]].dropna().shape[0] > 1:
        overall_corr = float(df["temperature_c"].corr(df["humidity_percent"]))
    else:
        overall_corr = float("nan")

    # Strong coupling windows where |corr| > 0.6
    strong_mask = df["rolling_corr"].abs() > 0.6
    strong_windows = df.loc[strong_mask & df["rolling_corr"].notna(), ["timestamp", "rolling_corr"]]
    strong_timestamps = [iso_ts(ts) for ts in strong_windows["timestamp"].tolist()]

    # Max absolute rolling correlation
    rc_nonnull = df["rolling_corr"].dropna()
    if not rc_nonnull.empty:
        idx_max = rc_nonnull.abs().idxmax()
        max_abs_rc = float(abs(df.loc[idx_max, "rolling_corr"]))
        ts_max = df.loc[idx_max, "timestamp"]
    else:
        max_abs_rc = float("nan")
        ts_max = df["timestamp"].iloc[-1] if not df.empty else datetime.now()

    end_ts = df["timestamp"].iloc[-1] if not df.empty else datetime.now()

    results = []
    results.append({
        "name": "overall_correlation",
        "value": None if np.isnan(overall_corr) else round(overall_corr, 3),
        "description": "Pearson correlation between temperature_c and humidity_percent over entire dataset",
        "timestamp": iso_ts(end_ts)
    })
    results.append({
        "name": "max_abs_rolling_correlation",
        "value": None if np.isnan(max_abs_rc) else round(max_abs_rc, 3),
        "description": "Maximum absolute rolling correlation (window=6)",
        "timestamp": iso_ts(ts_max)
    })
    results.append({
        "name": "num_strong_coupling_windows",
        "value": int(len(strong_timestamps)),
        "description": "Number of rolling windows with |corr| > 0.6",
        "timestamp": iso_ts(end_ts)
    })
    results.append({
        "name": "strong_coupling_window_timestamps",
        "value": strong_timestamps,
        "description": "Timestamps where rolling window end had strong coupling (|corr| > 0.6)",
        "timestamp": iso_ts(end_ts)
    })

    out_obj = {
        "task_name": "temp_humidity_rolling_correlation",
        "description": "Calculate rolling Pearson correlation (window=6) and overall correlation between temperature_c and humidity_percent; flag windows where |corr| > 0.6 as strong coupling periods.",
        "result_summary": results,
        "result_generated_at": iso_ts(datetime.now())
    }

    out_path = os.path.join(output_dir, "temp_humidity_rolling_correlation_result.json")
    with open(out_path, "w") as f:
        json.dump(out_obj, f, indent=2)

    print(json.dumps(out_obj, indent=2))


if __name__ == "__main__":
    main()