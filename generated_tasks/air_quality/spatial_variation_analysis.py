import pandas as pd
import numpy as np
import os
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

df['aqi_uk'] = pd.to_numeric(df['aqi_uk'])

df['lat'] = pd.to_numeric(df['lat'])

df['lon'] = pd.to_numeric(df['lon'])

# Calculate average AQI by location
avg_aqi_by_location = df.groupby(['lat', 'lon'])['aqi_uk'].mean().reset_index()

# Identify locations with poor air quality (AQI > 50)
poor_air_quality_locations = avg_aqi_by_location[avg_aqi_by_location['aqi_uk'] > 50]

# Print results
print("Locations with poor air quality:")
print(poor_air_quality_locations)

# Save results to JSON file
import json
result_summary = [
    {
        "name": "Poor Air Quality Locations",
        "value": poor_air_quality_locations.shape[0],
        "description": "Number of locations with poor air quality",
        "timestamp": datetime.now().isoformat()
    }
]
result = {
    "task_name": "spatial_variation_analysis",
    "description": "Analyze the spatial variation in air quality across different locations to identify areas with poor air quality and potential sources of pollution.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}
with open(os.path.join("output", "air_quality", "spatial_variation_analysis_result.json"), 'w') as f:
    json.dump(result, f)