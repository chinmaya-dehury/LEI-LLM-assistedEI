import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import ast

BASE_DIRS = [
    "Rpi4 Updated Data/Wind/timestamp_path/wind/",
    "Rpi5 Updated Data/Wind/timestamp_path/wind/"
]

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
# STEP 2 — TASKS GENERATED
# =========================
step2_files = []
for base_dir in BASE_DIRS:
    step2_files.extend([
        f for f in glob.glob(os.path.join(base_dir, "step2_*.csv"))
        if "resource" not in f.lower()
    ])

step2_all = []

for f in step2_files:
    df = pd.read_csv(f)
    model = extract_model(f, "step2_")
    df["model"] = model
    df["tasks"] = df["tasks"].apply(parse_tasks)
    df = df.explode("tasks")

    step2_all.append(
        df[["model", "run_count", "tasks"]]
        .rename(columns={"tasks": "task_name"})
        .drop_duplicates()
    )

df_step2 = pd.concat(step2_all, ignore_index=True)

# =========================
# STEP 3 — TASKS REACHED
# =========================
step3_files = []
for base_dir in BASE_DIRS:
    step3_files.extend([
        f for f in glob.glob(os.path.join(base_dir, "step3_*.csv"))
        if "resource" not in f.lower()
    ])

step3_all = []

for f in step3_files:
    df = pd.read_csv(f)
    model = extract_model(f, "step3_")
    df["model"] = model

    # ignore no_corrections_needed
    df = df[df["status"] != "no_corrections_needed"]

    step3_all.append(
        df[["model", "run_count", "task_name"]].drop_duplicates()
    )

df_step3 = pd.concat(step3_all, ignore_index=True)

# =========================
# STEP 4 — TASKS PASSED
# =========================
step4_files = []
for base_dir in BASE_DIRS:
    step4_files.extend([
        f for f in glob.glob(os.path.join(base_dir, "step4_*.csv"))
        if "resource" not in f.lower()
    ])

step4_all = []

for f in step4_files:
    df = pd.read_csv(f)
    model = extract_model(f, "step4_")
    df["model"] = model

    step4_all.append(
        df[["model", "run_count", "task_name"]].drop_duplicates()
    )

df_step4 = pd.concat(step4_all, ignore_index=True)

# =========================
# AGGREGATION
# =========================
models = sorted(df_step2["model"].unique())
summary = []

for model in models:
    s2 = df_step2[df_step2["model"] == model]
    s3 = df_step3[df_step3["model"] == model]
    s4 = df_step4[df_step4["model"] == model]

    step2_cnt = len(s2)
    step3_cnt = len(s3)
    step4_cnt = len(s4)

    red_loss = max(step2_cnt - step3_cnt, 0)

    summary.append({
        "model": model,
        "Step-4 Passed": step4_cnt,
        "Reached Step-3": step3_cnt - step4_cnt,
        "Script Not Generated": red_loss
    })

df_plot = pd.DataFrame(summary).set_index("model")

# =========================
# STACKED BAR PLOT
# =========================
ax = df_plot.plot(
    kind="bar",
    stacked=True,
    figsize=(13, 5),
    color=[
        "#2ca02c",  # Step-4 Passed
        "#1f77b4",  # Reached Step-3
        "#d62728"   # Script Not Generated (RED)
    ]
)

for container in ax.containers:
    labels = [str(int(v)) if v > 0 else "" for v in container.datavalues]
    ax.bar_label(container, labels=labels, label_type="center", fontsize=9, color="black")

plt.ylabel("Number of Tasks")
plt.xlabel("Model")
plt.title("Sequential Pipeline Outcome: Step-2 → Step-3 → Step-4")
plt.xticks(rotation=30)
plt.legend(title=None)
plt.tight_layout()
#plt.savefig("sequential_pipeline_outcome_rpi4_rpi5_wind.png")
plt.close()
