"""
Task: soil_temperature_stratification
Description: Analyze the soil temperature stratification and thermal profile dynamics for drought detection and root zone assessment
"""

import os
import json
from datetime import datetime
import pandas as pd

data_path = os.path.join('data', 'soil', 'raw_data.csv')
output_path = os.path.join('output', 'soil', 'soil_temperature_stratification_result.json')

def analyze_soil_temperature_stratification():
    try:
        # Read dataset
        df = pd.read_csv(data_path)
        
        # Calculate temperature differences between depth levels
        df['temp_diff_0cm_6cm'] = df['soil_temperature_6cm'] - df['soil_temperature_0cm']
        df['temp_diff_6cm_18cm'] = df['soil_temperature_18cm'] - df['soil_temperature_6cm']
        df['temp_diff_18cm_54cm'] = df['soil_temperature_54cm'] - df['soil_temperature_18cm']
        
        # Calculate average temperature differences
        avg_temp_diff_0cm_6cm = df['temp_diff_0cm_6cm'].mean()
        avg_temp_diff_6cm_18cm = df['temp_diff_6cm_18cm'].mean()
        avg_temp_diff_18cm_54cm = df['temp_diff_18cm_54cm'].mean()
        
        # Create result dictionary
        result = {
            'task_name': 'soil_temperature_stratification',
            'description': 'Analyze the soil temperature stratification and thermal profile dynamics for drought detection and root zone assessment',
            'result_summary': [
                {'depth': '0cm-6cm', 'avg_temp_diff': avg_temp_diff_0cm_6cm},
                {'depth': '6cm-18cm', 'avg_temp_diff': avg_temp_diff_6cm_18cm},
                {'depth': '18cm-54cm', 'avg_temp_diff': avg_temp_diff_18cm_54cm}
            ],
            'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save result to JSON file
        with open(output_path, 'w') as f:
            json.dump(result, f)
        
        print('Soil temperature stratification analysis completed.')
    except Exception as e:
        print(f'Error: {str(e)}')

analyze_soil_temperature_stratification()