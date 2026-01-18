import os
import glob
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# =========================
# CONFIGURATION
# =========================
FILE_PATTERN = [
    "Rpi4 Updated Data/Wind/validator/wind/validation_summary_*_all_runs.json",
    "Rpi5 Updated Data/Wind/validator/wind/validation_summary_*_all_runs.json"
]
OUTPUT_CSV = "validation_metrics_summary_rpi4_rpi5_wind.csv"

sns.set_theme(style="whitegrid", context="paper")

# =========================
# HELPERS
# =========================
def extract_model_name(filename):
    """
    Extract model name from:
    validation_summary_MODEL_NAME_timestamp_all_runs.json
    """
    base = os.path.basename(filename)
    clean = (
        base.replace("validation_summary_", "")
            .replace("_all_runs.json", "")
            .replace("_all.json", "")
    )

    parts = clean.split("_")
    model_parts = []
    for p in parts:
        if p.startswith("202"):
            break
        model_parts.append(p)

    return "_".join(model_parts)

def categorize_result(status, message):
    status = status.lower()
    message = (message or "").lower()

    if status == "passed":
        if "fixed after" in message or "correction" in message:
            return "Passed (Self-Corrected)"
        return "Passed (Zero-Shot)"

    if "script file not found" in message:
        return "Failed (Code Not Generated)"
    if "correction attempts" in message:
        return "Failed (Attempt Exceeded)"

    return "Failed (Runtime Error)"

# =========================
# PARSE VALIDATION FILES
# =========================
def parse_validation_files(patterns):
    files = []
    if isinstance(patterns, str):
        patterns = [patterns]
    
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    
    if not files:
        raise FileNotFoundError(f"No validation_summary JSON files found matching patterns")

    records = []

    for file in files:
        with open(file, "r") as f:
            data = json.load(f)

        model = data.get("model", extract_model_name(file))
        runs = data.get("runs", {})
        
        # Add device source
        device = "RPi4" if "Rpi4" in file else ("RPi5" if "Rpi5" in file else "Unknown")

        for run_id, tasks in runs.items():
            for task in tasks:
                outcome = categorize_result(
                    task.get("status", ""),
                    task.get("message", "")
                )

                records.append({
                    "model": model,
                    "device": device,
                    "run_id": run_id,
                    "task_name": task.get("task_name"),
                    "status": task.get("status"),
                    "outcome": outcome
                })

    return pd.DataFrame(records)

# =========================
# METRICS & PLOTS
# =========================
def generate_plots(df):
    # ----------------------------
    # 2. Outcome Distribution
    # ----------------------------
    outcome_counts = (
        df.groupby(["model", "outcome"])
          .size()
          .reset_index(name="count")
    )

    outcome_pivot = outcome_counts.pivot(
        index="model",
        columns="outcome",
        values="count"
    ).fillna(0)

    outcome_pivot.div(outcome_pivot.sum(axis=1), axis=0).plot(
        kind="bar",
        stacked=True,
        figsize=(13, 6),
        colormap="tab20"
    )

    plt.title("Distribution of Validation Outcomes per Model")
    plt.ylabel("Proportion")
    plt.xlabel("Model")
    plt.xticks(rotation=30, ha="right")
    plt.legend(title="Outcome", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    #plt.savefig("validation_outcome_distribution_wind.png")
    plt.close()

    # ----------------------------
    # 3. Run-Level Success Rate
    # ----------------------------
    df["passed"] = df["status"] == "passed"

    run_success = (
        df.groupby(["model", "run_id"])
          .agg(
              total_tasks=("task_name", "count"),
              passed_tasks=("passed", "sum")
          )
          .reset_index()
    )

    run_success["run_success_rate"] = (
        run_success["passed_tasks"] / run_success["total_tasks"]
    )

    model_success = (
        run_success
        .groupby("model")["run_success_rate"]
        .mean()
        .mul(100)
        .reset_index(name="avg_success_rate")
    )

    plt.figure(figsize=(12, 5))
    ax = sns.barplot(
        data=model_success,
        x="model",
        y="avg_success_rate",
        palette="viridis"
    )

    plt.ylabel("Average Success Rate per Run (%)")
    plt.xlabel("Model")
    plt.ylim(0, 100)
    plt.xticks(rotation=30, ha="right")

    for p in ax.patches:
        ax.annotate(
            f"{p.get_height():.1f}%",
            (p.get_x() + p.get_width() / 2, p.get_height()),
            ha="center",
            va="bottom",
            fontsize=9
        )

    plt.tight_layout()
    #plt.savefig("validation_success_rate_wind.png")
    plt.close()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    df_validation = parse_validation_files(FILE_PATTERN)

    df_validation.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved processed validation data to {OUTPUT_CSV}")

    print("\n=== Sample Records ===")
    print(df_validation.head(10))

    summary = df_validation.groupby(["model", "outcome"]).size().unstack(fill_value=0)
    print("\n=== Outcome Counts per Model ===")
    print(summary)

    generate_plots(df_validation)
