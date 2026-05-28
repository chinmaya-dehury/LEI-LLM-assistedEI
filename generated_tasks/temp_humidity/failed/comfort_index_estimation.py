"""
Task: Comfort_Index_Estimation
Description: Estimates the comfort index using temperature and humidity measurements
"""

import os
import json
import pandas as pd
from datetime import datetime

data_type = "temp_humidity"
task_name = "Comfort_Index_Estimation"

def estimate_comfort_index(df):
    # Simple comfort index estimation based on temperature and humidity
    df["comfort_index"] = (df["temperature_c"] - 20) ** 2 + (df["humidity_percent"] - 50) ** 2
    return df

def main():
    # Read dataset from file
    data_path = os.path.join("data", data_type, "raw_data.csv")
    df = pd.read_csv(data_path)
    
    # Estimate comfort index
    df = estimate_comfort_index(df)
    
    # Save task results to output file
    output_path = os.path.join("output", data_type, f"{task_name}_result.json")
    result_summary = df["comfort_index"].describe().to_dict()
    result = {
        "task_name": task_name,
        "description": "Estimates the comfort index using temperature and humidity measurements",
        "result_summary": result_summary,
        "result_generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(output_path, "w") as f:
        json.dump(result, f)

if __name__ == "__main__":
    main()