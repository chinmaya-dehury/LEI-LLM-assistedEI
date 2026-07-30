import json
"""
Task: Surface Temperature Correlation
Description: Examine the relationship between ambient temperature and surface temperature to understand the thermal dynamics of the local environment.
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
        
    ambient_temps = []
    surface_temps = []
    dropped_rows = 0
    
    with open(data_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            
            ambient_temp = parse_float(row.get("ambient_temperature"))
            surface_temp = parse_float(row.get("surface_temperature"))
            
            if ambient_temp is None or surface_temp is None:
                dropped_rows += 1
                continue
                
            ambient_temps.append(ambient_temp)
            surface_temps.append(surface_temp)
            
    print(f"Dropped {dropped_rows} rows due to missing data.")
    
    result = {
        "task_name": "Surface Temperature Correlation",
        "description": "Examine the relationship between ambient temperature and surface temperature to understand the thermal dynamics of the local environment.",
        "result_summary": [
            f"Number of data points: {len(ambient_temps)}",
            f"Minimum ambient temperature: {min(ambient_temps):.2f} °C",
            f"Maximum ambient temperature: {max(ambient_temps):.2f} °C",
            f"Minimum surface temperature: {min(surface_temps):.2f} °C",
            f"Maximum surface temperature: {max(surface_temps):.2f} °C"
        ],
        "result_generated_at": datetime.now().isoformat()
    }
    
    output_path = os.path.join(OUTPUT_DIR, "surface_temperature_correlation_result.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
        
    print(f"Result saved to: {output_path}")

if __name__ == "__main__":
    main()