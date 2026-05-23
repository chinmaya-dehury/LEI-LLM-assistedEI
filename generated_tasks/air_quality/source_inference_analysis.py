import pandas as pd
import numpy as np
from datetime import datetime
import os
import json

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

df['hour'] = df['timestamp_utc'].dt.hour

df['day_of_week'] = df['timestamp_utc'].dt.dayofweek

df['co_avg'] = df['co'].rolling(window=5).mean()
df['no_avg'] = df['no'].rolling(window=5).mean()
df['no2_avg'] = df['no2'].rolling(window=5).mean()
df['so2_avg'] = df['so2'].rolling(window=5).mean()
df['pm2_5_avg'] = df['pm2_5'].rolling(window=5).mean()
df['pm10_avg'] = df['pm10'].rolling(window=5).mean()

traffic_pollutants = ['co', 'no', 'no2']
industry_pollutants = ['so2', 'pm2_5', 'pm10']
agriculture_pollutants = ['nh3']

traffic_avg = df[traffic_pollutants].mean().mean()
industry_avg = df[industry_pollutants].mean().mean()
agriculture_avg = df[agriculture_pollutants].mean().mean()

result_summary = []

if traffic_avg > industry_avg and traffic_avg > agriculture_avg:
    result_summary.append({'name': 'Traffic', 'value': traffic_avg, 'description': 'Traffic is the main source of pollution', 'timestamp': datetime.now().isoformat()})
elif industry_avg > traffic_avg and industry_avg > agriculture_avg:
    result_summary.append({'name': 'Industry', 'value': industry_avg, 'description': 'Industry is the main source of pollution', 'timestamp': datetime.now().isoformat()})
elif agriculture_avg > traffic_avg and agriculture_avg > industry_avg:
    result_summary.append({'name': 'Agriculture', 'value': agriculture_avg, 'description': 'Agriculture is the main source of pollution', 'timestamp': datetime.now().isoformat()})

result = {'task_name': 'source_inference_analysis', 'description': 'Analyze the pollution data to infer the potential sources of pollution', 'result_summary': result_summary, 'result_generated_at': datetime.now().isoformat()}

output_path = os.path.join("output", "air_quality", "source_inference_analysis_result.json")

with open(output_path, 'w') as f:
    json.dump(result, f)

print(result)