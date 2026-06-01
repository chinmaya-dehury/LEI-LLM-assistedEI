"""
Task: Voltage Anomaly Detection
Description: Detect anomalies in voltage readings from sensor motes to identify potential battery health issues.
"""

import csv
import json
import os
from pathlib import Path
import statistics

def detect_voltage_anomalies(file_path, threshold=3):
    voltage_readings = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                voltage = float(row['voltage'])
                voltage_readings.append(voltage)
            except ValueError:
                pass

    if not voltage_readings:
        return []

    mean = statistics.mean(voltage_readings)
    stdev = statistics.stdev(voltage_readings) if len(voltage_readings) > 1 else 0

    anomalies = []
    for i, reading in enumerate(voltage_readings):
        z_score = (reading - mean) / stdev if stdev != 0 else 0
        if abs(z_score) > threshold:
            anomalies.append({'index': i, 'reading': reading})

    return anomalies

def main():
    data_type = 'Lab-Data'
    file_path = os.path.join('data', data_type, 'raw_data.csv')
    anomalies = detect_voltage_anomalies(file_path)

    result = {
        'task_name': 'Voltage Anomaly Detection',
        'description': 'Detect anomalies in voltage readings from sensor motes to identify potential battery health issues.',
        'result_summary': anomalies,
        'result_generated_at': ''
    }

    output_path = os.path.join('output', data_type, 'Voltage_Anomaly_Detection_result.json')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f)

if __name__ == '__main__':
    main()