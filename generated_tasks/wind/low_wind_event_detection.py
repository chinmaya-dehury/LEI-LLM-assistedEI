"""
Task: low_wind_event_detection
Description: Identify calm periods that may impact energy production and detect low wind events.
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")
task_name = "low_wind_event_detection"

def detect_low_wind_events(df):
    # Define low wind speed threshold (m/s)
    threshold = 2
    
    # Identify low wind events
    low_wind_events = df[(df['wind_speed_10m'] < threshold) & (df['wind_speed_80m'] < threshold) & (df['wind_speed_120m'] < threshold) & (df['wind_speed_180m'] < threshold)]
    
    return low_wind_events

df = pd.read_csv(data_path)
low_wind_events = detect_low_wind_events(df)

result_summary = []
for index, row in low_wind_events.iterrows():
    result_summary.append({
        "name": "Low Wind Event",
        "value": row['date'],
        "description": "Low wind speed event detected at {}".format(row['date']),
        "timestamp": datetime.now().isoformat()
    })

result = {
    "task_name": task_name,
    "description": "Identify calm periods that may impact energy production and detect low wind events.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}

with open(os.path.join(output_path, '{}_result.json'.format(task_name)), 'w') as f:
    json.dump(result, f, indent=4)