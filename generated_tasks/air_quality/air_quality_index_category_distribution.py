import pandas as pd
import numpy as np
from datetime import datetime
import os
import json

data_path = os.path.join("data", "air_quality", "raw_data.csv")
df = pd.read_csv(data_path)

def calculate_aqi(row):
    if row['pm2_5'] <= 12:
        return 'Good'
    elif row['pm2_5'] <= 35.4:
        return 'Moderate'
    elif row['pm2_5'] <= 55.4:
        return 'Unhealthy for sensitive groups'
    elif row['pm2_5'] <= 150.4:
        return 'Unhealthy'
    elif row['pm2_5'] <= 250.4:
        return 'Very unhealthy'
    else:
        return 'Hazardous'

df['aqi_category'] = df.apply(calculate_aqi, axis=1)

distribution = df['aqi_category'].value_counts().to_dict()
result_summary = []
for category, count in distribution.items():
    result_summary.append({
        'name': category,
        'value': count,
        'description': f'Number of times {category} air quality was recorded',
        'timestamp': datetime.now().isoformat()
    })
result = {
    'task_name': 'air_quality_index_category_distribution',
    'description': 'Analyze the distribution of air quality index categories over time',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}
output_path = os.path.join("output", "air_quality")
if not os.path.exists(output_path):
    os.makedirs(output_path)
with open(os.path.join(output_path, 'air_quality_index_category_distribution_result.json'), 'w') as f:
    json.dump(result, f)