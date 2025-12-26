import os
import json
import sys
import pandas as pd
from datetime import datetime

TASK_NAME = "source_inference_analysis"
DESCRIPTION = "Analyze pollutant patterns to infer likely sources (traffic, industry, agriculture, or mixed) based on ratios like NO2/SO2 and specific pollutant dominance."
DATA_TYPE = "air_quality"

def main():
    # Define paths
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_dir = os.path.join("output", DATA_TYPE)
    os.makedirs(output_dir, exist_ok=True)
    result_file = os.path.join(output_dir, f"{TASK_NAME}_result.json")

    try:
        # Load data
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at {data_path}")
        
        df = pd.read_csv(data_path)
        
        if df.empty:
            raise ValueError("No data found")
        
        # Ensure numeric types for pollutants
        cols_to_numeric = ['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']
        for col in cols_to_numeric:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows with missing critical values
        # Note: Original code dropped based on 'no2', 'so2', 'pm2_5', 'pm10', 'nh3'
        critical_cols = ['no2', 'so2', 'pm2_5', 'pm10', 'nh3']
        df = df.dropna(subset=[col for col in critical_cols if col in df.columns])
        
        if df.empty:
            raise ValueError("No valid data after cleaning")

        # Calculate averages
        avg = df[cols_to_numeric].mean()
        
        # 1. Traffic vs Industry Ratio (NO2/SO2)
        no2_val = avg.get('no2', 0)
        so2_val = avg.get('so2', 0)
        no2_so2_ratio = no2_val / so2_val if so2_val > 0 else float('inf')
        
        # 2. Agricultural Indicator (NH3)
        nh3_val = avg.get('nh3', 0)
        nh3_dominance = nh3_val > 5.0
        
        # 3. Particulate Matter Dominance
        pm2_5_val = avg.get('pm2_5', 0)
        pm10_val = avg.get('pm10', 0)
        pm_ratio = pm2_5_val / pm10_val if pm10_val > 0 else 0
        
        # Inference Logic
        sources = []
        
        if no2_so2_ratio > 1.5:
            sources.append("Traffic (High NO2/SO2 ratio)")
        elif no2_so2_ratio < 0.5:
            sources.append("Industry (High SO2)")
        else:
            sources.append("Mixed Traffic/Industry")
            
        if nh3_dominance:
            sources.append("Agriculture (High NH3)")
            
        if pm_ratio > 0.7:
            sources.append("Combustion/Fine Particles (High PM2.5)")
        elif pm_ratio < 0.4:
            sources.append("Road Dust/Construction (High PM10)")

        if not sources:
            sources.append("Unknown/Mixed")

        # Prepare Result
        timestamp = datetime.now().isoformat()
        
        result = {
            "task_name": TASK_NAME,
            "description": DESCRIPTION,
            "result_summary": [
                {
                    "name": "NO2/SO2 Ratio",
                    "value": round(float(no2_so2_ratio), 2),
                    "description": "Ratio > 1.5 suggests Traffic, < 0.5 suggests Industry",
                    "timestamp": timestamp
                },
                {
                    "name": "NH3 Dominance",
                    "value": bool(nh3_dominance),
                    "description": "True if NH3 > 5.0 (Agriculture indicator)",
                    "timestamp": timestamp
                },
                {
                    "name": "PM2.5/PM10 Ratio",
                    "value": round(float(pm_ratio), 2),
                    "description": "Ratio > 0.7 suggests fine particles (combustion), < 0.4 suggests coarse (dust)",
                    "timestamp": timestamp
                },
                {
                    "name": "Inferred Sources",
                    "value": ", ".join(sources),
                    "description": "Likely pollution sources based on analysis",
                    "timestamp": timestamp
                }
            ],
            "result_generated_at": timestamp
        }

        # Save to JSON and print
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
            
        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        error_result = {
            "task_name": TASK_NAME,
            "description": DESCRIPTION,
            "result_summary": [],
            "result_generated_at": datetime.now().isoformat(),
            "error": str(e)
        }
        with open(result_file, 'w') as f:
            json.dump(error_result, f, indent=2)
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()