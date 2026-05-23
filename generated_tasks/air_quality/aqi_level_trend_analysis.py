import pandas as pd
import numpy as np
import os
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

df['aqi_level'] = pd.cut(df['aqi_uk'], bins=[0, 12, 35, 55, 150, np.inf], labels=['Good', 'Moderate', 'Unhealthy', 'Very Unhealthy', 'Hazardous'])

result_summary = []
for level in df['aqi_level'].unique():
    count = df[df['aqi_level'] == level].shape[0]
    result_summary.append({'name': level, 'value': count, 'description': f'Number of {level} AQI levels', 'timestamp': datetime.now().isoformat()})

result = {'task_name': 'aqi_level_trend_analysis', 'description': 'Analyze the overall air quality score trend and categorize it into Good, Moderate, Unhealthy, Very Unhealthy, or Hazardous levels.', 'result_summary': result_summary, 'result_generated_at': datetime.now().isoformat()}

import json
with open(os.path.join('output', 'air_quality', 'aqi_level_trend_analysis_result.json'), 'w') as f:
    json.dump(result, f)