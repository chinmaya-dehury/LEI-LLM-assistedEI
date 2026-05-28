"""
Task: Hourly_Humidity_Trend_Analysis
Description: Analyzes hourly humidity trends for better understanding of indoor environmental conditions
"""

import pandas as pd

# Load data
raw_data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Group by hour and calculate mean humidity
hourly_humidity = raw_data.groupby('timestamp.dt.hour')['humidity_percent'].mean()

# Save result to JSON
import json
result = {'hourly_humidity': hourly_humidity.to_dict()}
with open('output/temp_humidity/Hourly_Humidity_Trend_Analysis_result.json', 'w') as f:
    json.dump(result, f)
