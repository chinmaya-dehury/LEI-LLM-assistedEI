"""
Task: Detect Concept Drift
Description: Implement a simple drift detection algorithm to identify changes in sensor responses over time, potentially indicating concept drift or sensor degradation.
"""

import pandas as pd
import numpy as np
import os
import json
from pathlib import Path

def detect_concept_drift(data_path):
    # Load data
    file_path = os.path.join(data_path, 'raw_data.csv')
    data = pd.read_csv(file_path)
    
    # Select sensor response columns
    sensor_columns = ['PT08.S1(CO)', 'PT08.S2(NMHC)', 'PT08.S3(NOx)', 'PT08.S4(NO2)', 'PT08.S5(O3)']
    data_sensor = data[sensor_columns]
    
    # Calculate mean and standard deviation for each sensor over time
    mean_values = data_sensor.mean()
    std_values = data_sensor.std()
    
    # Simple drift detection: check for values more than 2 standard deviations away from mean
    drift_indices = data_sensor[(np.abs(data_sensor - mean_values) > 2 * std_values).any(axis=1)].index
    
    # Save results
    result = {
      "task_name": "Detect Concept Drift",
      "description": "Detected concept drift in sensor responses",
      "result_summary": list(drift_indices),
      "result_generated_at": "2023-12-01"
    }
    output_path = os.path.join('output', 'air_quality', 'Detect_Concept_Drift_result.json')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
      json.dump(result, f)
    return result

if __name__ == '__main__':
    data_path = 'data/air_quality'
    detect_concept_drift(data_path)