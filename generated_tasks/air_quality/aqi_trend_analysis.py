import os
import json
import sys
import pandas as pd
from datetime import datetime

TASK_NAME = "aqi_trend_analysis"
DESCRIPTION = "Calculate daily AQI trends and classify air quality"
DATA_TYPE = "air_quality"

AQI_THRESHOLDS = {
    "Good": (0, 50),
    "Moderate": (51, 100),
    "Unhealthy": (101, 150),
    "Very Unhealthy": (151, 200),
    "Severe": (201, 1000)
}

def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_dir = os.path.join("output", DATA_TYPE)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")

    try:
        df = pd.read_csv(data_path)
        df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
        df = df.dropna(subset=['timestamp_utc'])
        df.set_index('timestamp_utc', inplace=True)
        df = df.resample('D').mean()
        
        results = []
        for idx, row in df.iterrows():
            aqi = pd.to_numeric(row['aqi_uk'], errors='coerce')
            if pd.isna(aqi):
                continue
            
            for category, (low, high) in AQI_THRESHOLDS.items():
                if low <= aqi <= high:
                    results.append({
                        "date": idx.strftime('%Y-%m-%d'),
                        "average_aqi": round(aqi, 2),
                        "category": category
                    })
                    break
        
        result = {
            "task_name": TASK_NAME,
            "description": DESCRIPTION,
            "result_summary": results,
            "result_generated_at": datetime.now().isoformat()
        }
        
        print(json.dumps(result))
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
    except Exception as e:
        error_msg = {
            "error": f"Failed to process data: {str(e)}"
        }
        print(json.dumps(error_msg))
        with open(output_path, 'w') as f:
            json.dump(error_msg, f, indent=2)
        sys.exit(1)

if __name__ == "__main__":
    main()