import pandas as pd
import os

# Set data path
data_path = os.path.join('data', 'air_quality', 'raw_data.csv')

# Load data
try:
    df = pd.read_csv(data_path)
    df = df.dropna(subset=['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3'])
except Exception as e:
    print(f"Error loading data: {str(e)}")
    exit()

# Calculate maximum concentrations
max_pollutants = df[['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']].max()

# Determine primary pollutant
primary_pollutant = max_pollutants.idxmax()
max_value = max_pollutants.max()

# Save results
output_path = os.path.join('results', 'pollutant_contribution_analysis.json')
with open(output_path, 'w') as f:
    import json
    json.dump({
        'primary_pollutant': primary_pollutant,
        'max_concentration': round(max_value, 2),
        'pollutants': dict(max_pollutants)
    }, f, indent=2)