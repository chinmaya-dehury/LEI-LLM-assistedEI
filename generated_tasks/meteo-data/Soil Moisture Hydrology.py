import re
"""
Task: Soil Moisture Hydrology
Description: Examine the soil moisture and watermark data to understand the local hydrology, monitor soil drying trends, and identify potential water stress events.
"""

# Programmatic path resolution pre-injected for reliability
import os
from pathlib import Path

_curr_dir = Path(__file__).resolve().parent
_root_dir = _curr_dir
while _root_dir.name and not (_root_dir / "data").exists():
    _parent = _root_dir.parent
    if _parent == _root_dir:
        break
    _root_dir = _parent

DATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "meteo-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "meteo-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os
from pathlib import Path
import csv
import math
import json
from datetime import datetime

def parse_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def main():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
        
    data_file = root_dir / "data" / "meteo-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "meteo-data" / "raw_data.txt"
    if not data_file.exists():
        print("Error: Meteorological data file not found.")
        return
        
    soil_moisture = []
    watermark = []
    timestamp = []
    
    dropped_rows = 0
    
    with open(data_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            try:
                soil_moisture.append(parse_float(row["soil_moisture"]))
                watermark.append(parse_float(row["watermark"]))
                timestamp.append(int(row["time_since_epoch"]))
            except (ValueError, KeyError):
                dropped_rows += 1
                continue
                
    if dropped_rows > 0:
        print(f"Warning: Dropped {dropped_rows} rows due to missing or invalid data.")
        
    result = {
        "task_name": "Soil Moisture Hydrology",
        "description": "Examine the soil moisture and watermark data to understand the local hydrology, monitor soil drying trends, and identify potential water stress events.",
        "result_summary": [
            f"Analyzed {len(soil_moisture)} data points for soil moisture and watermark.",
            f"Dropped {dropped_rows} rows due to missing or invalid data.",
            f"Soil moisture range: {min(soil_moisture):.2f} - {max(soil_moisture):.2f}%",
            f"Watermark range: {min(watermark):.2f} - {max(watermark):.2f} kPa"
        ],
        "result_generated_at": datetime.now().isoformat()
    }
    
    output_path = os.path.join(OUTPUT_DIR, "soil_moisture_hydrology_result.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
        
    print(f"Result saved to: {output_path}")

if __name__ == "__main__":
    main()