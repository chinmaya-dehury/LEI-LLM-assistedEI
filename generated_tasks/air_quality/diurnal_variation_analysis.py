import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

df['hour'] = df['timestamp_utc'].dt.hour

df_grouped = df.groupby('hour')[['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']].mean()

result_summary = []
for hour, row in df_grouped.iterrows():
    result_summary.append({
        'name': f'Hour {hour} Average Pollution Levels',
        'value': {k: v for k, v in row.items()},
        'description': f'Average pollution levels for hour {hour}',
        'timestamp': datetime.now().isoformat()
    })

result = {
    'task_name': 'diurnal_variation_analysis',
    'description': 'Analyze the diurnal variation in air quality to identify patterns and trends in pollution levels throughout the day.',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

output_path = os.path.join('output', 'air_quality', 'diurnal_variation_analysis_result.json')
with open(output_path, 'w') as f:
    json.dump(result, f, indent=4)