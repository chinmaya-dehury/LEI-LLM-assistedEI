"""
Task: Mote Temperature Calibration Comparison
Description: Compare temperature readings from multiple motes at overlapping epochs to evaluate calibration consistency and suggest recalibration if discrepancies exceed a tolerance level.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "lab-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import csv
from pathlib import Path
import os

def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

class MoteTemperatureCalibration:
    def __init__(self, tolerance=0.5):
        self.tolerance = tolerance  # degrees Celsius
        self.discrepancies = []

    def process_file(self, filepath):
        root_dir = Path(__file__).resolve().parent
        while (root_dir / 'data').exists() is False:
            root_dir = root_dir.parent
            if root_dir == root_dir.parent:  # prevent infinite loop
                break
        data_path = root_dir / 'data' / 'lab-data' / Path(filepath).name
        if not data_path.exists():
            print(f"File {filepath} not found.")
            return
        with open(data_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            # Normalize column names to lowercase
            for row in rows:
                row = {k.lower(): v for k, v in row.items()}
            epoch_to_readings = {}
            for row in rows:
                epoch = int(row['epoch'])
                mote_id = int(row['moteid'])
                temperature = safe_float(row.get('temperature'))
                if epoch not in epoch_to_readings:
                    epoch_to_readings[epoch] = {}
                epoch_to_readings[epoch][mote_id] = temperature
            # Compare temperatures across motes for each epoch
            for epoch, readings in epoch_to_readings.items():
                first_mote = next(iter(readings))
                first_temp = readings[first_mote]
                if first_temp is None:
                    continue  # skip rows with missing temperature
                for mote_id, temp in readings.items():
                    if temp is None:
                        continue  # skip missing values
                    diff = abs(temp - first_temp)
                    if diff > self.tolerance:
                        self.discrepancies.append((epoch, first_mote, mote_id, diff))
    def summarize(self):
        print(f"Total discrepant readings: {len(self.discrepancies)}")
        for epoch, m1, m2, diff in sorted(self.discrepancies):
            print(f"Epoch {epoch}: Mote {m1} vs Mote {m2} discrepancy = {diff:.2f}°C")

if __name__ == "__main__":
    calibrator = MoteTemperatureCalibration()
    calibrator.process_file('raw_data.csv')  # or 'raw_data.txt' as needed
    calibrator.summarize()