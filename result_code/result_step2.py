import os
import glob
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style="whitegrid", context="paper")

# =========================
# CONFIG
# =========================
BASE_DIRS = [
    "Rpi4 Updated Data/Wind/timestamp_path/wind/",
    "Rpi5 Updated Data/Wind/timestamp_path/wind/"
]

# =========================
# LOAD FILES (EXCLUDE RESOURCE)
# =========================
files = []
for base_dir in BASE_DIRS:
    files.extend([
        f for f in glob.glob(os.path.join(base_dir, "step2_*.csv"))
        if "resource" not in os.path.basename(f).lower()
    ])


if not files:
    raise RuntimeError("No valid step2 CSV files found")

dfs = []
for f in files:
    df = pd.read_csv(f)

    model = (
        os.path.basename(f)
        .replace("step2_", "")
        .rsplit("_", 2)[0]
    )

    # Add device source (RPi4 or RPi5)
    if "Rpi4" in f:
        df["device"] = "RPi4"
    elif "Rpi5" in f:
        df["device"] = "RPi5"

    df["model"] = model
    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)

# =========================
# AGGREGATE METRICS
# =========================
metrics = (
    df_all
    .groupby("model")
    .agg(
        mean_duration_sec=("script_duration_sec", "mean"),
        prompt_tps=("prompt_tokens_per_sec", "mean"),
        completion_tps=("completion_tokens_per_sec", "mean"),
        llm_duration=("llm_duration_sec", "mean"),
    )
    .reset_index()
)

print(metrics)

# Save metrics to CSV
metrics.to_csv("step2_rpi4_rpi5_metric_wind.csv", index=False)
print("\nMetrics saved to: step2_rpi4_rpi5_metric_wind.csv")

# =========================
# HELPER: ADD VALUES ON BARS
# =========================
def annotate_bars(ax, fmt="{:.2f}"):
    for p in ax.patches:
        ax.annotate(
            fmt.format(p.get_height()),
            (p.get_x() + p.get_width() / 2., p.get_height()),
            ha="center",
            va="bottom",
            fontsize=9,
            color="black"
        )

# =========================
# BAR GRAPHS
# =========================
plt.figure(figsize=(10,4))
ax = sns.barplot(data=metrics, x="model", y="mean_duration_sec")
annotate_bars(ax)
plt.title("Step-2 Mean Code Generation Time (sec)")
plt.xticks(rotation=30)
plt.tight_layout()
#plt.savefig("step2_plot_duration_wind.png")
plt.close()

plt.figure(figsize=(10,4))
ax = sns.barplot(data=metrics, x="model", y="prompt_tps")
annotate_bars(ax)
plt.title("Prompt Tokens per Second")
plt.xticks(rotation=30)
plt.tight_layout()
#plt.savefig("step2_plot_prompt_tps_wind.png")
plt.close()

plt.figure(figsize=(10,4))
ax = sns.barplot(data=metrics, x="model", y="completion_tps")
annotate_bars(ax)
plt.title("Completion Tokens per Second")
plt.xticks(rotation=30)
plt.tight_layout()
#plt.savefig("step2_plot_completion_tps_wind.png")
plt.close()

# =========================
# LINE GRAPH (LLM DURATION)
# =========================
plt.figure(figsize=(10,4))
ax = sns.lineplot(data=metrics, x="model", y="llm_duration", marker="o")
for i, v in enumerate(metrics["llm_duration"]):
    ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
plt.title("Average LLM Duration (sec)")
plt.xticks(rotation=30)
plt.tight_layout()
#plt.savefig("step2_plot_llm_duration_wind.png")
plt.close()
