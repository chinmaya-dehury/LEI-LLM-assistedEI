"""
Task: HVAC_System_Efficiency_Evaluation
Description: Evaluates HVAC system efficiency based on temperature trends and energy consumption
"""

import pandas as pd
import numpy as np

# Load data
raw_data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Calculate temperature trend
trend = raw_data['temperature_c'].diff()

# Evaluate HVAC system efficiency
efficiency = np.mean(trend)

# Print result
print(f'HVAC system efficiency: {efficiency:.2f}°C/h')
