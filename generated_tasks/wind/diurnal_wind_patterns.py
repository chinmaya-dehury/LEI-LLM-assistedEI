"""
Task: diurnal_wind_patterns
Description: Analyze hourly wind trends to understand day vs night wind behavior and identify diurnal patterns.
"""

import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")

df = pd.read_csv(data_path)

df['date'] = pd.to_datetime(df['date'])

df['hour'] = df['date'].dt.hour

day_wind_speed = df[(df['hour'] >= 6) & (df['hour'] <= 18)].groupby('hour')[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].mean()

night_wind_speed = df[(df['hour'] < 6) | (df['hour'] > 18)].groupby('hour')[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].mean()

result_summary = []

for i, row in day_wind_speed.iterrows():
    result_summary.append({
        'name': f'Day Wind Speed at {i} hour',
        'value': row['wind_speed_10m'],
        'description': 'Average wind speed during day time',
        'timestamp': datetime.now().isoformat()
    })

for i, row in night_wind_speed.iterrows():
    result_summary.append({
        'name': f'Night Wind Speed at {i} hour',
        'value': row['wind_speed_10m'],
        'description': 'Average wind speed during night time',
        'timestamp': datetime.now().isoformat()
    })

result = {
    'task_name': 'diurnal_wind_patterns',
    'description': 'Analyze hourly wind trends to understand day vs night wind behavior and identify diurnal patterns.',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

output_path = os.path.join("output", "wind", "diurnal_wind_patterns_result.json")

with open(output_path, 'w') as f:
    json.dump(result, f, indent=4)