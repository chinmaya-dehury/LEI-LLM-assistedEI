"""
Task: Seasonal_Baseline_Deviation_Detection
Description: Compares seasonal baselines and detects deviations in temperature and humidity
"""

import pandas as pd
import json

# Load data
raw_data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Calculate seasonal baselines
seasonal_baselines = raw_data.groupby('timestamp.dt.month')[['temperature_c', 'humidity_percent']].mean()

# Detect deviations
developments = raw_data.merge(seasonal_baselines, on='timestamp.dt.month')
developments['deviation'] = developments.apply(lambda row: (abs(row['temperature_c'] - seasonal_baselines.loc[row['timestamp.dt.month'], 'temperature_c']) > 2) or (abs(row['humidity_percent'] - seasonal_baselines.loc[row['timestamp.dt.month'], 'humidity_percent']) > 5), axis=1)

# Save results
result = developments[['timestamp', 'temperature_c', 'humidity_percent', 'deviation']].to_json(orient='records')
with open('output/temp_humidity/Seasonal_Baseline_Deviation_Detection_result.json', 'w') as f:
    f.write(result)

# Print result summary
print('Seasonal baseline deviation detection results saved to output/temp_humidity/Seasonal_Baseline_Deviation_Detection_result.json')