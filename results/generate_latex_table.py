import os
import glob
import pandas as pd

def format_metric(s):
    # s is a Series
    med = s.median()
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    return f"{med:.1f} [{q1:.1f}, {q3:.1f}]"

def main():
    search_pattern = os.path.join("*", "benchmark_results_triple.csv")
    csv_files = glob.glob(search_pattern)
    
    if not csv_files:
        print("No CSV files found.")
        return
        
    all_data = []
    for f in csv_files:
        df = pd.read_csv(f)
        all_data.append(df)
        
    df_all = pd.concat(all_data, ignore_index=True)
    df_all['framework'] = df_all['framework'].str.strip()
    
    metrics = {
        'lei_time_up_to_codegen': 'Up to Code Gen',
        'lei_time_val': 'Validation',
        'elapsed_time_sec': 'Total',
        'avg_cpu_percent': 'CPU (%)',
        'avg_memory_mb': 'Mem (MB)'
    }
    
    grouped = df_all.groupby(['framework', 'dataset'])
    
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\begin{tabular}{l l c c c c c}")
    print(r"\toprule")
    print(r"& & \multicolumn{3}{c}{Latency (s)} & \multicolumn{2}{c}{Resource Footprint} \\")
    print(r"\cmidrule(lr){3-5} \cmidrule(lr){6-7}")
    print(r"Framework & Dataset & Up to Code Gen & Validation & Total & CPU (\%) & Mem (MB) \\")
    print(r"\midrule")
    
    # Sort frameworks so LEI is first, etc.
    for fw in ["LEI", "AutoGen", "LangGraph"]:
        datasets = sorted(df_all[df_all['framework'] == fw]['dataset'].unique())
        for i, ds in enumerate(datasets):
            group = df_all[(df_all['framework'] == fw) & (df_all['dataset'] == ds)]
            if group.empty: continue
            
            t_codegen = format_metric(group['lei_time_up_to_codegen'])
            t_val = format_metric(group['lei_time_val'])
            t_total = format_metric(group['elapsed_time_sec'])
            r_cpu = format_metric(group['avg_cpu_percent'])
            r_mem = format_metric(group['avg_memory_mb'])
            
            fw_col = fw if i == 0 else ""
            print(f"{fw_col} & {ds} & {t_codegen} & {t_val} & {t_total} & {r_cpu} & {r_mem} \\\\")
            
        print(r"\midrule")
        
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\caption{Resource Utilization and Latency across Frameworks (Median [Q1, Q3])}")
    print(r"\end{table}")

if __name__ == "__main__":
    main()
