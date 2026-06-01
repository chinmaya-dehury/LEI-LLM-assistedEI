"""
Task: Estimate CO Concentration
Description: Develop a lightweight model to estimate CO concentration using PT08.S1(CO) sensor readings and compare with CO(GT) ground truth values.
"""

import csv
import json
import os
from pathlib import Path

def estimate_co_concentration(data_path):
    co_gt_values = []
    pt08_s1_co_values = []
    with open(data_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            co_gt_values.append(float(row['CO(GT)']))
            pt08_s1_co_values.append(float(row['PT08.S1(CO)']))
    
    # Simple linear regression for demonstration purposes
    sum_x = sum(pt08_s1_co_values)
    sum_y = sum(co_gt_values)
    sum_xy = sum(x * y for x, y in zip(pt08_s1_co_values, co_gt_values))
    sum_xx = sum(x ** 2 for x in pt08_s1_co_values)
    n = len(pt08_s1_co_values)
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x ** 2)
    intercept = (sum_y - slope * sum_x) / n
    
    estimated_co = [slope * x + intercept for x in pt08_s1_co_values]
    return estimated_co, co_gt_values

def main():
    data_path = os.path.join('data', 'air_quality', 'raw_data.csv')
    estimated_co, co_gt_values = estimate_co_concentration(data_path)
    result = {
        "task_name": "Estimate CO Concentration",
        "description": "Estimation of CO concentration using PT08.S1(CO) sensor readings",
        "result_summary": ["Estimated CO: " + str(estimated_co), "CO Ground Truth: " + str(co_gt_values)],
        "result_generated_at": "2023-01-01"
    }
    output_path = os.path.join('output', 'air_quality', 'Estimate_CO_Concentration_result.json')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f)
if __name__ == '__main__':
    main()