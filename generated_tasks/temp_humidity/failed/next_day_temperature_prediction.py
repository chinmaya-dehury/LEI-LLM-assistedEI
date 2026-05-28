"""
Task: Next_Day_Temperature_Prediction
Description: Makes a simple next-day temperature prediction using the last day's data for long-term planning
"""

import pandas as pd
import numpy as np

# Load data
data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Filter last day's data
last_day_data = data[data['timestamp'] >= data['timestamp'].max() - pd.Timedelta(days=1)]

# Calculate next-day temperature prediction
prediction = last_day_data['temperature_c'].mean() + (last_day_data['temperature_c'].max() - last_day_data['temperature_c'].min()) / 2

# Save result
prediction.to_json('output/temp_humidity/Next_Day_Temperature_Prediction_result.json')