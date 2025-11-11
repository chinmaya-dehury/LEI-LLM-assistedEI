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
            "task_name": "condensation_risk_indicator",
            "description": "Compute dewpoint depression (temperature_c − dew_point_c) and classify condensation risk (high <2°C, moderate 2–4°C, low >4°C); optionally flag if dew_point_c ≥ (temperature_c − 2.0) to indicate potential surface condensation.",
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
        out_path = os.path.join(output_dir, "condensation_risk_indicator_result.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        return

    df = pd.read_csv(data_path)
    if "timestamp" not in df.columns or "temperature_c" not in df.columns or "humidity_percent" not in df.columns:
        result = {
            "task_name": "condensation_risk_indicator",
            "description": "Compute dewpoint depression (temperature_c − dew_point_c) and classify condensation risk (high <2°C, moderate 2–4°C, low >4°C); optionally flag if dew_point_c ≥ (temperature_c − 2.0) to indicate potential surface condensation.",
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
        out_path = os.path.join(output_dir, "condensation_risk_indicator_result.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    T = pd.to_numeric(df["temperature_c"], errors="coerce")
    RH = pd.to_numeric(df["humidity_percent"], errors="coerce").clip(lower=0, upper=100)

    a, b = 17.62, 243.12  # Magnus constants for water over liquid (Celsius)
    gamma = np.log(RH / 100.0) + (a * T) / (b + T)
    dew_point_c = (b * gamma) / (a - gamma)

    df["dew_point_c"] = dew_point_c
    df["dewpoint_depression_c"] = T - df["dew_point_c"]

    def classify(dd):
        try:
            if dd < 2.0:
                return "high"
            elif dd <= 4.0:
                return "moderate"
            else:
                return "low"
        except Exception:
            return "unknown"

    df["condensation_risk"] = df["dewpoint_depression_c"].apply(classify)
    df["potential_surface_condensation"] = df["dew_point_c"] >= (T - 2.0)

    if df.empty:
        result = {
            "task_name": "condensation_risk_indicator",
            "description": "Compute dewpoint depression (temperature_c − dew_point_c) and classify condensation risk (high <2°C, moderate 2–4°C, low >4°C); optionally flag if dew_point_c ≥ (temperature_c − 2.0) to indicate potential surface condensation.",
            "result_summary": [
                {
                    "name": "error",
                    "value": "No valid rows after parsing",
                    "description": "Data is empty",
                    "timestamp": iso_ts(datetime.now())
                }
            ],
            "result_generated_at": iso_ts(datetime.now())
        }
        out_path = os.path.join(output_dir, "condensation_risk_indicator_result.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result, indent=2))
        return

    last_row = df.iloc[-1]
    end_ts = last_row["timestamp"]

    results = []
    results.append({
        "name": "latest_dew_point_c",
        "value": round(float(last_row["dew_point_c"]), 2),
        "description": "Dew point temperature at last sample (°C)",
        "timestamp": iso_ts(end_ts)
    })
    results.append({
        "name": "latest_dewpoint_depression_c",
        "value": round(float(last_row["dewpoint_depression_c"]), 2),
        "description": "Dew point depression at last sample (°C)",
        "timestamp": iso_ts(end_ts)
    })
    results.append({
        "name": "latest_condensation_risk",
        "value": str(last_row["condensation_risk"]),
        "description": "Condensation risk class at last sample",
        "timestamp": iso_ts(end_ts)
    })

    counts = df["condensation_risk"].value_counts(dropna=False).to_dict()
    for k in ["high", "moderate", "low", "unknown"]:
        v = int(counts.get(k, 0))
        results.append({
            "name": f"count_{k}_risk",
            "value": v,
            "description": f"Number of readings classified as {k} condensation risk",
            "timestamp": iso_ts(end_ts)
        })

    if df["dewpoint_depression_c"].notna().any():
        idx_min = df["dewpoint_depression_c"].idxmin()
        min_dd = float(df.loc[idx_min, "dewpoint_depression_c"])
        min_ts = df.loc[idx_min, "timestamp"]
        results.append({
            "name": "min_dewpoint_depression_c",
            "value": round(min_dd, 2),
            "description": "Minimum dew point depression observed (°C)",
            "timestamp": iso_ts(min_ts)
        })

    surf_count = int(df["potential_surface_condensation"].sum())
    results.append({
        "name": "potential_surface_condensation_count",
        "value": surf_count,
        "description": "Number of readings where dew_point_c >= (temperature_c - 2.0)",
        "timestamp": iso_ts(end_ts)
    })

    out_obj = {
        "task_name": "condensation_risk_indicator",
        "description": "Compute dewpoint depression (temperature_c − dew_point_c) and classify condensation risk (high <2°C, moderate 2–4°C, low >4°C); optionally flag if dew_point_c ≥ (temperature_c − 2.0) to indicate potential surface condensation.",
        "result_summary": results,
        "result_generated_at": iso_ts(datetime.now())
    }

    out_path = os.path.join(output_dir, "condensation_risk_indicator_result.json")
    with open(out_path, "w") as f:
        json.dump(out_obj, f, indent=2)

    print(json.dumps(out_obj, indent=2))


if __name__ == "__main__":
    main()