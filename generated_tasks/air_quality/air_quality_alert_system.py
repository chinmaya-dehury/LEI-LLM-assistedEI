import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

TASK_NAME = "air_quality_alert_system"
DESCRIPTION = "Develop an alert system to notify citizens when the air quality exceeds a certain threshold, providing them with valuable insights and recommendations."
DATA_TYPE = "air_quality"


def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    try:
        air_quality_data = pd.read_csv(data_path)
    except FileNotFoundError:
        print(json.dumps({"task_name": TASK_NAME, "error": "File not found"}))
        sys.exit(1)

    # Define AQI thresholds
    aqi_thresholds = {
        'Good': (0, 50),
        'Moderate': (51, 100),
        'Unhealthy for sensitive groups': (101, 150),
        'Unhealthy': (151, 200),
        'Very unhealthy': (201, 300),
        'Hazardous': (301, 500)
    }

    # Calculate AQI
    air_quality_data['aqi'] = np.where((air_quality_data['pm2_5'] <= 12),
                                        np.where((air_quality_data['pm2_5'] > 0),
                                                 (air_quality_data['pm2_5'] / 12) * 50,
                                                 0),
                                        np.where((air_quality_data['pm2_5'] <= 35.4),
                                                 ((air_quality_data['pm2_5'] - 12) / (35.4 - 12)) * (100 - 50) + 50,
                                                 np.where((air_quality_data['pm2_5'] <= 55.4),
                                                          ((air_quality_data['pm2_5'] - 35.4) / (55.4 - 35.4)) * (150 - 100) + 100,
                                                          np.where((air_quality_data['pm2_5'] <= 150.4),
                                                                   ((air_quality_data['pm2_5'] - 55.4) / (150.4 - 55.4)) * (200 - 150) + 150,
                                                                   np.where((air_quality_data['pm2_5'] <= 250.4),
                                                                            ((air_quality_data['pm2_5'] - 150.4) / (250.4 - 150.4)) * (300 - 200) + 200,
                                                                            np.where((air_quality_data['pm2_5'] <= 500.4),
                                                                                     ((air_quality_data['pm2_5'] - 250.4) / (500.4 - 250.4)) * (500 - 300) + 300,
                                                                                     500))))))

    # Define alert system
    def send_alert(aqi_value, aqi_category):
        print(f'AQI: {aqi_value}, Category: {aqi_category}')
        # Add notification logic here

    # Check AQI and send alerts
    result_summary = []
    for index, row in air_quality_data.iterrows():
        aqi_value = row['aqi']
        for category, threshold in aqi_thresholds.items():
            if threshold[0] <= aqi_value <= threshold[1]:
                send_alert(aqi_value, category)
                result_summary.append({
                    'name': 'AQI Alert',
                    'value': aqi_value,
                    'description': category,
                    'timestamp': datetime.now().isoformat()
                })
                break

    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': result_summary,
        'result_generated_at': datetime.now().isoformat()
    }
    print(json.dumps(result))
    with open(os.path.join('output', DATA_TYPE, TASK_NAME + '_result.json'), 'w') as f:
        json.dump(result, f)
    sys.exit(0)

if __name__ == '__main__':
    import sys
    main()