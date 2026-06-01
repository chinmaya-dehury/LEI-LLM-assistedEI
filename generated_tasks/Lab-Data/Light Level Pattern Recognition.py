"""
Task: Light Level Pattern Recognition
Description: Recognize patterns in light level readings to detect anomalies and potential issues with sensor calibration.
"""

import csv
import json
import os
from pathlib import Path

def light_level_pattern_recognition(data_path):
    data = []
    with open(data_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                light = float(row['light'])
                if light < 0:
                    continue
                data.append(light)
            except (ValueError, KeyError):
                continue
    if not data:
        return []
    mean_light = sum(data) / len(data)
    std_dev = (sum((x - mean_light) ** 2 for x in data) / len(data)) ** 0.5
    anomalies = [x for x in data if abs(x - mean_light) > 2 * std_dev]
    result = {
        "task_name": "Light Level Pattern Recognition",
        "description": "Recognize patterns in light level readings to detect anomalies and potential issues with sensor calibration.",
        "result_summary": ["Mean light level: {:.2f}".format(mean_light), "Standard deviation: {:.2f}".format(std_dev), "Anomalies: {}".format(len(anomalies))],
        "result_generated_at": "{}".format(datetime.datetime.now())
    }
    return result

if __name__ == '__main__':
    data_path = os.path.join('data', 'Lab-Data', 'raw_data.csv')
    result = light_level_pattern_recognition(data_path)
    output_path = os.path.join('output', 'Lab-Data', 'Light Level Pattern Recognition_result.json')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f)