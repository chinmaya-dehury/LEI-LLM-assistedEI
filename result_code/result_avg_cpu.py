"""
Later merge this with result_res.py once verified.
This script processes a single CSV file containing all steps' metrics.
"""
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
INPUT_CSVS = [
    "Rpi4 Updated Data/Wind/timestamp_path/wind/all_steps_metrics.csv",
    "Rpi5 Updated Data/Wind/timestamp_path/wind/all_steps_metrics.csv"
]
OUTPUT_CSV = "avg_cpu_memory_per_run_step_model_rpi4_rpi5_wind.csv"

# =========================
# LOAD CSVs
# =========================
dfs = []
for csv_file in INPUT_CSVS:
    try:
        df_temp = pd.read_csv(csv_file)
        # Add device identifier
        if "Rpi4" in csv_file:
            df_temp["device"] = "RPi4"
        elif "Rpi5" in csv_file:
            df_temp["device"] = "RPi5"
        dfs.append(df_temp)
    except Exception as e:
        print(f"Warning: Could not load {csv_file}: {e}")

if not dfs:
    raise ValueError("No CSV files could be loaded")

df = pd.concat(dfs, ignore_index=True)

required_cols = {
    "model_name", "step", "run_count", "cpu_percent", "memory_percent"
}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# =========================
# AGGREGATE (PER RUN, STEP, MODEL)
# =========================
agg = (
    df
    .groupby(["model_name", "step", "run_count"], as_index=False)
    .agg(
        avg_cpu_percent=("cpu_percent", "mean"),
        avg_memory_percent=("memory_percent", "mean")
    )
)

# =========================
# SAVE RESULT (CSV — NO DEPENDENCY ISSUES)
# =========================
agg.to_csv(OUTPUT_CSV, index=False)

# =========================
# HEATMAP: CPU
# =========================
cpu_heatmap = (
    agg
    .groupby(["model_name", "step"])["avg_cpu_percent"]
    .mean()
    .unstack()
)

plt.figure(figsize=(10, 6))
sns.heatmap(
    cpu_heatmap,
    annot=True,
    fmt=".2f",
    cmap="YlOrRd",
    linewidths=0.4,
    cbar_kws={"label": "Average CPU Usage (%)"}
)
plt.xlabel("Pipeline Step")
plt.ylabel("Model")
plt.title("Average CPU Usage per Step per Model")
plt.tight_layout()
plt.savefig("avg_cpu_usage_heatmap_wind.png")
plt.close()

# =========================
# HEATMAP: MEMORY
# =========================
mem_heatmap = (
    agg
    .groupby(["model_name", "step"])["avg_memory_percent"]
    .mean()
    .unstack()
)

plt.figure(figsize=(10, 6))
sns.heatmap(
    mem_heatmap,
    annot=True,
    fmt=".2f",
    cmap="Blues",
    linewidths=0.4,
    cbar_kws={"label": "Average Memory Usage (%)"}
)
plt.xlabel("Pipeline Step")
plt.ylabel("Model")
plt.title("Average Memory Usage per Step per Model")
plt.tight_layout()
plt.savefig("avg_memory_usage_heatmap_wind.png")
plt.close()

print("\nImages saved: avg_cpu_usage_heatmap_wind.png, avg_memory_usage_heatmap_wind.png")