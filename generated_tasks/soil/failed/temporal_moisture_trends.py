"""
Task: temporal_moisture_trends
Description: Examine temporal moisture trends for predictive irrigation scheduling and crop yield prediction
"""

import os
import json
import pandas as pd
from datetime import datetime

data_path = os.path.join('data', 'soil', 'raw_data.csv')
output_path = os.path.join('output', 'soil', 'temporal_moisture_trends_result.json')

# Load data
try:
    data = pd.read_csv(data_path)
except Exception as e:
    print(f'Error loading data: {e}')
    result = {'task_name': 'temporal_moisture_trends', 'description': 'Examine temporal moisture trends for predictive irrigation scheduling and crop yield prediction', 'result_summary': ['Error loading data'], 'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    with open(output_path, 'w') as f:
        json.dump(result, f)
    exit()

# Calculate temporal moisture trends
moisture_columns = ['soil_moisture_0_to_1cm', 'soil_moisture_1_to_3cm', 'soil_moisture_9_to_27cm']
trends = {}
for column in moisture_columns:
    trends[column] = data[column].mean()

# Save result
result = {'task_name': 'temporal_moisture_trends', 'description': 'Examine temporal moisture trends for predictive irrigation scheduling and crop yield prediction', 'result_summary': [f'{column}: {trend}' for column, trend in trends.items()], 'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
with open(output_path, 'w') as f:
    json.dump(result, f)