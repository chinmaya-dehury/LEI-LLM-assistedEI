"""
Task: Analyze Weather Forecast
Description: Analyze weather data to predict rainfall probability and intensity.
"""

import os
from pathlib import Path
import csv
import json
import sys

def main():
    # Resolve paths dynamically
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = root_dir / "data" / "meteo-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "meteo-data" / "raw_data.txt"

    if not data_file.exists():
        print(json.dumps({
            "status": "error",
            "error": f"Data file not found at {data_file}"
        }))
        sys.exit(1)

    rain_meter_values = []
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    val = float(row.get('Rain_Meter') or 0.0)
                    rain_meter_values.append(val)
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": f"Failed to read data file: {e}"
        }))
        sys.exit(1)

    if not rain_meter_values:
        avg_rain = 0.0
    else:
        avg_rain = sum(rain_meter_values) / len(rain_meter_values)

    rain_predicted = avg_rain > 2.0

    output = {
        "status": "success",
        "result_summary": [
            {
                "key": "average_rainfall",
                "value": avg_rain
            },
            {
                "key": "rain_predicted",
                "value": rain_predicted
            }
        ]
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()