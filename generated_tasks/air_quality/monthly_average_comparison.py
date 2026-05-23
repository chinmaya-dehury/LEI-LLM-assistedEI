import pandas as pd
import os
import json
from datetime import datetime

TASK_NAME = "monthly_average_comparison"
DESCRIPTION = "Compare the monthly average concentrations of different pollutants to identify seasonal patterns and trends, and determine if there are any significant changes over time."
DATA_TYPE = "air_quality"
pollutants = ['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']


def calculate_monthly_average(df, pollutant):
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
    df['month'] = df['timestamp_utc'].dt.to_period('M').apply(lambda x: x.strftime('%Y-%m'))
    monthly_avg = df.groupby('month')[pollutant].mean().reset_index()
    return monthly_avg


def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    try:
        raw_data = pd.read_csv(data_path)
    except FileNotFoundError:
        print(json.dumps({"task_name": TASK_NAME, "error": "File not found"}))
        sys.exit(1)
    # Calculate monthly average for each pollutant
    monthly_avgs = {}
    for pollutant in pollutants:
        monthly_avg = calculate_monthly_average(raw_data, pollutant)
        monthly_avgs[pollutant] = monthly_avg
    # Save results to JSON file
    result_summary = []
    for pollutant, monthly_avg in monthly_avgs.items():
        result = {
            'name': f'{pollutant} monthly average',
            'value': monthly_avg.to_dict(orient='records'),
            'description': f'Monthly average concentration of {pollutant}',
            'timestamp': datetime.now().isoformat()
        }
        result_summary.append(result)
    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': result_summary,
        'result_generated_at': datetime.now().isoformat()
    }
    print(json.dumps(result))
    output_path = os.path.join('output', DATA_TYPE, 'monthly_average_comparison_result.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=4)
    sys.exit(0)

if __name__ == '__main__':
    import sys
    main()