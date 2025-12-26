import os
import json
import sys
import pandas as pd
from datetime import datetime

TASK_NAME = "main_pollutant_identification"
DESCRIPTION = "Identify the dominant pollutant contributing to poor air quality by finding which component has the highest concentration relative to its typical background levels."
DATA_TYPE = "air_quality"

def main():
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_dir = os.path.join("output", DATA_TYPE)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found: {data_path}")
            
        df = pd.read_csv(data_path)
        
        if df.empty:
            raise ValueError("Data file is empty")
        
        # Convert timestamp columns to datetime to ensure proper handling
        if 'timestamp_utc' in df.columns:
            df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
        
        # Define pollutant columns
        pollutant_cols = ['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']
        available_cols = [c for c in pollutant_cols if c in df.columns]
        
        if not available_cols:
            raise ValueError("No pollutant columns found in data.")
        
        # Coerce numeric values
        for col in available_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows with NaN in pollutant columns
        df = df.dropna(subset=available_cols)
        
        if df.empty:
            raise ValueError("No valid data after cleaning")
        
        # Calculate baseline (mean of the sample)
        baseline = df[available_cols].mean()
        
        # Calculate relative increase (Current / Baseline) for the latest reading
        latest_reading = df.iloc[-1][available_cols]
        relative_concentration = latest_reading / baseline
        
        # Identify the pollutant with the highest relative concentration
        dominant_pollutant = relative_concentration.idxmax()
        dominant_value = latest_reading[dominant_pollutant]
        relative_score = relative_concentration[dominant_pollutant]
        
        # Generate result summary
        result = {
            "task_name": TASK_NAME,
            "description": DESCRIPTION,
            "result_summary": [
                {
                    "name": "Dominant Pollutant",
                    "value": dominant_pollutant.upper(),
                    "description": f"Pollutant with highest relative concentration (Score: {relative_score:.2f})",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "name": "Concentration",
                    "value": float(dominant_value),
                    "description": f"Latest concentration of {dominant_pollutant} in µg/m3",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "result_generated_at": datetime.now().isoformat()
        }
        
        # Save result to JSON
        output_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
            
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        error_result = {
            "task_name": TASK_NAME,
            "description": DESCRIPTION,
            "result_summary": [],
            "error": str(e),
            "result_generated_at": datetime.now().isoformat()
        }
        output_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
        with open(output_path, 'w') as f:
            json.dump(error_result, f, indent=2)
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()