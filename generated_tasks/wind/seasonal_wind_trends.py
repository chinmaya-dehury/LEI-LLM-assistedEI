"""
Task: seasonal_wind_trends
Description: Analyze wind speed and direction patterns across different seasons to understand seasonal variations and optimize wind energy production.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import json

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")

df = pd.read_csv(data_path)
df['date'] = pd.to_datetime(df['date'])
df['season'] = df['date'].dt.month.apply(lambda x: 'Spring' if x in [3, 4, 5] else 'Summer' if x in [6, 7, 8] else 'Autumn' if x in [9, 10, 11] else 'Winter')

df_grouped = df.groupby('season')[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].mean()

df_direction = df.groupby('season')[['wind_direction_10m', 'wind_direction_80m', 'wind_direction_120m', 'wind_direction_180m']].mean()

result_summary = []
for season, row in df_grouped.iterrows():
    result_summary.append({
        'name': f'{season} Wind Speed',
        'value': row.mean(),
        'description': f'Average wind speed in {season} season',
        'timestamp': datetime.now().isoformat()
    })

for season, row in df_direction.iterrows():
    result_summary.append({
        'name': f'{season} Wind Direction',
        'value': row.mean(),
        'description': f'Average wind direction in {season} season',
        'timestamp': datetime.now().isoformat()
    })

result = {
    'task_name': 'seasonal_wind_trends',
    'description': 'Analyze wind speed and direction patterns across different seasons',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

with open(os.path.join(output_path, 'seasonal_wind_trends_result.json'), 'w') as f:
    json.dump(result, f)