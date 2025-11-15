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
    task_name = "pollutant_plausibility_and_constraints"
    description = (
        "Validate readings for non-negativity and physical constraints (e.g., PM2.5 <= PM10) and flag out-of-range values using simple ambient bounds: CO<=10000, NO<=200, NO2<=400, O3<=300, SO2<=500, PM2.5<=500, PM10<=600, NH3<=100 µg/m3."
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

    bounds = {
        "co": 10000.0,
        "no": 200.0,
        "no2": 400.0,
        "o3": 300.0,
        "so2": 500.0,
        "pm2_5": 500.0,
        "pm10": 600.0,
        "nh3": 100.0,
    }

    try:
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at {data_path}")
        df = pd.read_csv(data_path)
        add_result("total_rows", int(len(df)), "Number of rows in the dataset.")

        # Track any row with any violation
        any_violation_mask = pd.Series(False, index=df.index)

        # Per-pollutant checks
        for col, max_v in bounds.items():
            if col not in df.columns:
                add_result(f"{col}_missing", True, f"Column '{col}' not found in input data.")
                continue
            ser = pd.to_numeric(df[col], errors="coerce")
            neg_mask = ser < 0
            high_mask = ser > max_v
            oor_mask = (neg_mask | high_mask) & ser.notna()
            any_violation_mask = any_violation_mask | oor_mask.fillna(False)
            add_result(f"{col}_out_of_range_count", int(oor_mask.sum()), f"Values < 0 or > {max_v} µg/m3 for '{col}'.")
            idx_list = df.index[oor_mask].tolist()
            add_result(f"{col}_out_of_range_indices", idx_list, f"Row indices where '{col}' is out of range (<0 or > {max_v}).")
            add_result(f"{col}_missing_count", int(ser.isna().sum()), f"Rows where '{col}' is missing or not parseable.")

        # Physical constraint: PM2.5 <= PM10
        if ("pm2_5" in df.columns) and ("pm10" in df.columns):
            pm25 = pd.to_numeric(df["pm2_5"], errors="coerce")
            pm10 = pd.to_numeric(df["pm10"], errors="coerce")
            valid_pair = pm25.notna() & pm10.notna()
            viol_mask = valid_pair & (pm25 > pm10)
            any_violation_mask = any_violation_mask | viol_mask.fillna(False)
            viol_indices = df.index[viol_mask].tolist()
            add_result("pm25_le_pm10_violations_count", int(viol_mask.sum()), "Count of rows where PM2.5 exceeds PM10 (should not happen).")
            add_result("pm25_le_pm10_violations_indices", viol_indices, "Row indices where PM2.5 > PM10.")
        else:
            add_result("pm25_pm10_constraint_skipped", True, "PM2.5 and/or PM10 column missing; physical constraint check skipped.")

        # Summary of any violation across all rules
        add_result("rows_with_any_violation_count", int(any_violation_mask.sum()), "Number of rows with at least one constraint violation.")
        add_result("rows_with_any_violation_indices", df.index[any_violation_mask].tolist(), "Indices of rows with at least one violation.")

        output_obj = {
            "task_name": task_name,
            "description": description,
            "result_summary": result_summary,
            "result_generated_at": iso_now(),
        }
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(output_obj, f, ensure_ascii=False, indent=2)
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
