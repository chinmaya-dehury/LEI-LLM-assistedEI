import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import acf

data_path = 'data/air_quality/raw_data.csv'
df = pd.read_csv(data_path)
df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
df.set_index('timestamp_utc', inplace=True)

# Calculate autocorrelation for each column
for col in df.columns:
    if col not in ['lat', 'lon']:
        autocorrelation = acf(df[col])
        plt.plot(autocorrelation)
        plt.title(f'Autocorrelation of {col}')
        plt.xlabel('Lag')
        plt.ylabel('Autocorrelation')
        plt.show()

        # Save results to json file
        import json
        result_summary = []
        for i, value in enumerate(autocorrelation):
            result_summary.append({'name': f'Lag {i}', 'value': value, 'description': f'Autocorrelation at lag {i}', 'timestamp': pd.Timestamp('now').isoformat()})
        result = {'task_name': 'temporal_autocorrelation_analysis', 'description': 'Examine the temporal autocorrelation of air quality metrics.', 'result_summary': result_summary, 'result_generated_at': pd.Timestamp('now').isoformat()}
        with open('output/air_quality/temporal_autocorrelation_analysis_result.json', 'w') as f:
            json.dump(result, f)