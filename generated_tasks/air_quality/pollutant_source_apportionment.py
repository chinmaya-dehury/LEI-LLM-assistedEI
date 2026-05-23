import pandas as pd
import numpy as np
from sklearn.decomposition import NMF

data_path = "data/air_quality/raw_data.csv"
df = pd.read_csv(data_path)
pollutants = ["co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]

# Receptor model using Non-negative Matrix Factorization (NMF)
nmf = NMF(n_components=3, init="random", random_state=0)

# Prepare data for NMF
X = df[pollutants].values

# Fit NMF model
nmf.fit(X)

# Get the contribution of each source to each pollutant
source_contributions = nmf.components_

# Print the source contributions
for i, source in enumerate(source_contributions):
    print(f"Source {i+1} contributions:")
    for j, pollutant in enumerate(pollutants):
        print(f"  {pollutant}: {source[j]:.2f}")

# Save results to JSON file
import json
from datetime import datetime
result_summary = []
for i, source in enumerate(source_contributions):
    for j, pollutant in enumerate(pollutants):
        result_summary.append({
            "name": f"Source {i+1} {pollutant} contribution",
            "value": source[j],
            "description": f"Contribution of source {i+1} to {pollutant}",
            "timestamp": datetime.now().isoformat()
        })
result = {
    "task_name": "pollutant_source_apportionment",
    "description": "Estimate the contribution of different sources to pollutant concentrations.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}
with open("output/air_quality/pollutant_source_apportionment_result.json", "w") as f:
    json.dump(result, f)