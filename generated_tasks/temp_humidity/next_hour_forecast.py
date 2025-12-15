import os
import json
import sys
import pandas as pd
from datetime import timedelta

TASK_NAME = "next_hour_forecast"
DESCRIPTION = "Predict next-hour temperature and humidity using simple moving average"
DATA_TYPE = "temp_humidity"


def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_path = os.path.join("output", DATA_TYPE)
    os.makedirs(output_path, exist_ok=True)
    
    try:
        df = pd.read_csv(data_path, parse_dates=["timestamp"])
        df.set_index("timestamp", inplace=True)
        last_12 = df[-12:] if len(df) >= 12 else df
        
        temp_avg = last_12["temperature_c"].mean()
        humidity_avg = last_12["humidity_percent"].mean()
        
        forecast_time = df.index[-1] + timedelta(minutes=60)
        
        result = {
            "task_name": TASK_NAME,
            "description": DESCRIPTION,
            "result_summary": [
                {
                    "name": "predicted_temperature_c",
                    "value": temp_avg,
                    "description": "Average temperature for next hour",
                    "timestamp": forecast_time.isoformat()
                },
                {
                    "name": "predicted_humidity_percent",
                    "value": humidity_avg,
                    "description": "Average humidity for next hour",
                    "timestamp": forecast_time.isoformat()
                }
            ],
            "result_generated_at": pd.Timestamp.now().isoformat()
        }
        
        result_file = os.path.join(output_path, f"{TASK_NAME}_result.json")
        with open(result_file, "w") as f:
            f.write(json.dumps(result))
        
        print(json.dumps(result))
        sys.exit(0)
    except Exception as e:
        error_result = {
            "task_name": TASK_NAME,
            "error": f"{str(e)}"
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()