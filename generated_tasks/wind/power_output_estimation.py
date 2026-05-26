"""
Task: power_output_estimation
Description: Estimate the wind energy potential at turbine hub heights (80m, 120m) based on wind speed data.
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")

def estimate_power_output(wind_speed):
    # Using a simplified power curve for a typical wind turbine
    power_output = 0.5 * 1.225 * np.pi * (50 ** 2) * (wind_speed ** 3) / 1000
    return power_output

df = pd.read_csv(data_path)
df['date'] = pd.to_datetime(df['date'])

df_80m = df[['date', 'wind_speed_80m']]
df_120m = df[['date', 'wind_speed_120m']]

df_80m['power_output'] = df_80m['wind_speed_80m'].apply(estimate_power_output)
df_120m['power_output'] = df_120m['wind_speed_120m'].apply(estimate_power_output)

result_summary = [
    {
        'name': 'Average Power Output at 80m',
        'value': df_80m['power_output'].mean(),
        'description': 'Average power output at 80m turbine hub height',
        'timestamp': datetime.now().isoformat()
    },
    {
        'name': 'Average Power Output at 120m',
        'value': df_120m['power_output'].mean(),
        'description': 'Average power output at 120m turbine hub height',
        'timestamp': datetime.now().isoformat()
    }
]

result = {
    'task_name': 'power_output_estimation',
    'description': 'Estimate the wind energy potential at turbine hub heights (80m, 120m) based on wind speed data.',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

with open(os.path.join(output_path, 'power_output_estimation_result.json'), 'w') as f:
    json.dump(result, f, indent=4)
print('Power output estimation result saved to', os.path.join(output_path, 'power_output_estimation_result.json'))