import pandas as pd
import os
from datetime import datetime

# Get data path
data_type = 'air_quality'
data_path = os.path.join('data', data_type, 'raw_data.csv')
output_path = os.path.join('output', data_type, f'{task_name}_result.json')

# Load data
try:
    df = pd.read_csv(data_path, parse_dates=['timestamp_utc'])
    df['hour'] = df['timestamp_utc'].dt.hour
    df['pm2_5'] = pd.to_numeric(df['pm2_5'], errors='coerce')
    df['o3'] = pd.to_numeric(df['o3'], errors='coerce')
except Exception as e:
    print(f"Error loading data: {str(e)}")
    exit()

# Find peak pollution hours
peak_hours = df.groupby('hour')[['pm2_5', 'o3']].max().reset_index()
peak_hours['combined'] = peak_hours['pm2_5'] + peak_hours['o3']
peak_hour = peak_hours.loc[peak_hours['combined'].idxmax()]['hour']

# Determine potential sources
sources = []
if peak_hour in [7, 8, 9, 17, 18, 19]:
    sources.append('Traffic congestion')
if peak_hour in [10, 11, 12, 13, 14]:
    sources.append('Industrial activity')
if peak_hour in [20, 21, 22]:
    sources.append('Nighttime inversion')

# Save result
result = {
    "task_name": "daily_pollution_peak_timing_analysis",
    "description": "Identify daily peak pollution hours and correlate with activity patterns",
    "result_summary": [
        {
            "name": "peak_pollution_hour",
            "value": peak_hour,
            "description": f"Hour with highest combined PM2.5 and O3 concentrations",
            "timestamp": datetime.now().isoformat()
        },
        {
            "name": "potential_sources",
            "value": sources,
            "description": "Possible sources of peak pollution based on time-of-day patterns",
            "timestamp": datetime.now().isoformat()
        }
    ],
    "result_generated_at": datetime.now().isoformat()
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    f.write(json.dumps(result, indent=2))