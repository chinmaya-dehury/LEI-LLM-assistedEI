import os
import json
import sys
import pandas as pd
import math
from datetime import datetime

TASK_NAME = "dew_point_calculation"
DESCRIPTION = "Calculate dew point from temperature and humidity"
DATA_TYPE = "temp_humidity"

def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_path = os.path.join("output", DATA_TYPE)
    os.makedirs(output_path, exist_ok=True)
    
    try:
        df = pd.read_csv(data_path)
        
        # Calculate dew point using Magnus formula
        df['dew_point_c'] = df.apply(lambda row: (243.0416 * (math.log(row['humidity_percent']/100) + (17.625 * row['temperature_c']) / (243.0416 + row['temperature_c']))) / (17.625 - (math.log(row['humidity_percent']/100) + (17.625 * row['temperature_c']) / (243.0416 + row['temperature_c']))), axis=1)
        
        result = {
            "task_name": TASK_NAME,
            "description": DESCRIPTION,
            "result_summary": [
                {
                    "name": "dew_point_c_avg",
                    "value": df['dew_point_c'].mean(),
                    "description": "Average dew point temperature",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "name": "dew_point_c_min",
                    "value": df['dew_point_c'].min(),
                    "description": "Minimum dew point temperature",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "name": "dew_point_c_max",
                    "value": df['dew_point_c'].max(),
                    "description": "Maximum dew point temperature",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "result_generated_at": datetime.now().isoformat()
        }
        
        # Output to stdout and file
        print(json.dumps(result))
        result_file = os.path.join(output_path, f"{TASK_NAME}_result.json")
        with open(result_file, 'w') as f:
            json.dump(result, f)
        sys.exit(0)
    except Exception as e:
        error_msg = f"Error in {TASK_NAME}: {str(e)}"
        print(json.dumps({"task_name": TASK_NAME, "error": error_msg}))
        sys.exit(1)

if __name__ == "__main__":
    main()