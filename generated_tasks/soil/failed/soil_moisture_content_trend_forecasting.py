"""
Task: soil_moisture_content_trend_forecasting
Description: Forecast future soil moisture content based on historical trends for proactive irrigation planning
"""

import os
import json
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime

data_path = os.path.join('data', 'soil', 'raw_data.csv')
output_path = os.path.join('output', 'soil', 'soil_moisture_content_trend_forecasting_result.json')

# Load data
try:
    data = pd.read_csv(data_path)
except Exception as e:
    print(f'Error loading data: {e}')
    exit(1)

data['date'] = pd.to_datetime(data['date'])

data['soil_moisture_0_to_1cm'] = data['soil_moisture_0_to_1cm'].astype(float)

data['soil_moisture_1_to_3cm'] = data['soil_moisture_1_to_3cm'].astype(float)

data['soil_moisture_9_to_27cm'] = data['soil_moisture_9_to_27cm'].astype(float)

# Prepare data for forecasting
X = data[['date']]
X['date'] = X['date'].apply(lambda x: x.timestamp())
Y = data[['soil_moisture_0_to_1cm', 'soil_moisture_1_to_3cm', 'soil_moisture_9_to_27cm']]

# Create and fit linear regression model
model = LinearRegression()
try:
    model.fit(X, Y)
except Exception as e:
    print(f'Error fitting model: {e}')
    exit(1)

# Forecast future soil moisture content
future_date = datetime.now().timestamp() + 86400  # forecast for next day
future_X = [[future_date]]
future_Y = model.predict(future_X)

# Save result
result = {
    'task_name': 'soil_moisture_content_trend_forecasting',
    'description': 'Forecast future soil moisture content based on historical trends for proactive irrigation planning',
    'result_summary': [float(x) for x in future_Y[0]],
    'result_generated_at': str(datetime.now())
}

with open(output_path, 'w') as f:
    json.dump(result, f)