"""
Task: time_of_day_wind_analysis
Description: Examine wind speed and direction patterns at specific times of day (e.g., morning, afternoon, evening) to understand diel variations in wind behavior.
"""

import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")
task_name = "time_of_day_wind_analysis"

df = pd.read_csv(data_path)
df['date'] = pd.to_datetime(df['date'])
df['hour'] = df['date'].dt.hour

df_morning = df[(df['hour'] >= 6) & (df['hour'] < 12)]
df_afternoon = df[(df['hour'] >= 12) & (df['hour'] < 18)]
df_evening = df[(df['hour'] >= 18) & (df['hour'] < 24)]

df_morning_avg = df_morning[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].mean()
df_afternoon_avg = df_afternoon[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].mean()
df_evening_avg = df_evening[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].mean()

result_summary = [
    {
        "name": "morning_avg",
        "value": df_morning_avg.to_dict(),
        "description": "Average wind speed at different heights during morning hours",
        "timestamp": datetime.now().isoformat()
    },
    {
        "name": "afternoon_avg",
        "value": df_afternoon_avg.to_dict(),
        "description": "Average wind speed at different heights during afternoon hours",
        "timestamp": datetime.now().isoformat()
    },
    {
        "name": "evening_avg",
        "value": df_evening_avg.to_dict(),
        "description": "Average wind speed at different heights during evening hours",
        "timestamp": datetime.now().isoformat()
    }
]

result = {
    "task_name": task_name,
    "description": "Examine wind speed and direction patterns at specific times of day to understand diel variations in wind behavior.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}

with open(os.path.join(output_path, f"{task_name}_result.json"), 'w') as f:
    json.dump(result, f, indent=4)