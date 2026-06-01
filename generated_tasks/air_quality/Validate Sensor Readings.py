"""
Task: Validate Sensor Readings
Description: Compare sensor readings (PT08.S1(CO), PT08.S2(NMHC), PT08.S3(NOx), PT08.S4(NO2), PT08.S5(O3)) with corresponding ground truth values (CO(GT), NMHC(GT), C6H6(GT), NOx(GT), NO2(GT)) to evaluate sensor accuracy.
"""

import csv
import json
import os
from datetime import datetime

def validate_sensor_readings(data_type):
    file_path = os.path.join('data', data_type, 'raw_data.csv')
    results = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                co_gt = float(row['CO(GT)'])
                nmhc_gt = float(row['NMHC(GT)'])
                c6h6_gt = float(row['C6H6(GT)'])
                nox_gt = float(row['NOx(GT)'])
                no2_gt = float(row['NO2(GT)'])
                pt08_s1_co = float(row['PT08.S1(CO)'])
                pt08_s2_nmhc = float(row['PT08.S2(NMHC)'])
                pt08_s3_nox = float(row['PT08.S3(NOx)'])
                pt08_s4_no2 = float(row['PT08.S4(NO2)'])
                results.append({
                    'CO_GT': co_gt,
                    'PT08_S1_CO': pt08_s1_co,
                    'NMHC_GT': nmhc_gt,
                    'PT08_S2_NMHC': pt08_s2_nmhc,
                    'C6H6_GT': c6h6_gt,
                    'NOx_GT': nox_gt,
                    'PT08_S3_NOx': pt08_s3_nox,
                    'NO2_GT': no2_gt,
                    'PT08_S4_NO2': pt08_s4_no2
                })
            except (KeyError, ValueError) as e:
                print(f"Error processing row: {e}")
    output_path = os.path.join('output', data_type, 'validate_sensor_readings_result.json')
    with open(output_path, 'w') as output_file:
        json.dump({
            'task_name': 'Validate Sensor Readings',
            'description': 'Compare sensor readings with corresponding ground truth values.',
            'result_summary': results,
            'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, output_file)

validate_sensor_readings('air_quality')