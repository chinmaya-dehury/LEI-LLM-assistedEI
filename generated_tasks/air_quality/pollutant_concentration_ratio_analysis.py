import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['co_no_ratio'] = df['co'] / df['no']
df['no2_no_ratio'] = df['no2'] / df['no']
df['o3_no_ratio'] = df['o3'] / df['no']
df['so2_no_ratio'] = df['so2'] / df['no']
df['pm2_5_no_ratio'] = df['pm2_5'] / df['no']
df['pm10_no_ratio'] = df['pm10'] / df['no']
df['nh3_no_ratio'] = df['nh3'] / df['no']

result_summary = []
for column in df.columns:
    if 'ratio' in column:
        result_summary.append({
            'name': column,
            'value': df[column].mean(),
            'description': f'Mean {column} ratio',
            'timestamp': datetime.now().isoformat()
        })

result = {
    'task_name': 'pollutant_concentration_ratio_analysis',
    'description': 'Analyze the ratio of different pollutant concentrations to identify potential patterns and correlations.',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

output_path = os.path.join("output", "air_quality", "pollutant_concentration_ratio_analysis_result.json")
with open(output_path, 'w') as f:
    json.dump(result, f)