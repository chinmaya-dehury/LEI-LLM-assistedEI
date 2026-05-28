"""
Task: root_zone_moisture_balance
Description: Analyze the balance between soil moisture and temperature in the root zone for insights into root health and function
"""

import os
import json
import pandas as pd
from datetime import datetime

data_path = os.path.join('data', 'soil', 'raw_data.csv')
output_path = os.path.join('output', 'soil', 'root_zone_moisture_balance_result.json')

def analyze_root_zone_moisture_balance():
    try:
        # Read dataset
        df = pd.read_csv(data_path)
        
        # Calculate average soil moisture and temperature in the root zone
        df['soil_moisture_root_zone'] = (df['soil_moisture_0_to_1cm'] + df['soil_moisture_1_to_3cm']) / 2
        df['soil_temperature_root_zone'] = (df['soil_temperature_0cm'] + df['soil_temperature_6cm']) / 2
        
        # Calculate balance between soil moisture and temperature in the root zone
        df['root_zone_moisture_balance'] = df['soil_moisture_root_zone'] / df['soil_temperature_root_zone']
        
        # Generate result summary
        result_summary = df['root_zone_moisture_balance'].describe().to_dict()
        
        # Save result to JSON file
        result = {
            'task_name': 'root_zone_moisture_balance',
            'description': 'Analyze the balance between soil moisture and temperature in the root zone for insights into root health and function',
            'result_summary': result_summary,
            'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(output_path, 'w') as f:
            json.dump(result, f)
        
        print('Result saved to:', output_path)
    except Exception as e:
        print('Error:', str(e))

analyze_root_zone_moisture_balance()