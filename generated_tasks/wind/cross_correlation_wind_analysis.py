"""
Task: cross_correlation_wind_analysis
Description: Compute cross-correlations between wind speeds at different altitudes to quantify the relationships between wind patterns at various heights.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")

df = pd.read_csv(data_path)

correlation_matrix = df[['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m']].corr()

result_summary = []
for i in range(len(correlation_matrix.columns)):
    for j in range(i+1, len(correlation_matrix.columns)):
        result_summary.append({
            'name': f'Correlation between {correlation_matrix.columns[i]} and {correlation_matrix.columns[j]}',
            'value': correlation_matrix.iloc[i, j],
            'description': f'Cross-correlation coefficient between wind speeds at {correlation_matrix.columns[i]} and {correlation_matrix.columns[j]}',
            'timestamp': datetime.now().isoformat()
        })

result = {
    'task_name': 'cross_correlation_wind_analysis',
    'description': 'Compute cross-correlations between wind speeds at different altitudes',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

import json
with open(os.path.join(output_path, 'cross_correlation_wind_analysis_result.json'), 'w') as f:
    json.dump(result, f)