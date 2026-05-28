"""
Task: drought_stress_detection
Description: Detect drought stress and set early warning thresholds for irrigation management
"""

import os
import json
from datetime import datetime
import pandas as pd

# Define drought stress thresholds
low_threshold = 0.1
high_threshold = 0.3

# Load data
data_path = os.path.join('data', 'soil', 'raw_data.csv')
try:
    data = pd.read_csv(data_path)
except Exception as e:
    print(f'Error loading data: {e}')
    exit(1)

# Calculate drought stress
data['drought_stress'] = data['soil_moisture_0_to_1cm'].apply(lambda x: 'low' if x < low_threshold else ('high' if x > high_threshold else 'normal'))

# Save results
result = {
    'task_name': 'drought_stress_detection',
    'description': 'Detect drought stress and set early warning thresholds for irrigation management',
    'result_summary': data['drought_stress'].value_counts().to_dict(),
    'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}
output_path = os.path.join('output', 'soil', 'drought_stress_detection_result.json')
with open(output_path, 'w') as f:
    json.dump(result, f)