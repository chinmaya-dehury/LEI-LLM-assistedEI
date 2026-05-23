import pandas as pd
import os
import json
from datetime import datetime

TASK_NAME = "weather_condition_analysis"
DESCRIPTION = "Analyze the impact of weather conditions on air quality"
DATA_TYPE = "air_quality"


def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(json.dumps({"task_name": TASK_NAME, "error": "File not found"}))
        sys.exit(1)
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
    df.set_index('timestamp_utc', inplace=True)
    # Calculate daily averages for each pollutant
    pollutant_averages = df[['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']].resample('D').mean()
    # Convert pandas DataFrame to dictionary with string keys
    pollutant_averages_dict = pollutant_averages.to_dict(orient='index')
    # Convert datetime keys to string
    pollutant_averages_dict = {k.strftime('%Y-%m-%d'): v for k, v in pollutant_averages_dict.items()}
    # Print the results
    print(pollutant_averages)
    # Save the results to a JSON file
    result_summary = [
        {
            'name': 'Daily Average Pollutant Levels',
            'value': pollutant_averages_dict,
            'description': 'Daily average levels of each pollutant',
            'timestamp': datetime.now().isoformat()
        }
    ]
    result = {
        'task_name': TASK_NAME,
        'description': DESCRIPTION,
        'result_summary': result_summary,
        'result_generated_at': datetime.now().isoformat()
    }
    print(json.dumps(result))
    output_path = os.path.join("output", DATA_TYPE, "weather_condition_analysis_result.json")
    with open(output_path, 'w') as f:
        json.dump(result, f)
    sys.exit(0)

if __name__ == '__main__':
    import sys
    main()