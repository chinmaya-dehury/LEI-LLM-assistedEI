"""
Task: wind_shear_analysis
Description: Analyze the variation in wind speed across different altitude layers (10m to 180m) to understand wind shear patterns.
"""

import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")

df = pd.read_csv(data_path)

df['date'] = pd.to_datetime(df['date'])

df['wind_shear_10m_80m'] = df['wind_speed_80m'] - df['wind_speed_10m']
df['wind_shear_80m_120m'] = df['wind_speed_120m'] - df['wind_speed_80m']
df['wind_shear_120m_180m'] = df['wind_speed_180m'] - df['wind_speed_120m']

result_summary = []
for index, row in df.iterrows():
    result_summary.append({
        'name': 'Wind Shear at ' + str(row['date']),
        'value': row['wind_shear_10m_80m'],
        'description': 'Wind shear between 10m and 80m',
        'timestamp': row['date'].isoformat()
    })
    result_summary.append({
        'name': 'Wind Shear at ' + str(row['date']),
        'value': row['wind_shear_80m_120m'],
        'description': 'Wind shear between 80m and 120m',
        'timestamp': row['date'].isoformat()
    })
    result_summary.append({
        'name': 'Wind Shear at ' + str(row['date']),
        'value': row['wind_shear_120m_180m'],
        'description': 'Wind shear between 120m and 180m',
        'timestamp': row['date'].isoformat()
    })

result = {
    'task_name': 'wind_shear_analysis',
    'description': 'Analyze the variation in wind speed across different altitude layers (10m to 180m) to understand wind shear patterns.',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

with open(os.path.join(output_path, 'wind_shear_analysis_result.json'), 'w') as f:
    json.dump(result, f)