"""
Task: optimal_turbine_height
Description: Identify the optimal turbine height by analyzing wind conditions at different altitudes.
"""

import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")
task_name = "optimal_turbine_height"

df = pd.read_csv(data_path)

df['date'] = pd.to_datetime(df['date'])

df['wind_speed_avg'] = df[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].mean(axis=1)

optimal_height = df[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].mean().idxmax()

result_summary = [
    {
        "name": "Optimal Turbine Height",
        "value": optimal_height,
        "description": "The altitude with the highest average wind speed.",
        "timestamp": datetime.now().isoformat()
    }
]

result = {
    "task_name": task_name,
    "description": "Identify the optimal turbine height by analyzing wind conditions at different altitudes.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}

with open(os.path.join(output_path, f"{task_name}_result.json"), 'w') as f:
    json.dump(result, f, indent=4)

print(json.dumps(result, indent=4))