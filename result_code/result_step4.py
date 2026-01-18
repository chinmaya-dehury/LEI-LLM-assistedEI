import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
BASE_DIRS = [
    "Rpi4 Updated Data/Wind/timestamp_path/wind/",
    "Rpi5 Updated Data/Wind/timestamp_path/wind/"
]

# =========================
# DISCOVER MODELS
# =========================
step4_files = []
for base_dir in BASE_DIRS:
    step4_files.extend([
        f for f in glob.glob(os.path.join(base_dir, "step4_*.csv"))
        if "resource" not in f.lower()
    ])

all_models = sorted(list(set([
    os.path.basename(f).replace("step4_", "").rsplit("_", 2)[0]
    for f in step4_files
])))

# =========================
# LOAD CSVs (SAFE)
# =========================
dfs = []

for f in step4_files:
    model = os.path.basename(f).replace("step4_", "").rsplit("_", 2)[0]

    try:
        df = pd.read_csv(f)
        if df.empty:
            df = pd.DataFrame(columns=[
                "task_name",
                "script_duration_sec",
                "status",
                "return_code"
            ])
    except Exception:
        df = pd.DataFrame(columns=[
            "task_name",
            "script_duration_sec",
            "status",
            "return_code"
        ])

    # Add device source
    if "Rpi4" in f:
        df["device"] = "RPi4"
    elif "Rpi5" in f:
        df["device"] = "RPi5"

    df["model"] = model
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

# =========================
# NORMALIZE SUCCESS
# =========================
df["success"] = (
    df["status"].astype(str).str.lower() == "success"
) & (df["return_code"] == 0)

# =========================
# AGGREGATE
# =========================
summary = (
    df.groupby("model")
      .agg(
          executed_tasks=("task_name", "nunique"),
          successful_tasks=("success", "sum"),
          mean_exec_time=("script_duration_sec", "mean")
      )
      .reindex(all_models, fill_value=0)
)

# Correct failure calculation
summary["failed_tasks"] = (
    summary["executed_tasks"] - summary["successful_tasks"]
).clip(lower=0)

summary["success_rate (%)"] = (
    summary["successful_tasks"] /
    summary["executed_tasks"].replace(0, 1) * 100
)

summary = summary.fillna(0)

print("\n=== STEP-4 EXECUTION SUMMARY (CORRECT) ===")
print(summary.round(2))

# Save metrics to CSV
summary.to_csv("step4_rpi4_rpi5_metric_wind.csv")
print("\nMetrics saved to: step4_rpi4_rpi5_metric_wind.csv")

# =========================
# STACKED BAR (CORRECT)
# =========================
ax = summary[
    ["successful_tasks", "failed_tasks"]
].plot(
    kind="bar",
    stacked=True,
    figsize=(13, 5),
    color=["#2ca02c", "#d62728"]
)

for container in ax.containers:
    labels = [
        str(int(v)) if v > 0 else ""
        for v in container.datavalues
    ]
    ax.bar_label(container, labels=labels, label_type="center", fontsize=9)

plt.title("Step-4: Final Execution Outcome per Model")
plt.xlabel("Model")
plt.ylabel("Number of Tasks")
plt.xticks(rotation=30)
plt.legend(["Passed", "Failed"])
plt.tight_layout()
#plt.savefig("step4_plot_execution_outcome_wind.png")
plt.close()

# =========================
# EXECUTION TIME (UNCHANGED)
# =========================
if summary["mean_exec_time"].sum() > 0:
    ax = summary["mean_exec_time"].plot(
        kind="bar",
        figsize=(13, 4),
        color="#1f77b4"
    )
    ax.bar_label(ax.containers[0], fmt="%.2f", fontsize=9)
    plt.title("Step-4: Mean Script Execution Time")
    plt.ylabel("Seconds")
    plt.xlabel("Model")
    plt.xticks(rotation=30)
    plt.tight_layout()
    #plt.savefig("step4_plot_execution_time_wind.png")
    plt.close()
