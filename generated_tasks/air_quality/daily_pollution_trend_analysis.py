import os
import json
import sys
import pandas as pd
from datetime import datetime

# Configuration
TASK_NAME = "daily_pollution_trend_analysis"
DESCRIPTION = "Calculate daily pollution trends by aggregating data into time-of-day periods to identify morning/evening rush hour patterns."
DATA_TYPE = "air_quality"

def main():
    # Path construction
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming execution from root or generated_tasks folder, adapt path relative to script location
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_dir = os.path.join("output", DATA_TYPE)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Load data
        if not os.path.exists(data_path):
            print(json.dumps({"task_name": TASK_NAME, "error": f"Data file not found at {data_path}"}))
            sys.exit(1)

        df = pd.read_csv(data_path)
        
        # Check if required columns exist
        required_cols = ['timestamp_utc', 'aqi_uk', 'pm2_5', 'pm10', 'no2']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(json.dumps({"task_name": TASK_NAME, "error": f"Missing required columns: {missing_cols}"}))
            sys.exit(1)

        # Parse timestamps
        df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
        df = df.dropna(subset=['timestamp_utc'])
        
        if df.empty:
            print(json.dumps({"task_name": TASK_NAME, "error": "No valid timestamp data available."}))
            sys.exit(1)

        df['hour'] = df['timestamp_utc'].dt.hour
        
        # Define time periods
        def get_period(hour):
            if 6 <= hour < 12:
                return 'Morning (6-12)'
            elif 12 <= hour < 18:
                return 'Afternoon (12-18)'
            elif 18 <= hour < 24:
                return 'Evening (18-24)'
            else:
                return 'Night (0-6)'
        
        df['period'] = df['hour'].apply(get_period)
        
        # Aggregate by period
        # Calculate mean of pollutants and AQI, coerce errors to handle non-numeric safely
        agg_cols = ['aqi_uk', 'pm2_5', 'pm10', 'no2']
        for col in agg_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        trends = df.groupby('period')[agg_cols].mean().reset_index()
        
        # Reorder periods for logical flow
        period_order = ['Morning (6-12)', 'Afternoon (12-18)', 'Evening (18-24)', 'Night (0-6)']
        trends['period'] = pd.Categorical(trends['period'], categories=period_order, ordered=True)
        trends = trends.sort_values('period')
        
        # Identify peak pollution period (based on AQI)
        if not trends.empty:
            # Drop rows where AQI is NaN before finding max
            valid_trends = trends.dropna(subset=['aqi_uk'])
            if not valid_trends.empty:
                peak_row = valid_trends.loc[valid_trends['aqi_uk'].idxmax()]
                peak_period = str(peak_row['period'])
                peak_aqi = float(round(peak_row['aqi_uk'], 2))
            else:
                peak_period = "N/A"
                peak_aqi = 0.0
        else:
            peak_period = "N/A"
            peak_aqi = 0.0

        # Prepare JSON Result
        result = {
            "task_name": TASK_NAME,
            "description": DESCRIPTION,
            "result_summary": [
                {
                    "name": "Peak Pollution Period",
                    "value": peak_period,
                    "description": "Time of day with the highest average AQI.",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "name": "Peak AQI Value",
                    "value": peak_aqi,
                    "description": "The average AQI value recorded during the peak period.",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "name": "Trend Data",
                    "value": trends.to_dict(orient='records'),
                    "description": "Aggregated average values for each time period.",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "result_generated_at": datetime.now().isoformat()
        }

        # Output to stdout
        print(json.dumps(result))

        # Save JSON Result to file
        json_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        sys.exit(0)

    except Exception as e:
        error_result = {
            "task_name": TASK_NAME,
            "error": str(e),
            "traceback": sys.exc_info()}
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()