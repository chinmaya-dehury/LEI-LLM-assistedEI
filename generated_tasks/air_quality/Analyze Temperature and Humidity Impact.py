"""
Task: Analyze Temperature and Humidity Impact
Description: Investigate how temperature (T) and relative humidity (RH) affect sensor responses, particularly focusing on PT08.S1(CO), PT08.S2(NMHC), PT08.S3(NOx), and PT08.S4(NO2).
"""

import pandas as pd
import os
import json
from pathlib import Path

def analyze_temperature_humidity_impact(data_path):
    try:
        data = pd.read_csv(data_path)
        # Focus on relevant columns
        focused_data = data[['T', 'RH', 'PT08.S1(CO)', 'PT08.S2(NMHC)', 'PT08.S3(NOx)', 'PT08.S4(NO2)']
        # Calculate correlations
        correlations = focused_data.corr()
        return correlations
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def main():
    data_type = 'air_quality'
    raw_data_path = os.path.join('data', data_type, 'raw_data.csv')
    result = analyze_temperature_humidity_impact(raw_data_path)
    if result is not None:
        output_path = Path('output') / data_type / 'Analyze_Temperature_and_Humidity_Impact_result.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump({
                "task_name": "Analyze Temperature and Humidity Impact",
                "description": "Investigate how temperature (T) and relative humidity (RH) affect sensor responses, particularly focusing on PT08.S1(CO), PT08.S2(NMHC), PT08.S3(NOx), and PT08.S4(NO2).",
                "result_summary": result.to_dict().values(),
                "result_generated_at": "2023-04-06"
            }, f, indent=4)
if __name__ == '__main__':
    main()