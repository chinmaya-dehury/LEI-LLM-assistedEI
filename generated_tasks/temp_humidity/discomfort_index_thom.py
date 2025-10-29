#!/usr/bin/env python3

import os
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np


def compute_thom_di(temp_c_series: pd.Series, rh_percent_series: pd.Series) -> pd.Series:
    """
    Thom's Discomfort Index (Celsius):
    DI = T - 0.55 * (1 - RH) * (T - 14.5)
    where T in Celsius, RH as fraction (here RH%/100)
    """
    t = temp_c_series.astype(float)
    rh_frac = (rh_percent_series.astype(float) / 100.0)
    di = t - 0.55 * (1.0 - rh_frac) * (t - 14.5)
    return di


def label_di(di_series: pd.Series) -> pd.Series:
    labels = [
        "Comfortable",
        "Mild discomfort",
        "Moderate discomfort",
        "Severe discomfort",
        "Very severe discomfort",
        "Medical emergency risk",
    ]
    di = di_series
    conditions = [
        di < 21.0,
        (di >= 21.0) & (di < 24.0),
        (di >= 24.0) & (di < 27.0),
        (di >= 27.0) & (di < 29.0),
        (di >= 29.0) & (di < 32.0),
        di >= 32.0,
    ]
    return pd.Series(np.select(conditions, labels, default="Unknown"), index=di_series.index)


def main():
    DATA_TYPE = "temp_humidity"
    INPUT_CSV = os.path.join("data", DATA_TYPE, "raw_data.csv")
    OUTPUT_DIR = os.path.join("output", DATA_TYPE)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    RESULT_FILE = os.path.join(OUTPUT_DIR, "discomfort_index_thom_result.json")

    now_iso = datetime.now(timezone.utc).isoformat()

    result = {
        "task_name": "discomfort_index_thom",
        "description": "Calculate Thom’s Discomfort Index (DI) using temperature and humidity and label comfort risk levels.",
        "result_summary": [],
        "result_generated_at": now_iso,
    }

    if not os.path.exists(INPUT_CSV):
        msg = f"Input file not found at {INPUT_CSV}"
        print(msg)
        result["result_summary"].append({
            "name": "error",
            "value": msg,
            "description": "Missing input CSV.",
            "tiemstamp": now_iso,
        })
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    # Load data
    try:
        df = pd.read_csv(INPUT_CSV)
    except Exception as e:
        msg = f"Failed to read CSV: {e}"
        print(msg)
        result["result_summary"].append({
            "name": "error",
            "value": msg,
            "description": "Error while reading the input CSV.",
            "tiemstamp": now_iso,
        })
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    # Basic validation and parsing
    required_cols = {"timestamp", "temperature_c", "humidity_percent"}
    if not required_cols.issubset(df.columns):
        missing = sorted(list(required_cols - set(df.columns)))
        msg = f"Missing required columns: {missing}"
        print(msg)
        result["result_summary"].append({
            "name": "error",
            "value": msg,
            "description": "Input CSV lacks required columns.",
            "tiemstamp": now_iso,
        })
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "temperature_c", "humidity_percent"]).copy()
    if df.empty:
        msg = "No valid rows after parsing input dataset."
        print(msg)
        result["result_summary"].append({
            "name": "error",
            "value": msg,
            "description": "All rows invalid or missing required fields.",
            "tiemstamp": now_iso,
        })
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    # Compute Thom's DI and labels
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["di_thom"] = compute_thom_di(df["temperature_c"], df["humidity_percent"])  # float series
    df["di_label"] = label_di(df["di_thom"])  # categorical label

    # Summaries
    latest_row = df.iloc[-1]
    latest_summary = {
        "name": "latest_di",
        "value": {"di": round(float(latest_row["di_thom"]), 2), "label": str(latest_row["di_label"])},
        "description": "Most recent Thom DI and risk label.",
        "tiemstamp": latest_row["timestamp"].isoformat(),
    }
    result["result_summary"].append(latest_summary)

    # Max DI
    idx_max = df["di_thom"].idxmax()
    row_max = df.loc[idx_max]
    result["result_summary"].append({
        "name": "max_di",
        "value": {"di": round(float(row_max["di_thom"]), 2), "label": str(row_max["di_label"])},
        "description": "Maximum Thom DI observed and its risk label.",
        "tiemstamp": row_max["timestamp"].isoformat(),
    })

    # Min DI
    idx_min = df["di_thom"].idxmin()
    row_min = df.loc[idx_min]
    result["result_summary"].append({
        "name": "min_di",
        "value": {"di": round(float(row_min["di_thom"]), 2), "label": str(row_min["di_label"])},
        "description": "Minimum Thom DI observed and its risk label.",
        "tiemstamp": row_min["timestamp"].isoformat(),
    })

    # Mean DI
    mean_di = float(df["di_thom"].mean())
    result["result_summary"].append({
        "name": "mean_di",
        "value": round(mean_di, 2),
        "description": "Average Thom DI across the dataset.",
        "tiemstamp": now_iso,
    })

    # Band distribution (percent)
    labels_order = [
        "Comfortable",
        "Mild discomfort",
        "Moderate discomfort",
        "Severe discomfort",
        "Very severe discomfort",
        "Medical emergency risk",
    ]
    counts = df["di_label"].value_counts()
    total = len(df)
    band_distribution = {lab: round(float(counts.get(lab, 0) / total * 100.0), 2) for lab in labels_order}
    result["result_summary"].append({
        "name": "band_distribution_percent",
        "value": band_distribution,
        "description": "Percentage of readings in each Thom DI risk band.",
        "tiemstamp": now_iso,
    })

    # High-risk count (DI >= 27 => Severe and above)
    high_risk_count = int((df["di_thom"] >= 27.0).sum())
    result["result_summary"].append({
        "name": "high_risk_count",
        "value": high_risk_count,
        "description": "Number of readings with DI >= 27 (Severe discomfort or worse).",
        "tiemstamp": now_iso,
    })

    # Simple recommendation based on latest label
    latest_label = str(latest_row["di_label"]) if pd.notna(latest_row["di_label"]) else "Unknown"
    recommendation_map = {
        "Comfortable": "No action needed.",
        "Mild discomfort": "Consider increasing air circulation.",
        "Moderate discomfort": "Increase cooling or ventilation; ensure hydration.",
        "Severe discomfort": "Adjust HVAC urgently; reduce occupancy or add fans.",
        "Very severe discomfort": "Immediate cooling needed; potential health risk.",
        "Medical emergency risk": "Critical: Initiate emergency cooling and evacuate if needed.",
    }
    recommendation = recommendation_map.get(latest_label, "Monitor conditions.")
    result["result_summary"].append({
        "name": "latest_recommendation",
        "value": recommendation,
        "description": f"Action suggestion based on latest risk band: {latest_label}.",
        "tiemstamp": latest_row["timestamp"].isoformat(),
    })

    # Persist results
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Console output (concise)
    print(f"Processed {len(df)} rows from {INPUT_CSV}")
    print(f"Latest DI: {latest_summary['value']['di']} ({latest_summary['value']['label']}) at {latest_summary['tiemstamp']}")
    print(f"Max DI: {result['result_summary'][1]['value']['di']} ({result['result_summary'][1]['value']['label']}) at {result['result_summary'][1]['tiemstamp']}")
    print(f"Min DI: {result['result_summary'][2]['value']['di']} ({result['result_summary'][2]['value']['label']}) at {result['result_summary'][2]['tiemstamp']}")
    print("Band distribution (%):")
    for k, v in band_distribution.items():
        print(f"  - {k}: {v}%")
    print(f"High-risk (DI >= 27) count: {high_risk_count}")
    print(f"Recommendation: {recommendation}")
    print(f"Result saved to: {RESULT_FILE}")


if __name__ == "__main__":
    main()
