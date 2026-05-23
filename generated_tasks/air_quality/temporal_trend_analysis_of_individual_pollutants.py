import pandas as pd
import numpy as np
import os
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

df.set_index('timestamp_utc', inplace=True)

pollutants = ['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']

trends = {}

for pollutant in pollutants:
    trends[pollutant] = df[pollutant].rolling(window=5).mean()

result_summary = []

for pollutant, trend in trends.items():
    result_summary.append({
        'name': pollutant,
        'value': trend.mean(),
        'description': f'Temporal trend of {pollutant}',
        'timestamp': datetime.now().isoformat()
    })

result = {
    'task_name': 'temporal_trend_analysis_of_individual_pollutants',
    'description': 'Analyze the temporal trends of individual pollutants',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

import json

with open(os.path.join('output', 'air_quality', 'temporal_trend_analysis_of_individual_pollutants_result.json'), 'w') as f:
    json.dump(result, f, indent=4)