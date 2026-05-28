"""
Task: Dew_Point_Benchmarking
Description: Compares dew point temperatures against benchmarks for moisture and condensation risk assessment
"""

import pandas as pd
import numpy as np

def dew_point_benchmarking(data):
    # Calculate dew point temperature
    dew_point = pd.to_numeric(data['temperature_c']) - ((100 - pd.to_numeric(data['humidity_percent'])) / 5)
    # Define benchmark thresholds
    benchmark_high = 25
    benchmark_low = 15
    # Compare dew point temperatures against benchmarks
    result = []
    for i in range(len(dew_point)):
        if dew_point[i] > benchmark_high:
            result.append({'dew_point': dew_point[i], 'benchmark': benchmark_high, 'status': 'High Risk'})
        elif dew_point[i] < benchmark_low:
            result.append({'dew_point': dew_point[i], 'benchmark': benchmark_low, 'status': 'Low Risk'})
        else:
            result.append({'dew_point': dew_point[i], 'benchmark': benchmark_low, 'status': 'Normal'})
    return result

def main():
    # Load data
    data = pd.read_csv('data/temp_humidity/raw_data.csv')
    # Execute task
    result = dew_point_benchmarking(data)
    # Save result
    with open('output/temp_humidity/Dew_Point_Benchmarking_result.json', 'w') as f:
        import json
        json.dump({'task_name': 'Dew_Point_Benchmarking', 'description': 'Compares dew point temperatures against benchmarks for moisture and condensation risk assessment', 'result_summary': result, 'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f)

if __name__ == '__main__':
    main()