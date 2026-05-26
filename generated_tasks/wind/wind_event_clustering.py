"""
Task: wind_event_clustering
Description: Apply clustering algorithms to group similar wind events based on wind speed, direction, and gusts, allowing for the identification of patterns and relationships in wind data.
"""

import pandas as pd
from sklearn.cluster import KMeans
import numpy as np
import os
import json
from datetime import datetime

data_path = os.path.join("data", "wind", "raw_data.csv")

df = pd.read_csv(data_path)

df["date"] = pd.to_datetime(df["date"])

df_features = df[["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"]]

kmeans = KMeans(n_clusters=5)

kmeans.fit(df_features)

labels = kmeans.labels_

df["cluster"] = labels

result_summary = []
for cluster in np.unique(labels):
    cluster_df = df[df["cluster"] == cluster]
    result_summary.append({
        "name": f"Cluster {cluster}",
        "value": cluster_df.shape[0],
        "description": f"Number of wind events in cluster {cluster}",
        "timestamp": datetime.now().isoformat()
    })

result = {
    "task_name": "wind_event_clustering",
    "description": "Apply clustering algorithms to group similar wind events based on wind speed, direction, and gusts.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}

output_path = os.path.join("output", "wind", "wind_event_clustering_result.json")

with open(output_path, "w") as f:
    json.dump(result, f, indent=4)