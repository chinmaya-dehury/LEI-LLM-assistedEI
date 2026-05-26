"""
Task: wind_persistence
Description: Evaluate the duration of favorable wind speeds for energy generation to assess wind persistence.
"""

import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")

df = pd.read_csv(data_path)
df['date'] = pd.to_datetime(df['date'])

# Define favorable wind speeds for energy generation (e.g., between 5 and 25 m/s)
favorable_wind_speeds = (df['wind_speed_80m'] >= 5) & (df['wind_speed_80m'] <= 25)

# Calculate the duration of favorable wind speeds
persistence_durations = []
for i in range(len(df) - 1):
    if favorable_wind_speeds.iloc[i] and favorable_wind_speeds.iloc[i + 1]:
        persistence_durations.append((df['date'].iloc[i + 1] - df['date'].iloc[i]).total_seconds() / 3600)

# Calculate the average persistence duration
average_persistence = sum(persistence_durations) / len(persistence_durations) if persistence_durations else 0

# Create the result summary
result_summary = [
    {
        "name": "Average Wind Persistence Duration",
        "value": average_persistence,
        "description": "Average duration of favorable wind speeds for energy generation (hours)",
        "timestamp": datetime.now().isoformat()
    }
]

# Save the result to a JSON file
result = {
    "task_name": "wind_persistence",
    "description": "Evaluate the duration of favorable wind speeds for energy generation to assess wind persistence.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}
with open(os.path.join(output_path, "wind_persistence_result.json"), "w") as f:
    json.dump(result, f, indent=4)