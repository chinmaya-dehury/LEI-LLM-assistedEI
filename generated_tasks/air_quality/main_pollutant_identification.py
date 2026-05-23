import pandas as pd
import os

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

pollutants = ["co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]

main_pollutant = df[pollutants].mean().idxmax()

main_pollutant_concentration = df[main_pollutant].mean()

import json
from datetime import datetime

result = {
    "task_name": "main_pollutant_identification",
    "description": "Identify the main pollutant contributing to poor air quality and determine its concentration level.",
    "result_summary": [
        {
            "name": "Main Pollutant",
            "value": main_pollutant,
            "description": "The main pollutant contributing to poor air quality.",
            "timestamp": datetime.now().isoformat()
        },
        {
            "name": "Main Pollutant Concentration",
            "value": main_pollutant_concentration,
            "description": "The concentration level of the main pollutant.",
            "timestamp": datetime.now().isoformat()
        }
    ],
    "result_generated_at": datetime.now().isoformat()
}

output_path = os.path.join("output", "air_quality", "main_pollutant_identification_result.json")

with open(output_path, "w") as f:
    json.dump(result, f, indent=4)

print("Main pollutant: ", main_pollutant)
print("Main pollutant concentration: ", main_pollutant_concentration)