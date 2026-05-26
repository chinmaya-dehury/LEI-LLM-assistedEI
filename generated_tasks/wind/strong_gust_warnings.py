"""
Task: strong_gust_warnings
Description: Detect extreme wind gusts to issue safety alerts and warnings.
"""

import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")

df = pd.read_csv(data_path)

gust_threshold = 10  # m/s

strong_gusts = df[df['wind_gusts_10m'] > gust_threshold]

result_summary = []
for index, row in strong_gusts.iterrows():
    result_summary.append({
        "name": "Strong Gust Warning",
        "value": row['wind_gusts_10m'],
        "description": "Wind gust speed exceeded the threshold of {} m/s at {}".format(gust_threshold, row['date']),
        "timestamp": datetime.now().isoformat()
    })

result = {
    "task_name": "strong_gust_warnings",
    "description": "Detect extreme wind gusts to issue safety alerts and warnings.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}

output_path = os.path.join("output", "wind")
if not os.path.exists(output_path):
    os.makedirs(output_path)

with open(os.path.join(output_path, "strong_gust_warnings_result.json"), 'w') as f:
    json.dump(result, f, indent=4)