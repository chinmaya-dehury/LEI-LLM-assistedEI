import pandas as pd
import json
import os
from datetime import datetime

# Set file paths
data_path = os.path.join("data", "air_quality", "raw_data.csv")
output_path = os.path.join("output", "air_quality", "seasonal_pollution_trend_result.json")

# Load data
try:
    df = pd.read_csv(data_path)
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
    df.set_index('timestamp_utc', inplace=True)
except Exception as e:
    print(f"Error loading data: {str(e)}")
    exit()

# Extract month and year
df['month_year'] = df.index.strftime('%Y-%m')

# Calculate monthly averages
monthly_avg = df.resample('M').mean()
monthly_avg['month_year'] = monthly_avg.index.strftime('%Y-%m')

# Identify seasonal trends
seasonal_trend = []
for col in ['pm2_5', 'pm10', 'o3', 'no2']:
    if col in df.columns:
        trend_data = monthly_avg[[col, 'month_year']].sort_values('month_year')
        trend_summary = {
            "name": f"{col} Seasonal Trend",
            "value": trend_data.to_dict(orient='records'),
            "description": f"Monthly average {col} concentrations showing seasonal variation",
            "timestamp": datetime.now().isoformat()
        }
        seasonal_trend.append(trend_summary)

# Save results
result = {
    "task_name": "seasonal_pollution_trend",
    "description": "Analyze monthly pollution patterns to identify seasonal variations",
    "result_summary": seasonal_trend,
    "result_generated_at": datetime.now().isoformat()
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)
print(f"Results saved to {output_path}")