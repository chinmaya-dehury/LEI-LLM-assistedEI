import os
import pandas as pd

def generate_latex_table(csv_path, output_tex_path):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} does not exist. Run collate_results.py first.")
        return
        
    df = pd.read_csv(csv_path)
    
    # Map steps to Table 8 steps
    step_map = {
        'task_generator': 'Step 1',
        'code_generator': 'Step 2',
        'validator': 'Step 3'
    }
    
    # Filter only relevant steps
    df = df[df['step'].isin(step_map.keys())].copy()
    df['step_label'] = df['step'].map(step_map)
    
    # Clean up model names to get M1, M2... mappings if needed
    models = sorted(df['model_name'].unique())
    model_mapping = {m: f"M{i+1}" for i, m in enumerate(models)}
    
    # Clean up dataset names to get D1, D2... mappings if needed
    datasets = sorted(df['dataset'].unique())
    dataset_mapping = {d: f"D{i+1}" for i, d in enumerate(datasets)}
    
    df['M'] = df['model_name'].map(model_mapping)
    df['D'] = df['dataset'].map(dataset_mapping)
    
    # We will pivot by step to get them as columns
    # We need Avg CPU and Avg Mem for each step
    pivot_data = {}
    
    for idx, row in df.iterrows():
        key = (row['M'], row['D'], row['model_name'], row['dataset'])
        if key not in pivot_data:
            pivot_data[key] = {
                'Step 1_cpu': "N/A", 'Step 1_mem': "N/A",
                'Step 2_cpu': "N/A", 'Step 2_mem': "N/A",
                'Step 3_cpu': "N/A", 'Step 3_mem': "N/A"
            }
        
        step_lbl = row['step_label']
        cpu_val = f"{row['avg_cpu_percent_median']:.2f} \\pm {row['avg_cpu_percent_iqr']:.2f}"
        mem_val = f"{row['avg_memory_mb_median']:.2f} \\pm {row['avg_memory_mb_iqr']:.2f}"
        
        pivot_data[key][f"{step_lbl}_cpu"] = cpu_val
        pivot_data[key][f"{step_lbl}_mem"] = mem_val
        
    # Convert pivot to list
    rows_list = []
    for (m_code, d_code, model, dataset), steps in pivot_data.items():
        rows_list.append({
            'M_code': m_code,
            'D_code': d_code,
            'Model': model,
            'Dataset': dataset,
            **steps
        })
        
    df_pivot = pd.DataFrame(rows_list).sort_values(by=['M_code', 'D_code'])
    
    # Write LaTeX Table
    tex = []
    tex.append(r"\begin{table*}[t]")
    tex.append(r"\centering")
    tex.append(r"\caption{CPU and Memory Footprint across Steps 1, 2, and 3 on edge devices (Median $\pm$ IQR)}")
    tex.append(r"\begin{tabular}{llcccccc}")
    tex.append(r"\hline")
    tex.append(r" & & \multicolumn{2}{c}{Step 1 (Task Generator)} & \multicolumn{2}{c}{Step 2 (Code Generator)} & \multicolumn{2}{c}{Step 3 (Validator)} \\")
    tex.append(r"\cline{3-8}")
    tex.append(r"M & D & Avg CPU (\%) & Avg Mem (MB) & Avg CPU (\%) & Avg Mem (MB) & Avg CPU (\%) & Avg Mem (MB) \\")
    tex.append(r"\hline")
    
    current_m = None
    for idx, row in df_pivot.iterrows():
        # Clean print format
        m_val = row['M_code'] if row['M_code'] != current_m else ""
        current_m = row['M_code']
        
        tex.append(f"{m_val} & {row['D_code']} & {row['Step 1_cpu']} & {row['Step 1_mem']} & {row['Step 2_cpu']} & {row['Step 2_mem']} & {row['Step 3_cpu']} & {row['Step 3_mem']} \\\\")
        
    tex.append(r"\hline")
    tex.append(r"\end{tabular}")
    tex.append(r"\label{tab:cpu_mem_footprint}")
    tex.append(r"\end{table*}")
    
    # Also add Legend mapping for clarity
    tex.append("\n\n% Model Mapping Legend:")
    for k, v in model_mapping.items():
        tex.append(f"% {v}: {k}")
    tex.append("% Dataset Mapping Legend:")
    for k, v in dataset_mapping.items():
        tex.append(f"% {v}: {k}")
        
    with open(output_tex_path, 'w') as f:
        f.write('\n'.join(tex))
        
    print(f"LaTeX Table successfully written to {output_tex_path}")

if __name__ == "__main__":
    csv_file = os.path.join(os.path.dirname(__file__), "1_cpu_memory_usage.csv")
    output_tex = os.path.join(os.path.dirname(__file__), "table_cpu_mem_iqr.tex")
    generate_latex_table(csv_file, output_tex)
