"""
Task: altitude_specific_wind_statistics
Description: Calculate and compare statistical measures (e.g., mean, standard deviation) of wind speed and direction at each altitude level to gain insights into altitude-specific wind characteristics.
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")
output_path = os.path.join("output", "wind")

data = pd.read_csv(data_path)

# Calculate statistics for each altitude level
altitude_levels = [10, 80, 120, 180]
statistics = {}
for altitude in altitude_levels:
    speed_column = f"wind_speed_{altitude}m"
    direction_column = f"wind_direction_{altitude}m"
    speed_mean = data[speed_column].mean()
    speed_std = data[speed_column].std()
    direction_mean = data[direction_column].mean()
    direction_std = data[direction_column].std()
    statistics[altitude] = {
        "speed_mean": speed_mean,
        "speed_std": speed_std,
        "direction_mean": direction_mean,
        "direction_std": direction_std
    }

# Save results to JSON file
result = {
    "task_name": "altitude_specific_wind_statistics",
    "description": "Calculate and compare statistical measures of wind speed and direction at each altitude level",
    "result_summary": []
}
for altitude, stats in statistics.items():
    result["result_summary"].append({
        "name": f"Altitude {altitude}m",
        "value": stats,
        "description": f"Wind speed and direction statistics at {altitude}m altitude",
        "timestamp": datetime.now().isoformat()
    })
result["result_generated_at"] = datetime.now().isoformat()

with open(os.path.join(output_path, "altitude_specific_wind_statistics_result.json"), "w") as f:
    json.dump(result, f, indent=4)