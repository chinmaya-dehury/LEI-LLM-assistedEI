"""
Task: soil_moisture_threshold_analysis
Description: Determine optimal soil moisture thresholds for different crops at various growth stages for precise irrigation targets
"""

import os
import json
import pandas as pd
from datetime import datetime

data_path = os.path.join('data', 'soil', 'raw_data.csv')
output_path = os.path.join('output', 'soil', 'soil_moisture_threshold_analysis_result.json')

def analyze_soil_moisture_thresholds():
    try:
        # Read dataset
        df = pd.read_csv(data_path)
        
        # Calculate average soil moisture at different depths
        avg_moisture_0_to_1cm = df['soil_moisture_0_to_1cm'].mean()
        avg_moisture_1_to_3cm = df['soil_moisture_1_to_3cm'].mean()
        avg_moisture_9_to_27cm = df['soil_moisture_9_to_27cm'].mean()
        
        # Determine optimal soil moisture thresholds
        optimal_thresholds = {
            '0-1cm': avg_moisture_0_to_1cm,
            '1-3cm': avg_moisture_1_to_3cm,
            '9-27cm': avg_moisture_9_to_27cm
        }
        
        # Save results to JSON file
        result = {
            'task_name': 'soil_moisture_threshold_analysis',
            'description': 'Determine optimal soil moisture thresholds for different crops at various growth stages for precise irrigation targets',
            'result_summary': [optimal_thresholds],
            'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(output_path, 'w') as f:
            json.dump(result, f)
        
        print('Soil moisture threshold analysis completed. Results saved to:', output_path)
    except Exception as e:
        print('Error occurred during soil moisture threshold analysis:', str(e))

class SoilMoistureThresholdAnalysis:
    def __init__(self):
        pass
    def run(self):
        analyze_soil_moisture_thresholds()

if __name__ == '__main__':
    analysis = SoilMoistureThresholdAnalysis()
    analysis.run()