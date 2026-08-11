import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def make_ranges(values, step, clamp_max=None):
    max_value = float(values.max()) if len(values) else 0.0
    if max_value == 0:
        return [0, step], [f"0-{step}"]
    
    bins = [0]
    labels = []
    current = 0.0
    precision = 1 if step < 1 else 0
    
    while current < (clamp_max if clamp_max else max_value):
        next_edge = current + step
        bins.append(next_edge)
        if precision == 0:
            labels.append(f"{int(current)}-{int(next_edge)}")
        else:
            labels.append(f"{current:.{precision}f}-{next_edge:.{precision}f}")
        current = next_edge
        
    if clamp_max and max_value > clamp_max:
        bins.append(float('inf'))
        labels.append(f">{int(clamp_max)}")
        
    return bins, labels

def plot_range_bars(ax, values, bins, labels, title, xlabel, ylabel, color, bar_width=0.6):
    counts = pd.cut(values, bins=bins, labels=labels, include_lowest=True).value_counts().reindex(labels).fillna(0)
    bars = ax.bar(labels, counts, width=bar_width, color=color, edgecolor="black", alpha=0.85)
    total = len(values)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=12, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=12, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=14)
    ax.tick_params(axis='y', labelsize=14)
    
    max_count = max(float(counts.max()), 1.0)
    ax.set_ylim(0, max_count + max(2, int(max_count * 0.2)))
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            pct = (height / total * 100) if total else 0
            if pct >= 1.0:
                label_text = f"{int(height)}\n({pct:.1f}%)"
            else:
                label_text = f"{int(height)}\n(<1%)"
            
            ax.text(bar.get_x() + bar.get_width() / 2., height + max_count * 0.02, label_text,
                    ha="center", va="bottom", rotation=90, fontsize=9, fontweight="bold")
    return counts

def main():
    parser = argparse.ArgumentParser(description="Plot resource usage distributions.")
    parser.add_argument("--csv", default="resource_usage_with_time.csv", help="Path to input CSV file")
    parser.add_argument("--out", default="resource_distribution_counts_4_panels_v6.pdf", help="Path to output PDF")
    args = parser.parse_args()

    # Load Raw Data
    df = pd.read_csv(args.csv)
    
    # Remove unknown dataset
    df = df[df["dataset"].notna()]
    df = df[~df["dataset"].str.lower().str.contains("unknown")]
    
    for col in ["peak_cpu", "peak_mem", "exec_time", "median_cpu", "median_mem"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    axes = axes.flatten()

    cpu_bins, cpu_labels = make_ranges(df["peak_cpu"], step=5)
    mem_bins, mem_labels = make_ranges(df["peak_mem"], step=100)
    time_bins, time_labels = make_ranges(df["exec_time"], step=10, clamp_max=60)

    cpu_counts = plot_range_bars(
        axes[0], df["peak_cpu"], cpu_bins, cpu_labels,
        f"A. Peak CPU Usage Distribution (n={len(df)})", "Peak CPU Usage (%)", "Scripts Count", "#2b5c8f", bar_width=0.6
    )

    mem_counts = plot_range_bars(
        axes[1], df["peak_mem"], mem_bins, mem_labels,
        f"B. Peak Memory Usage Distribution (n={len(df)})", "Peak Memory Usage (MB)", "Scripts Count", "#d95f02", bar_width=0.6
    )

    time_counts = plot_range_bars(
        axes[2], df["exec_time"], time_bins, time_labels,
        f"C. Execution Time Distribution (n={len(df)})", "Execution Time (s)", "Scripts Count", "#7570b3", bar_width=0.6
    )

    # D. Dataset-wise Stacked CPU
    ax4 = axes[3]
    grouped = df.groupby("dataset")[["median_cpu", "peak_cpu"]].median()
    
    x = np.arange(len(grouped))
    width = 0.5
    
    # Stacked CPU with contrasting colors
    med_cpu = grouped["median_cpu"]
    diff_cpu = grouped["peak_cpu"] - med_cpu
    bar1 = ax4.bar(x, med_cpu, width, label="Median CPU (%)", color="#2b5c8f", edgecolor="black")
    bar2 = ax4.bar(x, diff_cpu, width, bottom=med_cpu, label="Peak CPU Diff", color="#d95f02", edgecolor="black")
    
    ax4.set_title("D. Median vs Peak CPU Usage by Dataset", fontsize=12, fontweight="bold")
    ax4.set_ylabel("Peak CPU Usage (%)", fontsize=12, fontweight="bold")
    ax4.set_xlabel("Dataset", fontsize=12, fontweight="bold")
    ax4.set_xticks(x)
    ax4.set_xticklabels(grouped.index, rotation=0, ha="center", fontsize=14)
    ax4.tick_params(axis='y', labelsize=14)
    ax4.set_yticks(range(0, 70, 10))
    ax4.set_ylim(0, 60)
    ax4.legend(loc="upper left", fontsize=9)
    ax4.grid(axis="y", linestyle="--", alpha=0.5)

    # Add text labels on the bars (Peak values at the top)
    for i, peak in enumerate(grouped["peak_cpu"]):
        ax4.text(i, peak + 1, f"{peak:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold', rotation=90)

    plt.tight_layout()
    plt.savefig(args.out, format='pdf', dpi=600, bbox_inches='tight')
    plt.close()

    print(f"\nSaved combined 4-subplot PDF to: {args.out}")

if __name__ == "__main__":
    main()