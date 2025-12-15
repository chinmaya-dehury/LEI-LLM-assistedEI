import pandas as pd
import os
from datetime import datetime

# Define WHO thresholds for vulnerable populations
WHO_THRESHOLDS = {
    'PM2.5': [0, 35, 55, 150, 250],
    'O3': [0, 50, 75, 150, 250],
    'categories': ['Good', 'Moderate', 'Poor', 'Very Poor', 'Severe']
}

# Get data path
data_type = 'air_quality'
data_path = os.path.join('data', data_type, 'raw_data.csv')
output_path = os.path.join('output', data_type, f'{task_name}_result.json')

# Load data
try:
    df = pd.read_csv(data_path, parse_dates=['timestamp_utc'])
    latest_row = df.iloc[-1]
    pm2_5 = latest_row['pm2_5']
    o3 = latest_row['o3']
    timestamp = latest_row['timestamp_utc']
except Exception as e:
    print(f"Error loading data: {str(e)}")
    exit()

# Calculate AQI for PM2.5 and O3
def calculate_aqi(pollutant, value):
    thresholds = WHO_THRESHOLDS[pollutant]
    for i in range(len(thresholds)-1):
        if value <= thresholds[i+1]:
            return WHO_THRESHOLDS['categories'][i]
    return WHO_THRESHOLDS['categories'][-1]

pm2_5_category = calculate_aqi('PM2.5', pm2_5)
 o3_category = calculate_aqi('O3', o3)

# Generate health alert
alert = """
Health Alert - {timestamp}:
PM2.5: {pm2_5} µg/m³ ({pm2_5_category})
O3: {o3} µg/m³ ({o3_category})
"""

# Save result
result = {
    "task_name": "real_time_health_alert_generator",
    "description": "Generate immediate health advisories based on real-time pollutant levels",
    "result_summary": [
        {
            "name": "health_alert",
            "value": alert,
            "description": "Health advisory based on WHO thresholds for vulnerable populations",
            "timestamp": datetime.now().isoformat()
        }
    ],
    "result_generated_at": datetime.now().isoformat()
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    f.write(json.dumps(result, indent=2))