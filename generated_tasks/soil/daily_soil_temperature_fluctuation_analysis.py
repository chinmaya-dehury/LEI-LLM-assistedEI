"""
Task: daily_soil_temperature_fluctuation_analysis
Description: Analyze daily fluctuations in soil temperature at different depths for insights into soil thermal dynamics
"""

import os
import json
import pandas as pd
from datetime import datetime

data_path = os.path.join('data', 'soil', 'raw_data.csv')
output_path = os.path.join('output', 'soil', 'daily_soil_temperature_fluctuation_analysis_result.json')

def analyze_soil_temperature_fluctuation():
    try:
        # Read dataset
        df = pd.read_csv(data_path)
        
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Extract daily temperature fluctuations
        daily_fluctuations = {}
        for column in ['soil_temperature_0cm', 'soil_temperature_6cm', 'soil_temperature_18cm', 'soil_temperature_54cm']:
            daily_fluctuations[column] = df.groupby(df['date'].dt.date)[column].max() - df.groupby(df['date'].dt.date)[column].min()
        
        # Create result summary
        result_summary = []
        for column, fluctuations in daily_fluctuations.items():
            result_summary.append({'depth': column, 'fluctuation': fluctuations.mean()})
        
        # Create result dictionary
        result = {
            'task_name': 'daily_soil_temperature_fluctuation_analysis',
            'description': 'Analyze daily fluctuations in soil temperature at different depths for insights into soil thermal dynamics',
            'result_summary': result_summary,
            'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save result to JSON file
        with open(output_path, 'w') as f:
            json.dump(result, f)
        
        return result
    except Exception as e:
        print(f'Error: {str(e)}')
        return None

# Execute task
result = analyze_soil_temperature_fluctuation()
if result:
    print('Result saved to', output_path)