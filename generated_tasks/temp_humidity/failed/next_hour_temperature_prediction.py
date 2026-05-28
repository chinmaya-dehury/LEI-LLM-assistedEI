"""
Task: Next_Hour_Temperature_Prediction
Description: Makes a simple next-hour temperature prediction using the last hour's data
"""

import pandas as pd
import numpy as np

# Load data
raw_data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Filter last hour's data
last_hour_data = raw_data[raw_data['timestamp'] >= raw_data['timestamp'].max() - pd.Timedelta(hours=1)]

# Calculate next hour's temperature prediction
prediction = last_hour_data['temperature_c'].iloc[-1] + (last_hour_data['temperature_c'].iloc[-1] - last_hour_data['temperature_c'].iloc[-2])

# Save result
prediction.to_json('output/temp_humidity/Next_Hour_Temperature_Prediction_result.json')