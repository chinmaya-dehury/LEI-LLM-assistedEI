"""
Task: Alert_Trigging_for_Comfort_Threshold_Exceedance
Description: Triggers alerts when comfort thresholds are exceeded for temperature, humidity, or both
"""

import pandas as pd
import json

# Load data
raw_data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Define comfort thresholds
comfort_threshold_temp = 28
comfort_threshold_humidity = 60

# Check for threshold exceedance
threshold_exceeded = raw_data[(raw_data['temperature_c'] > comfort_threshold_temp) | (raw_data['humidity_percent'] > comfort_threshold_humidity)]

# Save results
result = threshold_exceeded.to_json(orient='records')
with open('output/temp_humidity/Alert_Trigging_for_Comfort_Threshold_Exceedance_result.json', 'w') as f:
    f.write(result)

# Print result summary
print('Threshold exceeded:', threshold_exceeded.shape[0])