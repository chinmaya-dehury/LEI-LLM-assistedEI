import pandas as pd
import numpy as np
from scipy.stats import spearmanr

data = [
    ["moonshotai/kimi-k2.7-code", "agri-data", 18, 7, 2, 0, 9, 0.488888889, 0.466666667, 0.494444444, 0.5, 0.477777778],
    ["moonshotai/kimi-k2.7-code", "air-quality", 19, 10, 1, 4, 4, 0.742105263, 0.668421053, 0.765789474, 0.789473684, 0.652631579],
    ["moonshotai/kimi-k2.7-code", "lab-data", 17, 12, 0, 1, 4, 0.752941176, 0.735294118, 0.758823529, 0.764705882, 0.729411765],
    ["moonshotai/kimi-k2.7-code", "meteo-data", 10, 5, 1, 0, 4, 0.59, 0.57, 0.595, 0.6, 0.58],
    ["openai/gpt-4o-mini", "agri-data", 14, 4, 0, 0, 10, 0.285714286, 0.285714286, 0.285714286, 0.285714286, 0.285714286],
    ["openai/gpt-4o-mini", "air-quality", 17, 10, 2, 2, 3, 0.788235294, 0.729411765, 0.805882353, 0.823529412, 0.729411765],
    ["openai/gpt-4o-mini", "lab-data", 12, 2, 0, 0, 10, 0.166666667, 0.166666667, 0.166666667, 0.166666667, 0.166666667],
    ["openai/gpt-4o-mini", "meteo-data", 12, 3, 1, 2, 6, 0.458333333, 0.391666667, 0.479166667, 0.5, 0.383333333],
    ["qwen/qwen3.7-flash", "agri-data", 8, 3, 2, 2, 1, 0.8, 0.675, 0.8375, 0.875, 0.675],
    ["qwen/qwen3.7-flash", "air-quality", 10, 2, 4, 3, 1, 0.8, 0.63, 0.85, 0.9, 0.64],
    ["qwen/qwen3.7-flash", "lab-data", 12, 0, 4, 4, 4, 0.566666667, 0.4, 0.616666667, 0.666666667, 0.4],
    ["qwen/qwen3.7-flash", "meteo-data", 10, 5, 4, 0, 1, 0.86, 0.78, 0.88, 0.9, 0.82]
]

columns = ["model", "dataset", "Total_Valid_Tasks", "P0", "P1", "P2", "F", 
           "R_sys_baseline", "R_sys_harsh", "R_sys_more", "R_sys_equal", "R_sys_steep_decay"]

df = pd.DataFrame(data, columns=columns)

# Compute average R_sys per model across datasets
model_summary = df.groupby("model")[["R_sys_baseline", "R_sys_equal", "R_sys_more", "R_sys_harsh", "R_sys_steep_decay"]].mean()

# Sort by R_sys_baseline descending
model_summary = model_summary.sort_values(by="R_sys_baseline", ascending=False)

# Compute Max Delta R_sys for each model across configurations
model_summary["Max_Delta"] = model_summary[["R_sys_baseline", "R_sys_equal", "R_sys_more", "R_sys_harsh", "R_sys_steep_decay"]].max(axis=1) - \
                             model_summary[["R_sys_baseline", "R_sys_equal", "R_sys_more", "R_sys_harsh", "R_sys_steep_decay"]].min(axis=1)

# Compute Spearman rank correlation compared to Baseline for each config
configs = ["R_sys_equal", "R_sys_more", "R_sys_harsh", "R_sys_steep_decay"]
spearman_corrs = {}
for c in configs:
    corr, _ = spearmanr(model_summary["R_sys_baseline"], model_summary[c])
    spearman_corrs[c] = corr

# Also compute Spearman rank correlation overall across all 12 dataset-model pairs
overall_spearman = {}
for c in configs:
    corr, _ = spearmanr(df["R_sys_baseline"], df[c])
    overall_spearman[c] = corr

print("Model Summary:")
print(model_summary)
print("\nSpearman Correlation (Model Average Rankings vs Baseline):", spearman_corrs)
print("\nSpearman Correlation (Overall 12 Dataset-Model Pair Rankings vs Baseline):", overall_spearman)