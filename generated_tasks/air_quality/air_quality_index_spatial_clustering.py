import pandas as pd
from sklearn.cluster import KMeans
import numpy as np
from datetime import datetime
import json
import os

data_path = os.path.join("data", "air_quality", "raw_data.csv")

df = pd.read_csv(data_path)

df['aqi_uk'] = pd.to_numeric(df['aqi_uk'], errors='coerce')

df = df.dropna(subset=['aqi_uk'])

kmeans = KMeans(n_clusters=5)

kmeans.fit(df[['lat', 'lon']])

df['cluster'] = kmeans.labels_

df['aqi_avg'] = df.groupby('cluster')['aqi_uk'].transform('mean')

result_summary = []
for cluster in df['cluster'].unique():
    cluster_df = df[df['cluster'] == cluster]
    aqi_avg = cluster_df['aqi_uk'].mean()
    result_summary.append({
        'name': f'Cluster {cluster} AQI Average',
        'value': aqi_avg,
        'description': f'Average AQI for cluster {cluster}',
        'timestamp': datetime.now().isoformat()
    })

result = {
    'task_name': 'air_quality_index_spatial_clustering',
    'description': 'Apply spatial clustering algorithms to group areas with similar air quality index values, enabling the identification of pollution hotspots.',
    'result_summary': result_summary,
    'result_generated_at': datetime.now().isoformat()
}

output_path = os.path.join("output", "air_quality", "air_quality_index_spatial_clustering_result.json")

with open(output_path, 'w') as f:
    json.dump(result, f, indent=4)