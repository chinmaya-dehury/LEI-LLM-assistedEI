"""
Task: Temperature_Anomaly_Detection
Description: Detects anomalies in temperature readings indicating potential HVAC malfunctions
"""

import os
import json
from datetime import datetime
import pandas as pd

# Load data
DATA_TYPE = "temp_humidity"
data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
df = pd.read_csv(data_path)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df.sort_values(by="timestamp", inplace=True)

# Calculate mean and standard deviation
mean_temp = df["temperature_c"].mean()
std_temp = df["temperature_c"].std()

# Detect anomalies
anomalies = df[(df["temperature_c"] < (mean_temp - 2*std_temp)) | (df["temperature_c"] > (mean_temp + 2*std_temp))]

# Create result dictionary
result = {
    "task_name": "Temperature_Anomaly_Detection",
    "description": "Detects anomalies in temperature readings indicating potential HVAC malfunctions",
    "result_summary": anomalies["timestamp"].tolist(),
    "result_generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

# Save result to JSON file
output_path = os.path.join("output", DATA_TYPE, "Temperature_Anomaly_Detection_result.json")
with open(output_path, "w") as f:
    json.dump(result, f)