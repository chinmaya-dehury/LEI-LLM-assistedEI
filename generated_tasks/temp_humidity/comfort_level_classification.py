import os
import json
import sys
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = "comfort_level_classification"
DESCRIPTION = "Classify each reading into comfort bands using simplified heat index."
DATA_TYPE = "temp_humidity"

def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        error = {"task_name": TASK_NAME, "error": f"File not found: {data_path}"}
        print(json.dumps(error))
        sys.exit(1)
    # Parse timestamps
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
    # Ensure numeric columns are proper numbers
    df["temperature_c"] = pd.to_numeric(df.get("temperature_c"), errors="coerce")
    df["humidity_percent"] = pd.to_numeric(df.get("humidity_percent"), errors="coerce")
    # Drop rows with critical missing values
    df = df.dropna(subset=["timestamp", "temperature_c", "humidity_percent"])
    # Compute simplified heat index
    df["heat_index"] = df["temperature_c"] + 0.33 * df["humidity_percent"] - 4.0
    def classify(hi):
        if hi < 26:
            return "comfortable"
        elif hi < 30:
            return "warm"
        else:
            return "hot"
    df["comfort"] = df["heat_index"].apply(classify)
    counts = df["comfort"].value_counts().to_dict()
    total = int(len(df))
    now_iso = datetime.now(timezone.utc).isoformat()
    summary = []
    summary.append({"name": "total_readings", "value": total, "description": "Total number of readings processed", "timestamp": now_iso})
    for band in ["comfortable", "warm", "hot"]:
        summary.append({"name": f"{band}_count", "value": counts.get(band, 0), "description": f"Number of readings classified as {band}", "timestamp": now_iso})
    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": summary,
        "result_generated_at": now_iso
    }
    output_dir = os.path.join("output", DATA_TYPE)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
    try:
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        error = {"task_name": TASK_NAME, "error": str(e)}
        print(json.dumps(error))
        sys.exit(1)
    print(json.dumps(result, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    main()