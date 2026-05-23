import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

df['pm2_5'] = pd.to_numeric(df['pm2_5'])

df['pm10'] = pd.to_numeric(df['pm10'])

# Define health risk levels based on pollution levels
health_risk_levels = {
    'low': (0, 50),
    'moderate': (51, 100),
    'high': (101, 150),
    'very_high': (151, 200),
    'extremely_high': (201, np.inf)
}

# Map health risks to pollution levels
health_risks = []
for index, row in df.iterrows():
    pm2_5 = row['pm2_5']
    pm10 = row['pm10']
    for level, (lower, upper) in health_risk_levels.items():
        if lower <= pm2_5 <= upper or lower <= pm10 <= upper:
            health_risks.append({'timestamp': row['timestamp_utc'].isoformat(), 'health_risk': level})
            break

# Save results to JSON file
result_summary = []
for health_risk in health_risks:
    result_summary.append({'name': 'Health Risk', 'value': health_risk['health_risk'], 'description': 'Health risk level based on pollution levels', 'timestamp': health_risk['timestamp']})

result = {
    'task_name': 'health_risk_mapping',
    'description': 'Map the health risks associated with pollution levels, including respiratory and cardiovascular hazards, to provide citizens with valuable insights.',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

output_path = os.path.join("output", "air_quality", "health_risk_mapping_result.json")
with open(output_path, 'w') as f:
    json.dump(result, f)