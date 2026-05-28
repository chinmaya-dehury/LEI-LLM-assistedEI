"""
Task: Temperature_Humidity_Correlation
Description: Calculates the correlation between temperature and humidity for insights into environmental interactions
"""

import pandas as pd
import numpy as np

# Load data
raw_data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Calculate correlation
correlation = raw_data['temperature_c'].corr(raw_data['humidity_percent'])

# Print result
print(f'Temperature and humidity correlation: {correlation}')
