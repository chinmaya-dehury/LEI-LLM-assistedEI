"""
Task: Temperature_Avg_Calculation
Description: Calculates the hourly average temperature in degrees Celsius
"""

import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join('data', 'temp_humidity', 'raw_data.csv')
output_path = os.path.join('output', 'temp_humidity', 'Temperature_Avg_Calculation_result.json')

data = pd.read_csv(data_path)
data['timestamp'] = pd.to_datetime(data['timestamp'])
data['hour'] = data['timestamp'].dt.hour
data_avg = data.groupby('hour')['temperature_c'].mean().reset_index()
result_summary = data_avg['temperature_c'].tolist()
result = {'task_name': 'Temperature_Avg_Calculation', 'description': 'Calculates the hourly average temperature in degrees Celsius', 'result_summary': result_summary, 'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
with open(output_path, 'w') as f:
    json.dump(result, f)