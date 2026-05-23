import pandas as pd
import os
import json
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

data = pd.read_csv(data_path)

thresholds = {
    'co': 1000,
    'pm2_5': 35
}

exceedances = {}
for column, threshold in thresholds.items():
    exceedances[column] = data[data[column] > threshold]

result_summary = []
for column, exceedance_data in exceedances.items():
    if not exceedance_data.empty:
        result_summary.append({
            'name': f'{column} exceedance',
            'value': exceedance_data.shape[0],
            'description': f'{column} concentration exceeded {thresholds[column]} μg/m3',
            'timestamp': datetime.now().isoformat()
        })

result = {
    'task_name': 'pollutant_exceedance_notification',
    'description': 'Trigger notifications when pollutant concentrations exceed threshold values',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

output_path = os.path.join('output', 'air_quality', 'pollutant_exceedance_notification_result.json')
with open(output_path, 'w') as f:
    json.dump(result, f, indent=4)