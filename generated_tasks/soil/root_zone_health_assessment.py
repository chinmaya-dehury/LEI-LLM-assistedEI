"""
Task: root_zone_health_assessment
Description: Evaluate the root zone health based on temperature-moisture balance for precision agriculture
"""

import os
import json
from datetime import datetime
import pandas as pd

# Define the data path and task name
DATA_TYPE = "soil"
task_name = "root_zone_health_assessment"

# Load the dataset
data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
df = pd.read_csv(data_path)

# Calculate the average soil temperature and moisture at root zone (0-1cm and 1-3cm depth)
df["avg_soil_temp"] = (df["soil_temperature_0cm"] + df["soil_temperature_6cm"] + df["soil_temperature_18cm"] + df["soil_temperature_54cm"])/4
df["avg_soil_moisture"] = (df["soil_moisture_0_to_1cm"] + df["soil_moisture_1_to_3cm"])/2

# Evaluate the root zone health based on temperature-moisture balance
def evaluate_root_zone_health(avg_soil_temp, avg_soil_moisture):
    if avg_soil_temp > 20 and avg_soil_moisture < 0.2:
        return "Stressed"
    elif avg_soil_temp < 15 and avg_soil_moisture > 0.5:
        return "Waterlogged"
    else:
        return "Healthy"

df["root_zone_health"] = df.apply(lambda row: evaluate_root_zone_health(row["avg_soil_temp"], row["avg_soil_moisture"]), axis=1)

# Save the result to a JSON file
result = {
    "task_name": task_name,
    "description": "Evaluate the root zone health based on temperature-moisture balance for precision agriculture",
    "result_summary": df["root_zone_health"].value_counts().to_dict(),
    "result_generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

output_path = os.path.join("output", DATA_TYPE, f"{task_name}_result.json")
with open(output_path, "w") as f:
    json.dump(result, f)