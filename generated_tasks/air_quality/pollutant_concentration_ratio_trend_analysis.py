import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")
df = pd.read_csv(data_path)
df['pm2_5_to_pm10_ratio'] = df['pm2_5'] / df['pm10']
df['no2_to_no_ratio'] = df['no2'] / df['no']
result = {
  "task_name": "pollutant_concentration_ratio_trend_analysis",
  "description": "Analyze the trends in pollutant concentration ratios, such as PM2.5/PM10 or NO2/NO, to identify potential changes in emission sources or atmospheric processes.",
  "result_summary": [
    {
      "name": "PM2.5/PM10 ratio mean",
      "value": df['pm2_5_to_pm10_ratio'].mean(),
      "description": "Mean PM2.5/PM10 ratio",
      "timestamp": datetime.now().isoformat()
    },
    {
      "name": "NO2/NO ratio mean",
      "value": df['no2_to_no_ratio'].mean(),
      "description": "Mean NO2/NO ratio",
      "timestamp": datetime.now().isoformat()
    }
  ],
  "result_generated_at": datetime.now().isoformat()
}
output_path = os.path.join("output", "air_quality", "pollutant_concentration_ratio_trend_analysis_result.json")
with open(output_path, 'w') as f:
  json.dump(result, f)