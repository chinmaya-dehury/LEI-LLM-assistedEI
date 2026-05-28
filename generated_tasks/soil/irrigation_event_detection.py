"""
Task: irrigation_event_detection
Description: Automatically detect irrigation events from soil moisture data to assess irrigation efficiency
"""

import os
import json
import pandas as pd
from datetime import datetime

data_path = os.path.join('data', 'soil', 'raw_data.csv')
output_path = os.path.join('output', 'soil', 'irrigation_event_detection_result.json')

# Load data
try:
    data = pd.read_csv(data_path)
except Exception as e:
    print(f'Error loading data: {e}')
    exit(1)

data['date'] = pd.to_datetime(data['date'])

data['soil_moisture_0_to_1cm_diff'] = data['soil_moisture_0_to_1cm'].diff()
irrigation_events = data[data['soil_moisture_0_to_1cm_diff'] > 0.05]

result = {
    'task_name': 'irrigation_event_detection',
    'description': 'Automatically detect irrigation events from soil moisture data to assess irrigation efficiency',
    'result_summary': irrigation_events['date'].tolist(),
    'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

with open(output_path, 'w') as f:
    json.dump(result, f)