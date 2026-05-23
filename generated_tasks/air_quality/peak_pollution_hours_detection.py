import pandas as pd
import numpy as np
from datetime import datetime
import os
import json

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

df['hour'] = df['timestamp_utc'].dt.hour

df['aqi_uk'] = pd.to_numeric(df['aqi_uk'])

df_grouped = df.groupby('hour')['aqi_uk'].mean().reset_index()

df_sorted = df_grouped.sort_values(by='aqi_uk', ascending=False)

peak_hours = df_sorted.head(2)['hour'].tolist()

result_summary = [
    {
        "name": "Peak Pollution Hours",
        "value": peak_hours,
        "description": "Hours when air quality worsens",
        "timestamp": datetime.now().isoformat()
    }
]

result = {
    "task_name": "peak_pollution_hours_detection",
    "description": "Detect the peak pollution hours when air quality worsens and notify citizens accordingly.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}

output_path = os.path.join("output", "air_quality", "peak_pollution_hours_detection_result.json")

with open(output_path, 'w') as f:
    json.dump(result, f, indent=4)