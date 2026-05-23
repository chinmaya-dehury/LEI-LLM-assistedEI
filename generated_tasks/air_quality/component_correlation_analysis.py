import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

correlation_matrix = df[['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10']].corr()

result_summary = []
for i in range(len(correlation_matrix.columns)):
    for j in range(i+1, len(correlation_matrix.columns)):
        correlation_coefficient = correlation_matrix.iloc[i, j]
        result_summary.append({
            "name": f"Correlation between {correlation_matrix.columns[i]} and {correlation_matrix.columns[j]}",
            "value": correlation_coefficient,
            "description": f"The correlation coefficient between {correlation_matrix.columns[i]} and {correlation_matrix.columns[j]} is {correlation_coefficient}",
            "timestamp": datetime.now().isoformat()
        })

result = {
    "task_name": "component_correlation_analysis",
    "description": "Analyze the correlation between different air quality components",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}

output_path = os.path.join("output", "air_quality", "component_correlation_analysis_result.json")
with open(output_path, 'w') as f:
    json.dump(result, f, indent=4)