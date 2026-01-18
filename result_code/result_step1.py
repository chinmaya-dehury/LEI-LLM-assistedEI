import os
import glob
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# =========================
# CONFIGURATION
# =========================
# Path patterns to match your summary CSV files from both RPi4 and RPi5 (excluding resource_*)
# Combine data from both Rpi4 and Pi5
INPUT_FILE_PATTERNS = [
    "Rpi4 Updated Data/Wind/timestamp_path/wind/step1_*.csv",
    "Rpi5 Updated Data/Wind/timestamp_path/wind/step1_*.csv"
]

# Output filename for the aggregated metrics
OUTPUT_CSV = "step1_rpi4_rpi5_perf_metric_wind.csv"

# Plot styling
sns.set_theme(style="whitegrid", context="talk")

def load_data(file_patterns):
    """
    Loads all matching step1 CSVs from multiple file patterns (RPi4 and RPi5),
    excluding the 'resource' time-series files.
    """
    all_files = []
    for pattern in file_patterns:
        all_files.extend(glob.glob(pattern))
    
    # Filter: Exclude files that have 'resource' in the name (unless it's the only type available)
    # We specifically want the files containing 'prompt_tokens', 'llm_duration_sec', etc.
    summary_files = [f for f in all_files if "resource" not in os.path.basename(f)]
    
    if not summary_files:
        print("No summary files found. Looking for 'step1_MODEL_timestamp.csv' type files.")
        return pd.DataFrame()
        
    print(f"Processing {len(summary_files)} summary files from RPi4 and RPi5...")
    
    dfs = []
    for f in summary_files:
        try:
            df = pd.read_csv(f)
            # Basic validation to ensure it's the correct file type
            if "model" in df.columns and "prompt_tokens" in df.columns:
                # Add source identifier
                if "Rpi4" in f:
                    df["device"] = "RPi4"
                elif "Rpi5" in f:
                    df["device"] = "RPi5"
                dfs.append(df)
            else:
                print(f"Skipping {f}: Missing 'model' or 'prompt_tokens' columns.")
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not dfs:
        return pd.DataFrame()
        
    return pd.concat(dfs, ignore_index=True)

def aggregate_metrics(df):
    """
    Aggregates metrics by model.
    """
    # Define aggregation dictionary - only include columns that exist in CSV
    agg_rules = {
        'prompt_tokens': 'mean',
        'completion_tokens': 'mean',
        'total_tokens': 'mean',
        'llm_duration_sec': 'mean',
        'prompt_tokens_per_sec': 'mean',
        'completion_tokens_per_sec': 'mean',
        'run_count': 'count'
    }
    
    # Group and aggregate
    agg_df = df.groupby('model').agg(agg_rules).reset_index()
    
    # Rename columns for clarity
    agg_df = agg_df.rename(columns={
        'prompt_tokens': 'avg_input_tokens',
        'completion_tokens': 'avg_output_tokens',
        'total_tokens': 'avg_total_tokens',
        'llm_duration_sec': 'avg_duration_sec'
    })
    
    # Calculate Efficiency Score (Total Tokens / Duration)
    agg_df['efficiency_score'] = agg_df.apply(
        lambda x: (x['avg_total_tokens'] / x['avg_duration_sec']) if x['avg_duration_sec'] > 0 else 0, 
        axis=1
    )
    
    return agg_df

def generate_plots(agg_df, raw_df):
    """
    Generates the requested visualizations.
    """
    if agg_df.empty:
        print("No data available for plotting.")
        return

    # -------------------------------------------------------
    # 1. Stacked Bar Graph: Input vs Completion Tokens
    # -------------------------------------------------------
    plt.figure(figsize=(12, 7))
    
    # Create the bottom bars (Input Tokens)
    p1 = plt.bar(agg_df['model'], agg_df['avg_input_tokens'], label='Input (Prompt) Tokens', color='#4C72B0')
    
    # Create the top bars (Completion Tokens), stacked on input
    p2 = plt.bar(agg_df['model'], agg_df['avg_output_tokens'], bottom=agg_df['avg_input_tokens'], label='Output (Completion) Tokens', color='#DD8452')
    
    plt.title('Average Token Distribution per Model (Input vs Output)')
    plt.ylabel('Token Count')
    plt.xlabel('Model')
    plt.xticks(rotation=45)
    plt.legend()
    
    # Add labels on the stacked bars
    for bar in p1:
        height = bar.get_height()
        if height > 0:
            plt.text(bar.get_x() + bar.get_width()/2., height/2., f'{int(height)}', ha='center', va='center', color='white', fontsize=10)
            
    for bar_bottom, bar_top in zip(p1, p2):
        height = bar_top.get_height()
        bottom = bar_bottom.get_height()
        if height > 0:
            plt.text(bar_top.get_x() + bar_top.get_width()/2., bottom + height/2., f'{int(height)}', ha='center', va='center', color='white', fontsize=10)

    plt.tight_layout()
    plt.savefig("step1_plot_tokens_stacked_wind.png")
    plt.close()

    # -------------------------------------------------------
    # 2. Grouped Bar: Average Duration per Model
    # -------------------------------------------------------
    plt.figure(figsize=(12, 6))
    sns.barplot(data=agg_df, x='model', y='avg_duration_sec', hue='model', palette='Set2', legend=False)
    plt.title('Average LLM Duration per Model')
    plt.ylabel('Duration (seconds)')
    plt.xlabel('Model')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("step1_plot_duration_comparison_wind.png")
    plt.close()

    # -------------------------------------------------------
    # 3. Throughput (Tokens/Sec) Comparison
    # -------------------------------------------------------
    plt.figure(figsize=(12, 6))
    sns.barplot(data=agg_df, x='model', y='completion_tokens_per_sec', hue='model', palette='viridis', legend=False)
    plt.title('Average Generation Speed (Output Tokens/Sec)')
    plt.ylabel('Tokens / Second')
    plt.xlabel('Model')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("step1_plot_throughput_wind.png")
    plt.close()

# =========================
# MAIN EXECUTION
# =========================
if __name__ == "__main__":
    # 1. Load Data
    raw_df = load_data(INPUT_FILE_PATTERNS)
    
    if not raw_df.empty:
        # 2. Aggregate
        agg_df = aggregate_metrics(raw_df)
        
        print("\n=== Model Performance Summary ===")
        print(agg_df.round(2).T) # Transposed for easier reading in terminal
        
        # 3. Save Metrics
        agg_df.to_csv(OUTPUT_CSV, index=False)
        print(f"\nDetailed metrics saved to: {OUTPUT_CSV}")
        
        # 4. Generate Plots
        generate_plots(agg_df, raw_df)
    else:
        print("No valid data found to process.")