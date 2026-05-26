"""
Task: wind_direction_consistency
Description: Assess the consistency of wind direction across different heights to determine directional stability.
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")

df = pd.read_csv(data_path)

directions = ["wind_direction_10m", "wind_direction_80m", "wind_direction_120m", "wind_direction_180m"]

df[directions] = df[directions].apply(pd.to_numeric, errors='coerce')

df['direction_diff_10m_80m'] = np.abs(df['wind_direction_10m'] - df['wind_direction_80m'])

df['direction_diff_80m_120m'] = np.abs(df['wind_direction_80m'] - df['wind_direction_120m'])

df['direction_diff_120m_180m'] = np.abs(df['wind_direction_120m'] - df['wind_direction_180m'])

consistency = df[['direction_diff_10m_80m', 'direction_diff_80m_120m', 'direction_diff_120m_180m']].mean().to_dict()

result = {
    "task_name": "wind_direction_consistency",
    "description": "Assess the consistency of wind direction across different heights to determine directional stability.",
    "result_summary": [
        {
            "name": "direction_diff_10m_80m",
            "value": consistency['direction_diff_10m_80m'],
            "description": "Average absolute difference in wind direction between 10m and 80m heights.",
            "timestamp": datetime.now().isoformat()
        },
        {
            "name": "direction_diff_80m_120m",
            "value": consistency['direction_diff_80m_120m'],
            "description": "Average absolute difference in wind direction between 80m and 120m heights.",
            "timestamp": datetime.now().isoformat()
        },
        {
            "name": "direction_diff_120m_180m",
            "value": consistency['direction_diff_120m_180m'],
            "description": "Average absolute difference in wind direction between 120m and 180m heights.",
            "timestamp": datetime.now().isoformat()
        }
    ],
    "result_generated_at": datetime.now().isoformat()
}

with open(os.path.join(output_path, 'wind_direction_consistency_result.json'), 'w') as f:
    json.dump(result, f, indent=4)