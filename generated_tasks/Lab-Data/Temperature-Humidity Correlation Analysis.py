"""
Task: Temperature-Humidity Correlation Analysis
Description: Analyze the correlation between temperature and humidity readings across different motes and time periods to identify patterns and potential issues with sensor calibration.
"""

import csv
import os
import json
from pathlib import Path
import statistics

def analyze_correlation(data_path):
    temperature_values = []
    humidity_values = []
    with open(data_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                temperature_values.append(float(row['temperature']))
                humidity_values.append(float(row['humidity']))
            except ValueError:
                pass
    if not temperature_values or not humidity_values:
        return None
    temperature_mean = statistics.mean(temperature_values)
    humidity_mean = statistics.mean(humidity_values)
    covariance = sum((float(x) - temperature_mean) * (float(y) - humidity_mean) for x, y in zip(temperature_values, humidity_values)) / len(temperature_values)
    temperature_std_dev = statistics.stdev(temperature_values) if len(temperature_values) > 1 else 0
    humidity_std_dev = statistics.stdev(humidity_values) if len(humidity_values) > 1 else 0
    if temperature_std_dev == 0 or humidity_std_dev == 0:
        correlation_coefficient = 0
    else:
        correlation_coefficient = covariance / (temperature_std_dev * humidity_std_dev)
    return correlation_coefficient

def main():
    data_type = 'Lab-Data'
    data_path = os.path.join('data', data_type, 'raw_data.csv')
    result = analyze_correlation(data_path)
    if result is not None:
        task_name = 'Temperature-Humidity Correlation Analysis'
        description = 'Analyzed correlation between temperature and humidity'
        result_summary = [f'Correlation Coefficient: {result}']
        output_path = os.path.join('output', data_type, f'{task_name}_result.json')
        with open(output_path, 'w') as output_file:
            json.dump({
                'task_name': task_name,
                'description': description,
                'result_summary': result_summary,
                'result_generated_at': '2023-01-01'
            }, output_file)
if __name__ == '__main__':
    main()