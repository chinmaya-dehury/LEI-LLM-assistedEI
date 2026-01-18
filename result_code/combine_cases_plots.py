import os
import glob
import ast
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.patches import Patch

# Root folder containing all rpi4+rpi5 outputs
RESULT_DIR = "result_rpi4_rpi5"
CASES = ["aq", "wind", "soil", "th"]
CASE_COLORS = {"aq": "#1f77b4", "wind": "#ff7f0e", "soil": "#2ca02c", "th": "#d62728"}
PIPELINE_COLORS = {
    "Step-4 Passed": "#A8E6CF",
    "Reached Step-3": "#B4D7FF",
    "Script Not Generated": "#FFB3B3",
}

CASE_BASE_DIRS = {
    "aq": [
        "Rpi4 Updated Data/AQ/timestamp_path/air_quality/",
        "Rpi5 Updated Data/AQ/timestamp_path/air_quality/",
    ],
    "wind": [
        "Rpi4 Updated Data/Wind/timestamp_path/wind/",
        "Rpi5 Updated Data/Wind/timestamp_path/wind/",
    ],
    "soil": [
        "Rpi4 Updated Data/Soil/timestamp_path/soil/",
        "Rpi5 Updated Data/Soil/timestamp_path/soil/",
    ],
    "th": [
        "Rpi4 Updated Data/TH/timestamp_path/temp_humidity/",
        "Rpi5 Updated Data/TH/timestamp_path/temp_humidity/",
    ],
}

sns.set_theme(style="whitegrid", context="paper")


def _case_path(filename_template: str, case: str) -> str:
    return os.path.join(RESULT_DIR, filename_template.format(case=case))


def _load_data(filename_template: str) -> pd.DataFrame:
    """Generic function to load data for all cases"""
    dfs = {}
    for case in CASES:
        path = _case_path(filename_template.format(case=case), case)
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["case"] = case
            dfs[case] = df
    return pd.concat(dfs.values(), ignore_index=True) if dfs else None


def load_step1_data():
    """Load step1 metrics for all cases"""
    return _load_data("step1_rpi4_rpi5_perf_metric_{case}.csv")


def load_step2_data():
    """Load step2 metrics for all cases"""
    return _load_data("step2_rpi4_rpi5_metric_{case}.csv")


def load_step4_data():
    """Load step4 metrics for all cases"""
    return _load_data("step4_rpi4_rpi5_metric_{case}.csv")


def load_validation_data():
    """Load validation metrics for all cases"""
    return _load_data("validation_metrics_summary_rpi4_rpi5_{case}.csv")

def _extract_model_from_filename(path: str, prefix: str) -> str:
    return os.path.basename(path).replace(prefix, "").rsplit("_", 2)[0]


def _parse_tasks_column(value):
    if pd.isna(value):
        return []
    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return parsed
    except (ValueError, SyntaxError):
        pass
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _collect_pipeline_summary(case: str):
    base_dirs = CASE_BASE_DIRS.get(case, [])
    if not base_dirs:
        return None

    step2_files, step3_files, step4_files = [], [], []
    for base_dir in base_dirs:
        step2_files.extend([
            f for f in glob.glob(os.path.join(base_dir, "step2_*.csv"))
            if "resource" not in f.lower()
        ])
        step3_files.extend([
            f for f in glob.glob(os.path.join(base_dir, "step3_*.csv"))
            if "resource" not in f.lower()
        ])
        step4_files.extend([
            f for f in glob.glob(os.path.join(base_dir, "step4_*.csv"))
            if "resource" not in f.lower()
        ])

    if not step2_files and not step3_files and not step4_files:
        return None

    step2_records = []
    for file in step2_files:
        try:
            df_temp = pd.read_csv(file)
        except Exception:
            continue
        if "tasks" not in df_temp.columns:
            continue
        model = _extract_model_from_filename(file, "step2_")
        df_temp = df_temp.copy()
        df_temp["model"] = model
        df_temp["tasks"] = df_temp["tasks"].apply(_parse_tasks_column)
        df_temp = df_temp.explode("tasks")
        step2_records.append(
            df_temp[["model", "tasks"]].rename(columns={"tasks": "task_name"}).drop_duplicates()
        )
    df_step2 = pd.concat(step2_records, ignore_index=True) if step2_records else pd.DataFrame(columns=["model", "task_name"])

    step3_records = []
    for file in step3_files:
        try:
            df_temp = pd.read_csv(file)
        except Exception:
            continue
        if "task_name" not in df_temp.columns:
            continue
        model = _extract_model_from_filename(file, "step3_")
        df_temp = df_temp.copy()
        df_temp["model"] = model
        if "status" in df_temp.columns:
            df_temp = df_temp[df_temp["status"] != "no_corrections_needed"]
        step3_records.append(df_temp[["model", "task_name"]].drop_duplicates())
    df_step3 = pd.concat(step3_records, ignore_index=True) if step3_records else pd.DataFrame(columns=["model", "task_name"])

    step4_records = []
    for file in step4_files:
        try:
            df_temp = pd.read_csv(file)
        except Exception:
            continue
        if "task_name" not in df_temp.columns:
            continue
        model = _extract_model_from_filename(file, "step4_")
        df_temp = df_temp.copy()
        df_temp["model"] = model
        step4_records.append(df_temp[["model", "task_name"]].drop_duplicates())
    df_step4 = pd.concat(step4_records, ignore_index=True) if step4_records else pd.DataFrame(columns=["model", "task_name"])

    if df_step2.empty and df_step3.empty and df_step4.empty:
        return None

    models = sorted(set(df_step2["model"]) | set(df_step3["model"]) | set(df_step4["model"]))
    summary_rows = []
    for model in models:
        step2_cnt = len(df_step2[df_step2["model"] == model])
        step3_cnt = len(df_step3[df_step3["model"] == model])
        step4_cnt = len(df_step4[df_step4["model"] == model])

        reached_step3 = max(step3_cnt - step4_cnt, 0)
        not_generated = max(step2_cnt - step3_cnt, 0)

        summary_rows.append({
            "model": model,
            "Step-4 Passed": step4_cnt,
            "Reached Step-3": reached_step3,
            "Script Not Generated": not_generated,
        })

    return pd.DataFrame(summary_rows).set_index("model") if summary_rows else None


def plot_step4_success():
    """Step4: Success rate by model and case"""
    df = load_step4_data()
    if df is None:
        return
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    models = sorted(df["model"].unique())
    x = np.arange(len(models))
    width = 0.2
    
    for i, case in enumerate(CASES):
        case_data = df[df["case"] == case].set_index("model").reindex(models, fill_value=0)
        success_rate = (case_data["successful_tasks"] / case_data["executed_tasks"] * 100).fillna(0)
        ax.bar(x + i * width, success_rate, width, label=case.upper(), 
               color=CASE_COLORS[case], alpha=0.5)
    
    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Success Rate (%)", fontsize=12)
    ax.set_title("Step4: Execution Success Rate by Model and Case", fontsize=14, fontweight="bold")
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(models, rotation=45, ha="right", fontsize=12)
    max_val = max([ax.get_children()[i].get_height() for i in range(len(models)*4) if hasattr(ax.get_children()[i], 'get_height')])
    ax.set_ylim(0, max(max_val * 1.2, 100))
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=11)
    fig.tight_layout()
    #fig.savefig(os.path.join(RESULT_DIR, "combined_step4_success_rate.png"), dpi=150, bbox_inches="tight")
    #fig.savefig(os.path.join(RESULT_DIR, "combined_step4_success_rate.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_step4_execution_outcome():
    """Step4: Stacked execution outcome (passed vs failed) by model and case"""
    df = load_step4_data()
    if df is None:
        return

    models = sorted(df["model"].unique())
    cases_in_plot = [case for case in CASES if case in df["case"].unique()]
    if not models or not cases_in_plot:
        return

    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(models))
    width = 0.5
    offsets = (np.arange(len(cases_in_plot)) - (len(cases_in_plot) - 1) / 2) * width
    category_map = [
        ("successful_tasks", "Passed"),
        ("failed_tasks", "Failed"),
    ]
    hatch_map = {"successful_tasks": "", "failed_tasks": "//"}

    max_total = 0
    for idx, case in enumerate(cases_in_plot):
        case_df = df[df["case"] == case].set_index("model").reindex(models, fill_value=0)

        success = case_df["successful_tasks"].fillna(0) if "successful_tasks" in case_df else pd.Series(0, index=models)
        success = success.reindex(models, fill_value=0).astype(float)

        if "failed_tasks" in case_df:
            failed = case_df["failed_tasks"].reindex(models, fill_value=0).fillna(0).astype(float)
        elif "executed_tasks" in case_df:
            failed = (case_df["executed_tasks"].reindex(models, fill_value=0).fillna(0) - success).clip(lower=0)
        else:
            failed = pd.Series(0, index=models, dtype=float)

        case_summary = pd.DataFrame({
            "successful_tasks": success,
            "failed_tasks": failed,
        })

        total_case = (case_summary["successful_tasks"] + case_summary["failed_tasks"]).max()
        if pd.notna(total_case):
            max_total = max(max_total, float(total_case))

        positions = x + offsets[idx]
        bottom = np.zeros(len(models))
        for column, label in category_map:
            values = case_summary[column].to_numpy()
            ax.bar(
                positions,
                values,
                width,
                bottom=bottom,
                color=CASE_COLORS[case],
                edgecolor="#333333",
                hatch=hatch_map[column],
                alpha=0.50,
            )
            bottom += values

    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Number of Tasks", fontsize=12)
    ax.set_title("Step4: Execution Outcome by Model and Case", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha="right", fontsize=12)
    ax.set_ylim(0, max_total * 1.15 if max_total else 1)

    category_handles = [
        Patch(facecolor="white", edgecolor="#333333", hatch=hatch_map[col], label=label)
        for col, label in category_map
    ]
    legend_stage = ax.legend(handles=category_handles, title="Outcome", loc="upper left", frameon=True, fontsize=11)
    ax.add_artist(legend_stage)

    case_handles = [
        Patch(facecolor=CASE_COLORS[case], edgecolor="#333333", label=case.upper())
        for case in cases_in_plot
    ]
    ax.legend(handles=case_handles, title="Case", loc="upper right", frameon=True, fontsize=11)

    fig.tight_layout()
    #fig.savefig(os.path.join(RESULT_DIR, "combined_step4_execution_outcome.png"), dpi=150, bbox_inches="tight")
    #fig.savefig(os.path.join(RESULT_DIR, "combined_step4_execution_outcome.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_validation_success_grouped():
    """Validation success rate: grouped bars per model across cases."""
    df = load_validation_data()
    if df is None:
        return

    success_rate = (
        df.assign(passed=df["status"] == "passed")
          .groupby(["model", "case"])["passed"]
          .mean()
          .mul(100)
          .reset_index()
    )

    models = sorted(success_rate["model"].unique())
    x = np.arange(len(models))
    width = 0.20

    # Light colors for better visibility
    light_colors = {
        "aq": "#B4D7FF",      # Light blue
        "wind": "#FFD699",    # Light orange
        "soil": "#A8E6CF",    # Light green
        "th": "#FFB3B3",      # Light red
    }

    fig, ax = plt.subplots(figsize=(16, 6))

    # Increase y-limit to make room for vertical text
    ax.set_ylim(0, 90)

    for i, case in enumerate(CASES):
        case_df = (
            success_rate[success_rate["case"] == case]
            .set_index("model")
            .reindex(models, fill_value=0)
        )
        bars = ax.bar(
            x + i * width,
            case_df["passed"],
            width,
            label=case.upper(),
            color=light_colors[case],
            edgecolor="black",
            linewidth=1,
            alpha=0.9
        )
        
        # --- IMPROVED LABEL PLACEMENT ---
        for bar in bars:
            height = bar.get_height()
            # Show label for all bars, including 0.0%
            if height == 0:
                label = "0.0%"
                y_pos = 1  # Place at the base of the bar for better visibility
            else:
                label = f"{height:.1f}%"
                y_pos = height + 2
            ax.text(
                bar.get_x() + bar.get_width() / 2,  # X: Center of bar
                y_pos,                              # Y: Just above bar (or at 1 for zero)
                label,
                ha="center",
                va="bottom",
                rotation=90,                        # <--- ROTATE 90 DEGREES
                fontsize=14,                        # Slightly smaller font
                color="black"
            )

    ax.set_xlabel("Models", fontsize=18)
    ax.set_ylabel("Validation Success Rate (%)", fontsize=18)
    ax.set_title("Validation Success Rate Across Four Use Cases", fontsize=18, fontweight="bold")
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(models, rotation=45, ha="right", fontsize=16)
    
    group_half_width = 2.0 * width  # Half of total group width (4 bars)
    padding = 0.2 * width  # Small breathing room
    
    left_limit = x[0] - width/2 - padding
    right_limit = x[-1] + 3*width + width/2 + padding
    
    ax.set_xlim(left_limit, right_limit)
    # ----------------------------------
    
    ax.legend(ncol=4, loc="upper right", fontsize=14)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.tick_params(axis='y', labelsize=14)  # Increased fontsize from 12 to 14

    fig.tight_layout()
    #fig.savefig(os.path.join(RESULT_DIR, "grouped_validation_success_rate.png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(RESULT_DIR, "grouped_validation_success_rate.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_complete_pipeline_grouped():
    """Pipeline outcome: grouped bars per model across cases."""
    categories = ["Step-4 Passed", "Reached Step-3", "Script Not Generated"]
    
    # Collect pipeline data for all cases
    all_summaries = {}
    for case in CASES:
        summary = _collect_pipeline_summary(case)
        if summary is not None and not summary.empty:
            all_summaries[case] = summary[categories].fillna(0)
    
    if not all_summaries:
        return
    
    # Get all unique models across all cases
    all_models = sorted(set().union(*[set(summary.index) for summary in all_summaries.values()]))
    
    x = np.arange(len(all_models))
    width = 0.20  # Width per bar group
    
    fig, ax = plt.subplots(figsize=(16, 6))
    
    # Increase y-limit to make room for vertical text
    ax.set_ylim(0, 60)
    # Format y-axis ticks as integers
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.tick_params(axis='y', labelsize=12)
    
    case_positions = {
        "aq": x - 1.5 * width,
        "wind": x - 0.5 * width,
        "soil": x + 0.5 * width,
        "th": x + 1.5 * width,
    }
    
    case_markers = {"aq": "o", "wind": "s", "soil": "^", "th": "D"}
    for case_idx, case in enumerate(CASES):
        if case not in all_summaries:
            continue
        summary = all_summaries[case].reindex(all_models, fill_value=0)
        position = case_positions[case]
        # --- Add Case Markers Above Bars ---
        total_heights = summary.sum(axis=1)
        for i, model in enumerate(all_models):
            total_h = total_heights.get(model, 0)
            if total_h > 0:
                ax.plot(position[i], total_h + 2, marker=case_markers[case], color=CASE_COLORS[case], markersize=10, linestyle='None')
        # Stack the categories
        bottom = np.zeros(len(all_models))
        for cat in categories:
            values = summary[cat].to_numpy(dtype=float)
            bars = ax.bar(
                position,
                values,
                width,
                bottom=bottom,
                color=PIPELINE_COLORS[cat],
                edgecolor="black",
                linewidth=0.5,
                label=cat if case_idx == 0 else "",  # Only add label once
            )
            # Add count labels inside bars
            for bar_idx, bar in enumerate(bars):
                height = bar.get_height()
                model = all_models[bar_idx]
                if height >= 3:
                    label = f"{int(height)}"
                    y_pos = bottom[bar_idx] + height / 2
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        y_pos,
                        label,
                        ha="center",
                        va="center",
                        fontsize=15,
                        color="black",
                    )
                elif height == 2:
                    label = f"{int(height)}"
                    y_pos = bottom[bar_idx] + height / 2
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        y_pos,
                        label,
                        ha="center",
                        va="center",
                        fontsize=10,
                        color="black",
                    )
                elif height == 1:
                    label = f"{int(height)}"
                    y_pos = bottom[bar_idx] + height / 2
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        y_pos,
                        label,
                        ha="center",
                        va="center",
                        fontsize=7,
                        color="black",
                    )
                elif height == 0 and case in ["aq", "soil"] and model == "codellama_7b":
                    label = "0"
                    y_pos = 2
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        y_pos,
                        label,
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="black",
                    )
            bottom += values
    
    ax.set_xlabel("Models", fontsize=18)
    ax.set_ylabel("Number of Tasks", fontsize=18)
    ax.set_title("Pipeline Outcome Summary Across Four Use Cases", fontsize=18, fontweight="bold")
    
    # Ticks are already centered at x (0, 1, 2...), so this is correct
    ax.set_xticks(x)
    ax.set_xticklabels(all_models, rotation=45, ha="right", fontsize=18)
    
    group_half_width = 2.0 * width
    padding = 0.2 * width # Small breathing room
    
    left_limit = x[0] - group_half_width - padding
    right_limit = x[-1] + group_half_width + padding
    
    ax.set_xlim(left_limit, right_limit)
    # ----------------------------------

    # Create legend manually
    category_handles = [Patch(facecolor=PIPELINE_COLORS[cat], edgecolor="black", linewidth=1.5, label=cat) for cat in categories]
    case_handles = [plt.Line2D([0], [0], marker=case_markers[case], color=CASE_COLORS[case], label=case.upper(), linestyle='None', markersize=10) for case in CASES]
    # Create two separate legends
    legend1 = ax.legend(handles=category_handles, ncol=3, loc="upper right", fontsize=12, title="Outcome")
    ax.add_artist(legend1)
    ax.legend(handles=case_handles, ncol=4, loc="upper left", fontsize=12, title="Use Case", frameon=True, handlelength=1, handletextpad=0.5, columnspacing=0.8)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "grouped_complete_pipeline.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_avg_cpu():
    """Improved average CPU usage heatmaps (1×4 horizontal grid, publication-ready)."""
    heatmaps = {}
    model_order = []  # To store consistent model order
    vmin, vmax = np.inf, -np.inf

    # --- Load & prepare data ---
    for case in CASES:
        path = _case_path(f"avg_cpu_memory_per_run_step_model_rpi4_rpi5_{case}.csv", case)
        if not os.path.exists(path):
            continue

        df = pd.read_csv(path)
        if df.empty or not {"model_name", "step", "avg_cpu_percent"}.issubset(df.columns):
            continue

        df_case = (
            df.groupby(["model_name", "step"], as_index=False)["avg_cpu_percent"]
              .mean()
        )

        pivot = (
            df_case
            .pivot(index="model_name", columns="step", values="avg_cpu_percent")
            .sort_index()
            .sort_index(axis=1)
        )

        heatmaps[case] = pivot
        if not model_order:
            model_order = list(pivot.index)

        vmin = min(vmin, np.nanmin(pivot.values))
        vmax = max(vmax, np.nanmax(pivot.values))

    if not heatmaps:
        return

    # Create model name mapping (M1, M2, ... M8)
    model_labels = {model: f"M{i+1}" for i, model in enumerate(model_order)}

    # --- Plot (1×4 horizontal layout) ---
    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    axes = axes.flatten()

    # Custom light blue colormap
    from matplotlib.colors import LinearSegmentedColormap
    colors_blue = ["#f0f8ff", "#43C2F4"]  # Light blue to sky blue
    cmap = LinearSegmentedColormap.from_list("light_blue", colors_blue)
    cmap.set_bad(color="lightgray")  # NA = step not reached

    for idx, case in enumerate(CASES):
        ax = axes[idx]
        if case not in heatmaps:
            ax.set_visible(False)
            continue

        pivot = heatmaps[case]

        sns.heatmap(
            pivot,
            ax=ax,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            mask=pivot.isna(),
            annot=True,
            fmt=".1f",
            annot_kws={"fontsize": 20, "color": "black"},
            linewidths=0.3,
            linecolor="white",
            cbar=False,  # single shared colorbar
            square=False,
        )

        ax.set_title(f"{case.upper()}", fontsize=16, fontweight="bold")

        # Show model names (M1, M2...) only on the first subplot
        if idx == 0:
            ax.set_yticklabels([model_labels[m.get_text()] for m in ax.get_yticklabels()], 
                              fontsize=18, rotation=0)
            ax.set_ylabel("Models", fontsize=18)
        else:
            ax.set_yticklabels([])
            ax.set_ylabel("")

        # Show step labels on all subplots (no individual xlabel)
        ax.tick_params(axis="x", labelsize=18)
        ax.set_xlabel("")

    # --- Shared colorbar ---
    cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax)
    cbar.set_label("Average CPU (%)", fontsize=18)
    cbar.ax.tick_params(labelsize=18)

    fig.tight_layout(rect=[0, 0.08, 0.91, 1])
    
    # --- Shared x-axis label (centered, below subplots) ---
    fig.text(0.50, 0.01, "Steps", ha="center", fontsize=18)
    fig.savefig(os.path.join(RESULT_DIR, "combined_avg_cpu.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_avg_memory():
    """Average memory usage heatmaps (1×4 horizontal grid, publication-ready)."""
    heatmaps = {}
    model_order = []  # To store consistent model order
    vmin, vmax = np.inf, -np.inf

    # --- Load & prepare data ---
    for case in CASES:
        path = _case_path(f"avg_cpu_memory_per_run_step_model_rpi4_rpi5_{case}.csv", case)
        if not os.path.exists(path):
            continue

        df = pd.read_csv(path)
        if df.empty or not {"model_name", "step", "avg_memory_percent"}.issubset(df.columns):
            continue

        df_case = (
            df.groupby(["model_name", "step"], as_index=False)["avg_memory_percent"]
              .mean()
        )

        pivot = (
            df_case
            .pivot(index="model_name", columns="step", values="avg_memory_percent")
            .sort_index()
            .sort_index(axis=1)
        )

        heatmaps[case] = pivot
        if not model_order:
            model_order = list(pivot.index)

        vmin = min(vmin, np.nanmin(pivot.values))
        vmax = max(vmax, np.nanmax(pivot.values))

    if not heatmaps:
        return

    # Create model name mapping (M1, M2, ... M8)
    model_labels = {model: f"M{i+1}" for i, model in enumerate(model_order)}

    # --- Plot (1×4 horizontal layout) ---
    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    axes = axes.flatten()

    # Custom light green colormap
    from matplotlib.colors import LinearSegmentedColormap
    colors_green = ["#f0f9f0", "#29F429"]  # Light green to medium light green
    cmap = LinearSegmentedColormap.from_list("light_green", colors_green)
    cmap.set_bad(color="lightgray")  # NA = step not reached

    for idx, case in enumerate(CASES):
        ax = axes[idx]
        if case not in heatmaps:
            ax.set_visible(False)
            continue

        pivot = heatmaps[case]

        sns.heatmap(
            pivot,
            ax=ax,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            mask=pivot.isna(),
            annot=True,
            fmt=".1f",
            annot_kws={"fontsize": 18, "color": "black"},
            linewidths=0.3,
            linecolor="white",
            cbar=False,  # single shared colorbar
            square=False,
        )

        ax.set_title(f"{case.upper()}", fontsize=16, fontweight="bold")

        # Show model names (M1, M2...) only on the first subplot
        if idx == 0:
            ax.set_yticklabels([model_labels[m.get_text()] for m in ax.get_yticklabels()], 
                              fontsize=18, rotation=0)
            ax.set_ylabel("Models", fontsize=18)
        else:
            ax.set_yticklabels([])
            ax.set_ylabel("")

        # Show step labels on all subplots (no individual xlabel)
        ax.tick_params(axis="x", labelsize=18)
        ax.set_xlabel("")

    # --- Shared colorbar ---
    cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax)
    cbar.set_label("Average Memory (%)", fontsize=18)
    cbar.ax.tick_params(labelsize=18)

    fig.tight_layout(rect=[0, 0.08, 0.91, 1])
    
    # --- Shared x-axis label (centered, below subplots) ---
    fig.text(0.45, 0.01, "Steps", ha="center", fontsize=18)

    fig.savefig(os.path.join(RESULT_DIR, "combined_avg_memory.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_combined_duration_metrics():
    """Plot stacked bar chart for mean_duration_sec: one model with 4 bars (one per case), each stacked by steps."""
    # Load metrics for all steps and cases
    step_files = {
        "Step 1": "step1_rpi4_rpi5_perf_metric_{case}.csv",
        "Step 2": "step2_rpi4_rpi5_metric_{case}.csv",
        "Step 3": "step3_rpi4_rpi5_metric_{case}.csv",
        "Step 4": "step4_rpi4_rpi5_metric_{case}.csv",
    }

    df_list = []
    for step, filename_template in step_files.items():
        for case in CASES:
            path = _case_path(filename_template, case)
            if os.path.exists(path):
                df = pd.read_csv(path)
                df["case"] = case
                df["step"] = step
                df["model"] = df["model"].str.strip()
                df_list.append(df)

    if not df_list:
        return

    df_combined = pd.concat(df_list, ignore_index=True)

    # Normalize model names to prevent duplicates caused by whitespace/quotes/case
    df_combined["model"] = (
        df_combined["model"]
        .astype(str)
        .str.strip()
        .str.strip('"')
        .str.strip("'")
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(":", "_", regex=False) 
        .str.replace("-", "_", regex=False)
    )
    df_combined["model_key"] = df_combined["model"].str.lower()

    # Preserve a clean display label per normalized key
    model_display = (
        df_combined
        .drop_duplicates(subset=["model_key"])
        .set_index("model_key")["model"]
        .to_dict()
    )

    # Build a unified duration column per step
    step_duration_column = {
        "Step 1": "avg_duration_sec",
        "Step 2": "mean_duration_sec",
        "Step 3": "mean_duration_sec",
        "Step 4": "mean_exec_time",
    }
    df_combined["duration_sec"] = np.nan
    for step, col in step_duration_column.items():
        if col in df_combined.columns:
            mask = df_combined["step"] == step
            df_combined.loc[mask, "duration_sec"] = pd.to_numeric(df_combined.loc[mask, col], errors="coerce")

    # Aggregate once to avoid accidental duplicates
    df_combined = (
        df_combined
        .groupby(["model_key", "case", "step"], as_index=False)["duration_sec"]
        .mean()
    )

    # Get unique models and move 'codellama_7b' to the front
    all_models = sorted(df_combined["model_key"].unique())
    if "codellama_7b" in all_models:
        all_models.remove("codellama_7b")
        all_models.insert(0, "codellama_7b")

    n_models = len(all_models)
    n_cases = len(CASES)

    # Define colors for steps and markers for cases
    step_colors = {"Step 1": "#A8E6CF", "Step 2": "#B4D7FF", "Step 3": "#FFD699", "Step 4": "#FFB3B3"}
    case_markers = {"aq": "o", "wind": "s", "soil": "^", "th": "D"}

    fig, ax = plt.subplots(figsize=(18, 7))

    # Bar width and spacing - thicker bars for visibility
    bar_width = 0.10
    gap_between_bars = 0.01
    gap_between_groups = 0.1
    group_width = n_cases * bar_width + (n_cases - 1) * gap_between_bars + gap_between_groups
    
    # Pre-compute totals for each (model, case)
    totals = {(m, c): 0 for m in all_models for c in CASES}
    
    # Draw bars: iterate by step (bottom to top stacking)
    for step in step_files.keys():
        for case_idx, case in enumerate(CASES):
            heights = []
            x_vals = []
            bottoms = []
            for model_idx, model in enumerate(all_models):
                row = df_combined[
                    (df_combined["model_key"] == model) &
                    (df_combined["case"] == case) &
                    (df_combined["step"] == step)
                ]
                h = row["duration_sec"].sum() if not row.empty else 0
                heights.append(h)
                # Position: model_group_start + case_offset
                x_val = model_idx * group_width + case_idx * (bar_width + gap_between_bars)
                x_vals.append(x_val)
                bottoms.append(totals[(model, case)])
            
            ax.bar(
                x_vals,
                heights,
                bar_width,
                bottom=bottoms,
                color=step_colors[step],
                edgecolor="black",
                linewidth=0.1,
                label=step if case_idx == 0 else "",
            )
            
            # Update totals
            for model_idx, model in enumerate(all_models):
                totals[(model, case)] += heights[model_idx]

    # Add symbols above each bar (consistent offset)
    max_total = max(totals.values()) if totals else 0
    marker_offset = max(0.02 * max_total, 1)
    for model_idx, model in enumerate(all_models):
        for case_idx, case in enumerate(CASES):
            total_h = totals[(model, case)]
            if total_h > 0:
                x_val = model_idx * group_width + case_idx * (bar_width + gap_between_bars)
                ax.plot(
                    x_val,
                    total_h + marker_offset,
                    marker=case_markers[case],
                    color=CASE_COLORS[case],
                    markersize=8,
                    linestyle="None",
                    markeredgecolor="black",
                    markeredgewidth=0.5,
                )

    # Set x-axis: one label per model, centered on its group of 4 bars
    group_center_offset = (n_cases - 1) * (bar_width + gap_between_bars) / 2
    x_tick_positions = [m * group_width + group_center_offset for m in range(n_models)]
    ax.set_xticks(x_tick_positions)
    ax.set_xticklabels([model_display.get(m, m) for m in all_models], rotation=45, ha="right", fontsize=20)

    last_model_idx = n_models - 1
    last_case_idx = n_cases - 1
    last_bar_center = last_model_idx * group_width + last_case_idx * (bar_width + gap_between_bars)
    edge_padding = 0.05
    left_edge = -bar_width / 2 - edge_padding
    right_edge = last_bar_center + bar_width / 2 + edge_padding
    ax.set_xlim(left_edge, right_edge)

    ax.set_xlabel("Models", fontsize=20)
    ax.set_ylabel("Mean Duration (sec)", fontsize=20)
    ax.set_title("Mean Duration by Steps for Four Use Case", fontsize=20, fontweight="bold")
    ax.tick_params(axis="y", labelsize=16)

    # Create legends for steps and cases
    step_handles = [Patch(facecolor=step_colors[step], edgecolor="black", label=step) for step in step_files.keys()]
    case_handles = [
        plt.Line2D([0], [0], marker=case_markers[case], color=CASE_COLORS[case], label=case.upper(), linestyle="None", markersize=8, markeredgecolor="black", markeredgewidth=0.5)
        for case in CASES
    ]
    ax.legend(handles=step_handles + case_handles, fontsize=12, loc="upper left", ncol=2, title="Legend")

    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "stacked_duration_metrics.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_combined_prompt_tps():
    """Plot stacked bar chart for prompt tokens per second: one model with 4 bars (one per case), each stacked by steps (1-3 only)."""
    # Load metrics for steps 1, 2, 3 only
    step_files = {
        "Step 1": "step1_rpi4_rpi5_perf_metric_{case}.csv",
        "Step 2": "step2_rpi4_rpi5_metric_{case}.csv",
        "Step 3": "step3_rpi4_rpi5_metric_{case}.csv",
    }

    df_list = []
    for step, filename_template in step_files.items():
        for case in CASES:
            path = _case_path(filename_template, case)
            if os.path.exists(path):
                df = pd.read_csv(path)
                df["case"] = case
                df["step"] = step
                df["model"] = df["model"].str.strip()
                df_list.append(df)

    if not df_list:
        return

    df_combined = pd.concat(df_list, ignore_index=True)

    # Normalize model names to prevent duplicates caused by whitespace/quotes/case
    df_combined["model"] = (
        df_combined["model"]
        .astype(str)
        .str.strip()
        .str.strip('"')
        .str.strip("'")
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(":", "_", regex=False) 
        .str.replace("-", "_", regex=False)
    )
    df_combined["model_key"] = df_combined["model"].str.lower()

    # Preserve a clean display label per normalized key
    model_display = (
        df_combined
        .drop_duplicates(subset=["model_key"])
        .set_index("model_key")["model"]
        .to_dict()
    )

    # Build a unified prompt_tps column per step
    step_tps_column = {
        "Step 1": "prompt_tokens_per_sec",
        "Step 2": "prompt_tps",
        "Step 3": "prompt_tps",
    }
    df_combined["prompt_tps_unified"] = np.nan
    for step, col in step_tps_column.items():
        if col in df_combined.columns:
            mask = df_combined["step"] == step
            df_combined.loc[mask, "prompt_tps_unified"] = pd.to_numeric(df_combined.loc[mask, col], errors="coerce")

    # Aggregate once to avoid accidental duplicates
    df_combined = (
        df_combined
        .groupby(["model_key", "case", "step"], as_index=False)["prompt_tps_unified"]
        .mean()
    )

    # Get unique models and move 'codellama_7b' to the front
    all_models = sorted(df_combined["model_key"].unique())
    if "codellama_7b" in all_models:
        all_models.remove("codellama_7b")
        all_models.insert(0, "codellama_7b")

    n_models = len(all_models)
    n_cases = len(CASES)

    # Define colors for steps and markers for cases
    step_colors = {"Step 1": "#A8E6CF", "Step 2": "#B4D7FF", "Step 3": "#FFD699"}
    case_markers = {"aq": "o", "wind": "s", "soil": "^", "th": "D"}

    fig, ax = plt.subplots(figsize=(18, 7))

    # Bar width and spacing - thicker bars for visibility
    bar_width = 0.10
    gap_between_bars = 0.01
    gap_between_groups = 0.1
    group_width = n_cases * bar_width + (n_cases - 1) * gap_between_bars + gap_between_groups
    
    # Pre-compute totals for each (model, case)
    totals = {(m, c): 0 for m in all_models for c in CASES}
    
    # Draw bars: iterate by step (bottom to top stacking)
    for step in step_files.keys():
        for case_idx, case in enumerate(CASES):
            heights = []
            x_vals = []
            bottoms = []
            for model_idx, model in enumerate(all_models):
                row = df_combined[
                    (df_combined["model_key"] == model) &
                    (df_combined["case"] == case) &
                    (df_combined["step"] == step)
                ]
                h = row["prompt_tps_unified"].sum() if not row.empty else 0
                heights.append(h)
                # Position: model_group_start + case_offset
                x_val = model_idx * group_width + case_idx * (bar_width + gap_between_bars)
                x_vals.append(x_val)
                bottoms.append(totals[(model, case)])
            
            ax.bar(
                x_vals,
                heights,
                bar_width,
                bottom=bottoms,
                color=step_colors[step],
                edgecolor="black",
                linewidth=0.1,
                label=step if case_idx == 0 else "",
            )
            
            # Update totals
            for model_idx, model in enumerate(all_models):
                totals[(model, case)] += heights[model_idx]

    # Add symbols above each bar (consistent offset)
    max_total = max(totals.values()) if totals else 0
    marker_offset = max(0.02 * max_total, 1)
    for model_idx, model in enumerate(all_models):
        for case_idx, case in enumerate(CASES):
            total_h = totals[(model, case)]
            if total_h > 0:
                x_val = model_idx * group_width + case_idx * (bar_width + gap_between_bars)
                ax.plot(
                    x_val,
                    total_h + marker_offset,
                    marker=case_markers[case],
                    color=CASE_COLORS[case],
                    markersize=8,
                    linestyle="None",
                    markeredgecolor="black",
                    markeredgewidth=0.5,
                )

    # Set x-axis: one label per model, centered on its group of 4 bars
    group_center_offset = (n_cases - 1) * (bar_width + gap_between_bars) / 2
    x_tick_positions = [m * group_width + group_center_offset for m in range(n_models)]
    ax.set_xticks(x_tick_positions)
    ax.set_xticklabels([model_display.get(m, m) for m in all_models], rotation=45, ha="right", fontsize=20)

    last_model_idx = n_models - 1
    last_case_idx = n_cases - 1
    last_bar_center = last_model_idx * group_width + last_case_idx * (bar_width + gap_between_bars)
    edge_padding = 0.05
    left_edge = -bar_width / 2 - edge_padding
    right_edge = last_bar_center + bar_width / 2 + edge_padding
    ax.set_xlim(left_edge, right_edge)

    ax.set_xlabel("Models", fontsize=20)
    ax.set_ylabel("Prompt Tokens Per Second", fontsize=20)
    ax.set_title("Prompt Tokens Per Second by Steps for Four Use Case", fontsize=20, fontweight="bold")
    ax.tick_params(axis="y", labelsize=16)

    # Create legends for steps and cases
    step_handles = [Patch(facecolor=step_colors[step], edgecolor="black", label=step) for step in step_files.keys()]
    case_handles = [
        plt.Line2D([0], [0], marker=case_markers[case], color=CASE_COLORS[case], label=case.upper(), linestyle="None", markersize=8, markeredgecolor="black", markeredgewidth=0.5)
        for case in CASES
    ]
    ax.legend(handles=case_handles + step_handles, fontsize=12, loc="upper left", ncol=2, title="Legend")

    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "stacked_prompt_tps.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_combined_completion_tps():
    """Plot stacked bar chart for completion tokens per second: one model with 4 bars (one per case), each stacked by steps (1-3 only)."""
    # Load metrics for steps 1, 2, 3 only
    step_files = {
        "Step 1": "step1_rpi4_rpi5_perf_metric_{case}.csv",
        "Step 2": "step2_rpi4_rpi5_metric_{case}.csv",
        "Step 3": "step3_rpi4_rpi5_metric_{case}.csv",
    }

    df_list = []
    for step, filename_template in step_files.items():
        for case in CASES:
            path = _case_path(filename_template, case)
            if os.path.exists(path):
                df = pd.read_csv(path)
                df["case"] = case
                df["step"] = step
                df["model"] = df["model"].str.strip()
                df_list.append(df)

    if not df_list:
        return

    df_combined = pd.concat(df_list, ignore_index=True)

    # Normalize model names to prevent duplicates caused by whitespace/quotes/case
    df_combined["model"] = (
        df_combined["model"]
        .astype(str)
        .str.strip()
        .str.strip('"')
        .str.strip("'")
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(":", "_", regex=False) 
        .str.replace("-", "_", regex=False)
    )
    df_combined["model_key"] = df_combined["model"].str.lower()

    # Preserve a clean display label per normalized key
    model_display = (
        df_combined
        .drop_duplicates(subset=["model_key"])
        .set_index("model_key")["model"]
        .to_dict()
    )

    # Build a unified completion_tps column per step
    step_tps_column = {
        "Step 1": "completion_tokens_per_sec",
        "Step 2": "completion_tps",
        "Step 3": "completion_tps",
    }
    df_combined["completion_tps_unified"] = np.nan
    for step, col in step_tps_column.items():
        if col in df_combined.columns:
            mask = df_combined["step"] == step
            df_combined.loc[mask, "completion_tps_unified"] = pd.to_numeric(df_combined.loc[mask, col], errors="coerce")

    # Aggregate once to avoid accidental duplicates
    df_combined = (
        df_combined
        .groupby(["model_key", "case", "step"], as_index=False)["completion_tps_unified"]
        .mean()
    )

    # Get unique models and move 'codellama_7b' to the front
    all_models = sorted(df_combined["model_key"].unique())
    if "codellama_7b" in all_models:
        all_models.remove("codellama_7b")
        all_models.insert(0, "codellama_7b")

    n_models = len(all_models)
    n_cases = len(CASES)

    # Define colors for steps and markers for cases
    step_colors = {"Step 1": "#A8E6CF", "Step 2": "#B4D7FF", "Step 3": "#FFD699"}
    case_markers = {"aq": "o", "wind": "s", "soil": "^", "th": "D"}

    fig, ax = plt.subplots(figsize=(18, 7))

    # Bar width and spacing - thicker bars for visibility
    bar_width = 0.10
    gap_between_bars = 0.01
    gap_between_groups = 0.1
    group_width = n_cases * bar_width + (n_cases - 1) * gap_between_bars + gap_between_groups
    
    # Pre-compute totals for each (model, case)
    totals = {(m, c): 0 for m in all_models for c in CASES}
    
    # Draw bars: iterate by step (bottom to top stacking)
    for step in step_files.keys():
        for case_idx, case in enumerate(CASES):
            heights = []
            x_vals = []
            bottoms = []
            for model_idx, model in enumerate(all_models):
                row = df_combined[
                    (df_combined["model_key"] == model) &
                    (df_combined["case"] == case) &
                    (df_combined["step"] == step)
                ]
                h = row["completion_tps_unified"].sum() if not row.empty else 0
                heights.append(h)
                # Position: model_group_start + case_offset
                x_val = model_idx * group_width + case_idx * (bar_width + gap_between_bars)
                x_vals.append(x_val)
                bottoms.append(totals[(model, case)])
            
            ax.bar(
                x_vals,
                heights,
                bar_width,
                bottom=bottoms,
                color=step_colors[step],
                edgecolor="black",
                linewidth=0.1,
                label=step if case_idx == 0 else "",
            )
            
            # Update totals
            for model_idx, model in enumerate(all_models):
                totals[(model, case)] += heights[model_idx]

    # Add symbols above each bar (consistent offset)
    max_total = max(totals.values()) if totals else 0
    marker_offset = max(0.02 * max_total, 1)
    for model_idx, model in enumerate(all_models):
        for case_idx, case in enumerate(CASES):
            total_h = totals[(model, case)]
            if total_h > 0:
                x_val = model_idx * group_width + case_idx * (bar_width + gap_between_bars)
                ax.plot(
                    x_val,
                    total_h + marker_offset,
                    marker=case_markers[case],
                    color=CASE_COLORS[case],
                    markersize=8,
                    linestyle="None",
                    markeredgecolor="black",
                    markeredgewidth=0.5,
                )

    # Set x-axis: one label per model, centered on its group of 4 bars
    group_center_offset = (n_cases - 1) * (bar_width + gap_between_bars) / 2
    x_tick_positions = [m * group_width + group_center_offset for m in range(n_models)]
    ax.set_xticks(x_tick_positions)
    ax.set_xticklabels([model_display.get(m, m) for m in all_models], rotation=45, ha="right", fontsize=20)

    last_model_idx = n_models - 1
    last_case_idx = n_cases - 1
    last_bar_center = last_model_idx * group_width + last_case_idx * (bar_width + gap_between_bars)
    edge_padding = 0.05
    left_edge = -bar_width / 2 - edge_padding
    right_edge = last_bar_center + bar_width / 2 + edge_padding
    ax.set_xlim(left_edge, right_edge)

    ax.set_xlabel("Models", fontsize=20)
    ax.set_ylabel("Completion Tokens Per Second", fontsize=20)
    ax.set_title("Completion Tokens Per Second by Steps for Four Use Cases", fontsize=20, fontweight="bold")
    ax.tick_params(axis="y", labelsize=16)

    # Create legends for steps and cases
    step_handles = [Patch(facecolor=step_colors[step], edgecolor="black", label=step) for step in step_files.keys()]
    case_handles = [
        plt.Line2D([0], [0], marker=case_markers[case], color=CASE_COLORS[case], label=case.upper(), linestyle="None", markersize=8, markeredgecolor="black", markeredgewidth=0.5)
        for case in CASES
    ]
    ax.legend(handles=case_handles + step_handles, fontsize=12, loc="upper left", ncol=2, title="Legend")

    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "stacked_completion_tps.pdf"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(RESULT_DIR, exist_ok=True)
    print("Generating combined plots...")
    
    #plot_step4_success()
    print("✓ Step4 success rate")
    #plot_step4_execution_outcome()
    print("✓ Step4 execution outcome")
    #plot_avg_cpu()
    print("✓ Average CPU")
    #plot_avg_memory()
    print("✓ Average Memory")
    #plot_validation_success_grouped()
    print("✓ Grouped validation success rate")
    #plot_complete_pipeline_grouped()
    print("✓ Grouped complete pipeline")
    #plot_combined_duration_metrics()
    print("✓ Combined duration metrics")
    plot_combined_prompt_tps()
    print("✓ Combined prompt tokens per second")
    plot_combined_completion_tps()
    print("✓ Combined completion tokens per second")

    print(f"\nAll combined images saved to {RESULT_DIR}/")

if __name__ == "__main__":
    main()
