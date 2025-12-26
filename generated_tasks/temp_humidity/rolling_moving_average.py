import os
import json
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

TASK_NAME = "rolling_moving_average"
DESCRIPTION = "Compute a 3-sample (15‑minute) moving average for temperature and humidity and append the values to the data stream for smoothing."
DATA_TYPE = "temp_humidity"

def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    if not Path(data_path).exists():
        error = {"task_name": TASK_NAME, "error": f"Data file not found: {data_path}"}
        print(json.dumps(error))
        sys.exit(1)
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        error = {"task_name": TASK_NAME, "error": str(e)}
        print(json.dumps(error))
        sys.exit(1)

    # Parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
    df = df.dropna(subset=["timestamp"])

    # Ensure numeric columns
    for col in ["temperature_c", "humidity_percent"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=["temperature_c", "humidity_percent"])

    # Compute 3-sample moving averages (15 minutes)
    df["temperature_c_ma"] = df["temperature_c"].rolling(window=3, min_periods=1).mean()
    df["humidity_percent_ma"] = df["humidity_percent"].rolling(window=3, min_periods=1).mean()

    now_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [
            {
                "name": "rows_processed",
                "value": int(df.shape[0]),
                "description": "Number of rows after adding moving averages",
                "timestamp": now_iso
            },
            {
                "name": "latest_temperature_c_ma",
                "value": round(float(df["temperature_c_ma"].iloc[-1]), 2),
                "description": "Most recent temperature moving average",
                "timestamp": now_iso
            },
            {
                "name": "latest_humidity_percent_ma",
                "value": round(float(df["humidity_percent_ma"].iloc[-1]), 2),
                "description": "Most recent humidity moving average",
                "timestamp": now_iso
            }
        ],
        "result_generated_at": now_iso
    }

    # Output result JSON to stdout
    print(json.dumps(result))

    # Write result JSON and enriched CSV to output directory
    output_dir = Path("output") / DATA_TYPE
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / f"{TASK_NAME}_result.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    enriched_path = output_dir / f"{TASK_NAME}_enriched.csv"
    df.to_csv(enriched_path, index=False)

    sys.exit(0)

if __name__ == "__main__":
    main()