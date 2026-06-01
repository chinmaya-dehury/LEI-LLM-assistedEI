"""
Task: Sensor Battery Health Monitoring
Description: Monitor sensor battery health by analyzing voltage readings and their correlation with temperature.
"""

import csv
import json
import os
import pathlib
import statistics

def analyze_battery_health(data_file):
    voltage_readings = []
    temperature_readings = []
    with open(data_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                voltage_readings.append(float(row['voltage']))
                temperature_readings.append(float(row['temperature']))
            except ValueError:
                pass
    avg_voltage = statistics.mean(voltage_readings)
    std_dev_voltage = statistics.stdev(voltage_readings)
    result = {
        'avg_voltage': avg_voltage,
        'std_dev_voltage': std_dev_voltage
    }
    return result

def main():
    data_dir = pathlib.Path('data/Lab-Data')
    data_file = os.path.join(data_dir, 'raw_data.csv')
    result = analyze_battery_health(data_file)
    output_dir = pathlib.Path('output/Lab-Data')
    output_file = os.path.join(output_dir, 'Sensor_Battery_Health_Monitoring_result.json')
    with open(output_file, 'w') as file:
        json.dump({
            'task_name': 'Sensor Battery Health Monitoring',
            'description': 'Monitor sensor battery health by analyzing voltage readings and their correlation with temperature.',
            'result_summary': [result],
            'result_generated_at': '2023-12-01'
        }, file)

if __name__ == '__main__':
    main()