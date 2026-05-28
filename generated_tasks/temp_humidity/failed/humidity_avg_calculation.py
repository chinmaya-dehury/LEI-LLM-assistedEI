"""
Task: Humidity_Avg_Calculation
Description: Calculates the hourly average humidity in percentage
"""

import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join('data', 'temp_humidity', 'raw_data.csv')
output_path = os.path.join('output', 'temp_humidity', 'Humidity_Avg_Calculation_result.json')

data = pd.read_csv(data_path)
data['timestamp'] = pd.to_datetime(data['timestamp'])
data['hour'] = data['timestamp'].dt.hour
data['hourly_avg_humidity'] = data.groupby('hour')['humidity_percent'].transform('mean')

data['hourly_avg_humidity'] = data['hourly_avg_humidity'].round(2)
result = data[['hour', 'hourly_avg_humidity']].drop_duplicates().to_dict(orient='records')

result_summary = []
for item in result:
    result_summary.append({'hour': item['hour'], 'avg_humidity': item['hourly_avg_humidity']})

task_result = {
    "task_name": "Humidity_Avg_Calculation",
    "description": "Calculates the hourly average humidity in percentage",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

with open(output_path, 'w') as f:
    json.dump(task_result, f)