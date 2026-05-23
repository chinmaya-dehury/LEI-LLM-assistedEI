import pandas as pd
import numpy as np
from datetime import datetime
import os
import json

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

df['month'] = df['timestamp_utc'].dt.month

df_winter = df[(df['month'] >= 12) | (df['month'] <= 2)]

df_summer = df[(df['month'] >= 6) & (df['month'] <= 8)]

winter_pollution = df_winter[['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']].mean().mean()
summer_pollution = df_summer[['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']].mean().mean()

result = {
  "task_name": "seasonal_variation_analysis",
  "description": "Analyze the seasonal variation in pollution levels to determine if there is an increase in pollution during winter or summer months.",
  "result_summary": [
    {
      "name": "Winter Pollution Level",
      "value": winter_pollution,
      "description": "Average pollution level during winter months.",
      "timestamp": datetime.now().isoformat()
    },
    {
      "name": "Summer Pollution Level",
      "value": summer_pollution,
      "description": "Average pollution level during summer months.",
      "timestamp": datetime.now().isoformat()
    }
  ],
  "result_generated_at": datetime.now().isoformat()
}

output_path = os.path.join("output", "air_quality", "seasonal_variation_analysis_result.json")
with open(output_path, 'w') as f:
  json.dump(result, f, indent=4)