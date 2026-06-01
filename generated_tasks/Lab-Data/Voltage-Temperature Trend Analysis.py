"""
Task: Voltage-Temperature Trend Analysis
Description: Analyze the trend of voltage readings in relation to temperature changes to identify potential battery health issues and sensor calibration problems.
"""

import csv
import json
import os
import pathlib
from datetime import datetime

def voltage_temperature_trend(data_file):
    data_dir = pathlib.Path('data/Lab-Data')
    file_path = data_dir / data_file
    voltage_readings = {}
    temperature_readings = {}
    try:
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                mote_id = row['moteid']
                temperature = float(row['temperature'])
                voltage = float(row['voltage'])
                if mote_id not in voltage_readings:
                    voltage_readings[mote_id] = []
                    temperature_readings[mote_id] = []
                voltage_readings[mote_id].append(voltage)
                temperature_readings[mote_id].append(temperature)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return
    trend_data = []
    for mote_id in voltage_readings:
        avg_voltage = sum(voltage_readings[mote_id]) / len(voltage_readings[mote_id])
        avg_temperature = sum(temperature_readings[mote_id]) / len(temperature_readings[mote_id])
        trend_data.append({
            'mote_id': mote_id,
            'avg_voltage': avg_voltage,
            'avg_temperature': avg_temperature
        })
    output_dir = pathlib.Path('output/Lab-Data')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'voltage_temperature_trend_result.json'
    with open(output_file, 'w') as outfile:
        json.dump({
            'task_name': 'Voltage-Temperature Trend Analysis',
            'description': 'Analyzed the trend of voltage readings in relation to temperature changes.',
            'result_summary': trend_data,
            'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, outfile)
    print(f"Results saved to {output_file}")

if __name__ == '__main__':
    voltage_temperature_trend('raw_data.csv')