import os, json
import pandas as pd
from datetime import datetime, timezone

def main():
    data_path = os.path.join("data", "temp_humidity", "raw_data.csv")
    df = pd.read_csv(data_path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    alerts = []
    # Check 10‑minute window (2 samples apart)
    for i in range(2, len(df)):
        temp_diff_10 = abs(df.loc[i, "temperature_c"] - df.loc[i-2, "temperature_c"])
        hum_diff_10 = abs(df.loc[i, "humidity_percent"] - df.loc[i-2, "humidity_percent"])
        if temp_diff_10 > 2 or hum_diff_10 > 5:
            alerts.append({
                "timestamp": df.loc[i, "timestamp"].isoformat(),
                "temperature_change": round(temp_diff_10, 2),
                "humidity_change": round(hum_diff_10, 2),
                "description": "Abrupt change detected (10‑min)"
            })
    # Check 5‑minute step (1 sample apart)
    for i in range(1, len(df)):
        temp_diff_5 = abs(df.loc[i, "temperature_c"] - df.loc[i-1, "temperature_c"])
        hum_diff_5 = abs(df.loc[i, "humidity_percent"] - df.loc[i-1, "humidity_percent"])
        if temp_diff_5 > 2 or hum_diff_5 > 5:
            alerts.append({
                "timestamp": df.loc[i, "timestamp"].isoformat(),
                "temperature_change": round(temp_diff_5, 2),
                "humidity_change": round(hum_diff_5, 2),
                "description": "Abrupt change detected (5‑min)"
            })
    # Deduplicate alerts by timestamp
    seen = set()
    unique_alerts = []
    for a in alerts:
        if a["timestamp"] not in seen:
            seen.add(a["timestamp"])
            unique_alerts.append(a)

    result = {
        "task_name": "sudden_change_detection",
        "description": "Detect abrupt changes where temperature shifts >2 °C or humidity shifts >5 % within a 10‑minute window and raise a local alert.",
        "result_summary": [
            {
                "name": "alerts",
                "value": unique_alerts,
                "description": "List of detected abrupt change events",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    output_dir = os.path.join("output", "temp_humidity")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "sudden_change_detection_result.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()