import os
import json
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timezone

TASK_NAME = "hourly_averages"
DESCRIPTION = "Calculate the average temperature and humidity for each hour and store the results in the local SQLite database."
DATA_TYPE = "temp_humidity"

def main():
    # Build data file path
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    if not os.path.isfile(data_path):
        print(json.dumps({"task_name": TASK_NAME, "error": f"Data file not found: {data_path}"}))
        sys.exit(1)

    # Load CSV
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        print(json.dumps({"task_name": TASK_NAME, "error": str(e)}))
        sys.exit(1)

    # Parse timestamps safely
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Ensure numeric columns are proper floats
    for col in ["temperature_c", "humidity_percent"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df = df.dropna(subset=["temperature_c", "humidity_percent"])

    # Compute hourly averages
    df["hour"] = df["timestamp"].dt.floor("h")  # use lowercase 'h' per pandas recommendation
    hourly = df.groupby("hour", as_index=False).agg(
        avg_temperature=("temperature_c", "mean"),
        avg_humidity=("humidity_percent", "mean")
    )

    # Store results in SQLite
    db_path = os.path.join("data", DATA_TYPE, "insights.db")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS hourly_averages (
                hour TEXT PRIMARY KEY,
                avg_temperature REAL,
                avg_humidity REAL
            )"""
        )
        for _, row in hourly.iterrows():
            cur.execute(
                "INSERT OR REPLACE INTO hourly_averages (hour, avg_temperature, avg_humidity) VALUES (?,?,?)",
                (row["hour"].isoformat(), float(row["avg_temperature"]), float(row["avg_humidity"]))
            )
        conn.commit()
    except Exception as e:
        print(json.dumps({"task_name": TASK_NAME, "error": str(e)}))
        sys.exit(1)
    finally:
        conn.close()

    # Prepare result JSON
    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [
            {
                "name": "hours_computed",
                "value": int(hourly.shape[0]),
                "description": "Number of hourly average records stored.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    # Write result to output file
    output_dir = os.path.join("output", DATA_TYPE)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
    try:
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        print(json.dumps({"task_name": TASK_NAME, "error": f"Failed to write result file: {e}"}))
        sys.exit(1)

    # Emit JSON to stdout as required by validation
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()