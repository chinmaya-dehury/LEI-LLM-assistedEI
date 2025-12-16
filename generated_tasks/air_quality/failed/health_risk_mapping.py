import pandas as pd
import json
import os
from datetime import datetime

# Define WHO health risk thresholds (µg/m³)
health_risk = {
    'PM2.5': {"Good": (0, 12), "Moderate": (13, 35), "Poor": (36, 56), "Very Poor": (57, 150), "Severe": (151, float('inf'))},
    'O3': {"Good": (0, 50), "Moderate": (51, 100), "Poor": (101, 150), "Very Poor": (151, 250), "Severe": (251, float('inf'))}
}

# Set file paths
data_path = os.path.join("data", "air_quality", "raw_data.csv")
output_path = os.path.join("output", "air_quality", "health_risk_mapping_result.json")

# Load data
try:
    df = pd.read_csv(data_path)
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
    df.set_index('timestamp_utc', inplace=True)
except Exception as e:
    print(f"Error loading data: {str(e)}")
    exit()

# Calculate health risk
risk_summary = []
for pollutant, thresholds in health_risk.items():
    if pollutant in df.columns:
        df[pollutant+'_risk'] = df[pollutant].apply(lambda x: next(key for key, (low, high) in thresholds.items() if low <= x <= high))
        risk_summary.extend([
            {
                "name": f"{pollutant} Risk Level",
                "value": df[pollutant+'_risk'].mode()[0],
                "description": f"Most common health risk level for {pollutant} (WHO guidelines)",
                "timestamp": datetime.now().isoformat()
            }
        ])

# Save results
result = {
    "task_name": "health_risk_mapping",
    "description": "Map pollutant concentrations to health risk levels using WHO guidelines",
    "result_summary": risk_summary,
    "result_generated_at": datetime.now().isoformat()
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)
print(f"Results saved to {output_path}")