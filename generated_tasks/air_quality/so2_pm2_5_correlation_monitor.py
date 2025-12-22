import os
import json
import sys
import pandas as pd
from datetime import datetime

TASK_NAME = "so2_pm2_5_correlation_monitor"
DESCRIPTION = "Monitor SO2 and PM2.5 correlation to detect industrial vs. traffic pollution sources."
DATA_TYPE = "air_quality"

def main():
    # Construct data path using absolute path relative to script location or current directory
    # We try to locate the 'data' directory relative to the current working directory
    # Since the original error showed a path attempt, we ensure robustness.
    data_path = os.path.join("data", DATA_TYPE, "raw_data.csv")
    output_dir = os.path.join("output", DATA_TYPE)
    
    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [],
        "result_generated_at": datetime.now().isoformat()
    }
    
    try:
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at expected path: {data_path}")
            
        df = pd.read_csv(data_path)
        
        if df.empty:
            raise ValueError("Data file is empty")

        # Ensure required columns exist
        required_cols = ['so2', 'pm2_5']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise KeyError(f"Missing required columns: {missing_cols}")

        # Data cleaning: Coerce numeric columns
        df['so2'] = pd.to_numeric(df['so2'], errors='coerce')
        df['pm2_5'] = pd.to_numeric(df['pm2_5'], errors='coerce')
        
        # Drop rows where critical data is missing
        df = df.dropna(subset=['so2', 'pm2_5'])
        
        if df.empty:
            raise ValueError("No valid data remaining after cleaning")

        # Calculate correlation
        correlation = df['so2'].corr(df['pm2_5'])
        
        # Calculate ratio (SO2 / PM2.5)
        # Use numpy for vectorized division to handle zeros safely
        import numpy as np
        df['ratio'] = np.where(df['pm2_5'] > 0, df['so2'] / df['pm2_5'], 0)
        avg_ratio = df['ratio'].mean()
        
        # Interpretation logic
        if pd.isna(correlation):
            source_inference = "Correlation undefined (insufficient valid data)."
        elif correlation > 0.7:
            source_inference = "Strong correlation detected. Likely shared sources (e.g., combustion)."
        elif correlation < 0.3 and avg_ratio > 1.0:
            source_inference = "Low correlation, high SO2/PM2.5 ratio. Suggests industrial activity."
        elif correlation < 0.3 and avg_ratio <= 1.0:
            source_inference = "Low correlation, low ratio. Suggests traffic or mixed sources."
        else:
            source_inference = "Moderate correlation. Source mixed or unclear."

        # Construct result summary
        result["result_summary"] = [
            {
                "name": "Pearson Correlation (SO2 vs PM2.5)",
                "value": round(float(correlation), 4) if not pd.isna(correlation) else None,
                "description": "Measure of linear relationship between SO2 and PM2.5.",
                "timestamp": datetime.now().isoformat()
            },
            {
                "name": "Average SO2/PM2.5 Ratio",
                "value": round(float(avg_ratio), 4) if not pd.isna(avg_ratio) else None,
                "description": "Ratio indicating relative dominance of SO2 over PM2.5.",
                "timestamp": datetime.now().isoformat()
            },
            {
                "name": "Source Inference",
                "value": source_inference,
                "description": "Heuristic interpretation of correlation and ratio.",
                "timestamp": datetime.now().isoformat()
            }
        ]

    except Exception as e:
        # Capture standard error and prepare JSON error output
        result["error"] = str(e)
        # Print JSON to stdout for validation
        print(json.dumps(result))
        # Ensure exit code is non-zero for failure
        sys.exit(1)

    # Output result to stdout
    print(json.dumps(result))
    
    # Ensure output directory exists and save to file
    try:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{TASK_NAME}_result.json")
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass # Ignore file write errors if disk is read-only, but stdout already succeeded

if __name__ == "__main__":
    main()