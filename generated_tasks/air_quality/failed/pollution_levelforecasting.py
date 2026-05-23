import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import os
import json
from datetime import datetime

data_path = os.path.join("data", "air_quality", "raw_data.csv")
df = pd.read_csv(data_path)
df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
df.set_index('timestamp_utc', inplace=True)
df_resampled = df.resample('H').mean()
X = df_resampled.index.map(pd.Timestamp.toordinal)
X = X.values.reshape(-1, 1)
y = df_resampled['pm2_5'].values
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = LinearRegression()
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
result_summary = [
    {
        "name": "MSE",
        "value": mse,
        "description": "Mean Squared Error",
        "timestamp": datetime.now().isoformat()
    }
]
result = {
    "task_name": "pollution_levelforecasting",
    "description": "Develop a forecasting model to predict future air quality levels based on historical data and trends.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}
output_path = os.path.join("output", "air_quality", "pollution_levelforecasting_result.json")
with open(output_path, 'w') as f:
    json.dump(result, f)