import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import ast

# =========================
# CONFIG
# =========================
BASE_DIRS = [
    "Rpi5 Updated Data/Wind/timestamp_path/wind/",
    "Rpi5 Updated Data/Wind/timestamp_path/wind/"
]

# =========================
# HELPERS
# =========================
def extract_model(filename, prefix):
    return os.path.basename(filename).replace(prefix, "").rsplit("_", 2)[0]

def parse_tasks(val):
    if pd.isna(val):
        return []
    try:
        parsed = ast.literal_eval(val)
        if isinstance(parsed, list):
            return parsed
    except:
        pass
    return [t.strip() for t in str(val).split(",") if t.strip()]

# =========================
# LOAD STEP-3 FILES
# =========================
step3_files = []
for base_dir in BASE_DIRS:
    step3_files.extend([
        f for f in glob.glob(os.path.join(base_dir, "step3_*.csv"))
        if "resource" not in f.lower()
    ])

dfs = []
for f in step3_files:
    df = pd.read_csv(f)
    model = extract_model(f, "step3_")
    
    # Add device source
    if "Rpi4" in f:
        df["device"] = "RPi4"
    elif "Rpi5" in f:
        df["device"] = "RPi5"
    
    df["model"] = model
    dfs.append(df)

df3 = pd.concat(dfs, ignore_index=True)
ALL_MODELS = sorted(df3["model"].unique())

# =========================
# LOAD STEP-2 FILES (FOR RED BAR)
# =========================
step2_files = []
for base_dir in BASE_DIRS:
    step2_files.extend([
        f for f in glob.glob(os.path.join(base_dir, "step2_*.csv"))
        if "resource" not in f.lower()
    ])

step2_records = []
for f in step2_files:
    df2 = pd.read_csv(f)
    model = extract_model(f, "step2_")
    df2["model"] = model

    df2["task_list"] = df2["tasks"].apply(parse_tasks)
    df2 = df2.explode("task_list")

    step2_records.append(
        df2[["model", "run_count", "task_list"]]
        .rename(columns={"task_list": "task_name"})
        .drop_duplicates()
    )

df2 = pd.concat(step2_records, ignore_index=True)

# =========================
# STEP-3 TASK CLASSIFICATION
# =========================
def classify_task(task_df):
    if (task_df["status"] == "no_corrections_needed").any():
        return "Failed (Script Not Generated)"

    if ((task_df["status"] == "passed") & (task_df["attempt"] == 0)).any():
        return "Passed @ Attempt 0"
    if ((task_df["status"] == "passed") & (task_df["attempt"] == 1)).any():
        return "Passed @ Attempt 1"
    if ((task_df["status"] == "passed") & (task_df["attempt"] == 2)).any():
        return "Passed @ Attempt 2"

    if task_df["status"].str.contains("timeout", case=False).any():
        return "Failed (LLM Timeout)"

    return "Failed (After Attempts)"

task_outcomes = (
    df3.groupby(["model", "run_count", "task_name"])
       .apply(classify_task)
       .reset_index(name="outcome")
)

# =========================
# AGGREGATE STEP-3 OUTCOMES
# =========================
EXPECTED = [
    "Passed @ Attempt 0",
    "Passed @ Attempt 1",
    "Passed @ Attempt 2",
    "Failed (After Attempts)",
    "Failed (LLM Timeout)",
    "Failed (Script Not Generated)"
]

summary = (
    task_outcomes
    .groupby(["model", "outcome"])
    .size()
    .unstack(fill_value=0)
)

summary = summary.reindex(columns=EXPECTED, fill_value=0)
summary = summary.reindex(ALL_MODELS, fill_value=0)

# =========================
# CALCULATE PERFORMANCE METRICS
# =========================
perf_metrics = (
    df3
    .groupby("model")
    .agg(
        mean_duration_sec=("script_duration_sec", "mean"),
        prompt_tps=("prompt_tokens_per_sec", "mean"),
        completion_tps=("completion_tokens_per_sec", "mean"),
        llm_duration_sec=("llm_duration_sec", "mean"),
    )
    .reindex(ALL_MODELS) # Ensure all models are present
)

# Merge performance metrics with task outcomes summary
summary = summary.join(perf_metrics).fillna(0)

# Save metrics to CSV
summary.to_csv("step3_rpi4_rpi5_metric_wind.csv")
print("Metrics saved to: step3_rpi4_rpi5_metric_wind.csv")
print(summary)

# =========================
# ADD RED BAR FROM STEP-2 GAP
# =========================
for model in ALL_MODELS:
    step2_cnt = len(df2[df2["model"] == model])
    step3_cnt = len(
        task_outcomes[task_outcomes["model"] == model]
        [["run_count", "task_name"]]
        .drop_duplicates()
    )

    summary.loc[model, "Failed (Script Not Generated)"] = max(step2_cnt - step3_cnt, 0)

# =========================
# PLOT
# =========================
ax = summary.plot(
    kind="bar",
    stacked=True,
    figsize=(13, 5),
    color=[
        "#2ca02c",  # Passed @ Attempt 0
        "#98df8a",  # Passed @ Attempt 1
        "#c7e9c0",  # Passed @ Attempt 2
        "#ff7f0e",  # Failed (After Attempts)
        "#7f7f7f",  # Failed (LLM Timeout)
        "#d62728"   # Failed (Script Not Generated)
    ]
)

for c in ax.containers:
    labels = [str(int(v)) if v > 0 else "" for v in c.datavalues]
    ax.bar_label(c, labels=labels, label_type="center", fontsize=9, color="black")

plt.xlabel("Model")
plt.ylabel("Number of Tasks")
plt.title("Step-3 Task Outcomes with Script-Generation Failures")
plt.xticks(rotation=30)
plt.legend(title=None)
plt.tight_layout()
#plt.savefig("step3_plot_task_outcomes_wind.png")
plt.close()
