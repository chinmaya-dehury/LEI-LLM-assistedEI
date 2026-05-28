"""
Task: Occupancy_Environmental_Correlation
Description: Analyzes the correlation between occupancy and environmental conditions for data-driven decisions
"""

import pandas as pd
import numpy as np
from scipy.stats import pearsonr

# Load data
raw_data = pd.read_csv('data/temp_humidity/raw_data.csv')

# Handle missing values
raw_data.fillna(raw_data.mean(), inplace=True)

# Calculate correlation
corr_coef, _ = pearsonr(raw_data['temperature_c'], raw_data['humidity_percent'])

# Print result
print(f'Correlation coefficient: {corr_coef}')

# Save result
pd.DataFrame({'correlation_coefficient': [corr_coef]}).to_json('output/temp_humidity/Occupancy_Environmental_Correlation_result.json')