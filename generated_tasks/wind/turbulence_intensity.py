"""
Task: turbulence_intensity
Description: Calculate the gust-to-mean wind speed ratio to evaluate turbulence intensity and its impact on structural safety.
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")
task_name = "turbulence_intensity"

df = pd.read_csv(data_path)
df['date'] = pd.to_datetime(df['date'])

df['turbulence_intensity'] = df['wind_gusts_10m'] / df['wind_speed_10m']

turbulence_intensity_mean = df['turbulence_intensity'].mean()

turbulence_intensity_result = {
  "task_name": task_name,
  "description": "Turbulence intensity calculation",
  "result_summary": [
    {
      "name": "Mean Turbulence Intensity",
      "value": turbulence_intensity_mean,
      "description": "Mean gust-to-mean wind speed ratio",
      "timestamp": datetime.now().isoformat()
    }
  ],
  "result_generated_at": datetime.now().isoformat()
}

with open(os.path.join(output_path, f"{task_name}_result.json"), 'w') as f:
  json.dump(turbulence_intensity_result, f, indent=4)
print(turbulence_intensity_result)