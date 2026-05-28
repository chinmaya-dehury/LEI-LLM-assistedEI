"""
Task: Occupancy_Correlation_Analysis
Description: Analyzes the correlation between occupancy and environmental conditions
"""

import pandas as pd
import numpy as np

# Load data
raw_data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Handle missing values
raw_data.fillna(raw_data.mean(), inplace=True)

# Calculate correlation
correlation = raw_data['temperature_c'].corr(raw_data['humidity_percent'])

# Print result
print(f'Correlation between temperature and humidity: {correlation}')
