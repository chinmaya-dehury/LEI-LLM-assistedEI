"""
Task: Temperature-Humidity Correlation Analysis per Mote
Description: Analyze the correlation between temperature and humidity readings for each individual mote to identify patterns and potential issues with sensor calibration.
"""

import csv
import os
import json
from pathlib import Path
import numpy as np
from scipy.stats import pearsonr

def analyze_temperature_humidity_correlation(data_path, mote_id):
    temperature_values = []
    humidity_values = []
    with open(data_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if int(row['moteid']) == mote_id:
                temperature_values.append(float(row['temperature']))
                humidity_values.append(float(row['humidity']))
    if len(temperature_values) > 0 and len(humidity_values) > 0:
        correlation_coefficient, _ = pearsonr(temperature_values, humidity_values)
        return correlation_coefficient
    else:
        return None

def main():
    data_path = os.path.join('data', 'Lab-Data', 'raw_data.csv')
    mote_ids = range(1, 55)  # Assuming 54 motes
    results = {}
    for mote_id in mote_ids:
        correlation_coefficient = analyze_temperature_humidity_correlation(data_path, mote_id)
        if correlation_coefficient is not None:
            results[mote_id] = correlation_coefficient
    output_path = os.path.join('output', 'Lab-Data', 'Temperature_Humidity_Correlation_Result.json')
    output_dir = Path(output_path).parent
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump({'mote_correlations': results}, f)
if __name__ == '__main__':
    main()