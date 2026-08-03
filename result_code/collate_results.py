import os
import json
import glob
import re
import pandas as pd
import numpy as np
from datetime import datetime

import argparse

parser = argparse.ArgumentParser(description="Collate LEI benchmark results.")
parser.add_argument("--input_dir", type=str, required=True, help="Path to the result directory containing runs.")
parser.add_argument("--output_dir", type=str, required=True, help="Path to write aggregated CSVs.")
args = parser.parse_args()

out_dir = args.output_dir
os.makedirs(out_dir, exist_ok=True)

local_base = args.input_dir

def find_matching_session(row_time_str, session_timestamps):
    if not session_timestamps:
        return None
    try:
        clean_str = row_time_str.split("+")[0].split(".")[0].replace("T", " ")
        row_dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

    best_session = None
    min_diff = None

    for sess in session_timestamps:
        try:
            sess_dt = datetime.strptime(sess, "%Y%m%d_%H%M%S")
            diff = abs((row_dt - sess_dt).total_seconds())
            if min_diff is None or diff < min_diff:
                min_diff = diff
                best_session = sess
        except Exception:
            pass

    return best_session

def get_median_iqr(values):
    vals = [v for v in values if v is not None and not np.isnan(v)]
    if not vals:
        return 0.0, 0.0, 0.0
    median = float(np.median(vals))
    if len(vals) > 1:
        q75, q25 = np.percentile(vals, [75, 25])
        return median, float(q25), float(q75)
    else:
        return median, 0.0, 0.0

def get_scheduler_success_count(folder_path, filename_model, run_count, scheduler_start_time_iso):
    if not scheduler_start_time_iso:
        return 0, None
    try:
        clean_str = scheduler_start_time_iso.split("+")[0].split(".")[0].replace("T", " ")
        sched_dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return 0, None
        
    log_dir = os.path.join(folder_path, "logs")
    if not os.path.exists(log_dir):
        return 0, None
        
    log_pattern = os.path.join(log_dir, f"edge_execution_{filename_model}_run{run_count}_*.log")
    log_files = glob.glob(log_pattern)
    
    best_log = None
    min_diff = None
    
    for f in log_files:
        match = re.search(r"(\d{8}_\d{6})\.log$", f)
        if match:
            sess_str = match.group(1)
            try:
                sess_dt = datetime.strptime(sess_str, "%Y%m%d_%H%M%S")
                diff = abs((sched_dt - sess_dt).total_seconds())
                if min_diff is None or diff < min_diff:
                    min_diff = diff
                    best_log = f
            except Exception:
                pass
                
    if best_log and min_diff < 300: # within 5 minutes
        try:
            with open(best_log, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            match_succ = re.search(r"Successful:\s*(\d+)", content)
            if match_succ:
                return int(match_succ.group(1)), os.path.basename(best_log)
            return 0, os.path.basename(best_log)
        except Exception as e:
            print(f"      Error parsing log file {best_log}: {e}")
            return 0, os.path.basename(best_log)
            
    return 0, None

def round_dataframe(df):
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass
        if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
            if pd.api.types.is_float_dtype(df[col]):
                if "success_rate" in col or col.endswith("_rate") or col.endswith("_rate_median") or col.endswith("_rate_iqr"):
                    df[col] = df[col].round(4)
                else:
                    df[col] = df[col].round(2)
    return df

def collate_folder(folder_path, folder_name):
    print(f"\nScanning directory: {folder_path}")
    
    bench_models = []
    bench_csvs = [os.path.join(folder_path, 'results', 'benchmark_results_v3.csv')]
    bench_csvs.extend(glob.glob(os.path.join(folder_path, 'benchmark_results_v3*.csv')))
    
    for csv_p in bench_csvs:
        if os.path.exists(csv_p):
            try:
                df = pd.read_csv(csv_p)
                if 'model' in df.columns:
                    bench_models.extend(df['model'].dropna().unique())
            except Exception:
                pass
    bench_models = list(set(bench_models))
            
    # Find unique model/dataset/sessions in this folder
    keys = set() # set of (filename_model, dataset, session_timestamp)
    
    # Scan validator
    val_dir = os.path.join(folder_path, "validator")
    if os.path.exists(val_dir):
        for ds in os.listdir(val_dir):
            ds_path = os.path.join(val_dir, ds)
            if os.path.isdir(ds_path):
                for f in os.listdir(ds_path):
                    match = re.search(r'val_sum_(.+?)_(\d{8}_\d{6})', f)
                    if match:
                        keys.add((match.group(1), ds, match.group(2)))
                        
    # Scan timestamp_path
    ts_dir = os.path.join(folder_path, "timestamp_path")
    if os.path.exists(ts_dir):
        for ds in os.listdir(ts_dir):
            ds_path = os.path.join(ts_dir, ds)
            if os.path.isdir(ds_path):
                for f in os.listdir(ds_path):
                    match = re.search(r'step\d+_(?:resource_)?(.+?)_lei_v3_bench_(\d{8}_\d{6})', f)
                    if match:
                        keys.add((match.group(1), ds, match.group(2)))
                    # Alternate naming structure used in local repository
                    match_local = re.search(r'step\d+_(.+?)_(\d{8}_\d{6})', f)
                    if match_local and not f.startswith("step3_") and not f.startswith("step4_"):
                        # Ensure we don't accidentally match resource files
                        if "resource" not in f:
                            keys.add((match_local.group(1), ds, match_local.group(2)))

    discovered_runs = []
    for fm, ds, sess in sorted(list(keys)):
        reported = fm
        if bench_models:
            fm_clean = fm.lower().replace('-', '')
            matched = [bm for bm in bench_models if fm_clean in bm.lower().replace('-', '')]
            if matched:
                reported = matched[0]
            
        discovered_runs.append({
            'folder': folder_name,
            'filename_model': fm,
            'reported_model': reported,
            'dataset': ds,
            'session': sess
        })

    return discovered_runs, bench_csvs

def main():
    all_discovered = []
    folder_paths = {}
    
    # Check if local directory has runs
    local_runs, local_csvs = collate_folder(local_base, "local_run")
    if local_runs:
        all_discovered.extend(local_runs)
        folder_paths["local_run"] = local_base

    if not all_discovered:
        print("No validation runs or timestamps discovered in the local project directory.")
        return

    df_discovered = pd.DataFrame(all_discovered)
    # Group runs to assign run index
    df_unique_runs = df_discovered[['reported_model', 'folder', 'session']].drop_duplicates().copy()
    df_unique_runs['session_dt'] = pd.to_datetime(df_unique_runs['session'], format='%Y%m%d_%H%M%S', errors='coerce')
    df_unique_runs = df_unique_runs.sort_values(by=['reported_model', 'folder', 'session_dt'])
    df_unique_runs['run_idx'] = df_unique_runs.groupby('reported_model').cumcount() + 1
    df_unique_runs['total_runs'] = df_unique_runs.groupby('reported_model')['reported_model'].transform('count')

    df_discovered = df_discovered.merge(
        df_unique_runs[['reported_model', 'folder', 'session', 'run_idx', 'total_runs']], 
        on=['reported_model', 'folder', 'session'], how='left'
    )

    master_step_rows = []
    master_run_rows = []
    run_mapping_rows = []

    run_groups = df_discovered.groupby(['folder', 'filename_model', 'reported_model', 'session', 'run_idx', 'total_runs'])
    
    # We will support up to 10 runs per model group
    run_keys = [str(i) for i in range(1, 11)]

    for (folder, filename_model, reported_model, sess, run_idx, total_runs), group in run_groups:
        folder_path = folder_paths[folder]
        print(f"Processing Model: {reported_model} (Run {run_idx}/{total_runs}), Session: {sess}")
        
        # Load benchmark results
        df_bench = pd.DataFrame()
        bench_csvs = [os.path.join(folder_path, "results", "benchmark_results_v3.csv")]
        bench_csvs.extend(glob.glob(os.path.join(folder_path, "benchmark_results_v3*.csv")))
        dfs = []
        for csv_p in bench_csvs:
            if os.path.exists(csv_p):
                try:
                    df_full_bench = pd.read_csv(csv_p)
                    dfs.append(df_full_bench)
                except Exception:
                    pass
        if dfs:
            df_all_bench = pd.concat(dfs, ignore_index=True)
            fm_clean = filename_model.lower().replace('-', '')
            matching_models = [m for m in (df_all_bench['gen_model'] if 'gen_model' in df_all_bench else df_all_bench['model']).dropna().unique() if fm_clean in m.lower().replace('-', '')]
            if matching_models:
                df_bench = df_all_bench[(df_all_bench['gen_model'] if 'gen_model' in df_all_bench else df_all_bench['model']) == matching_models[0]]
            else:
                df_bench = pd.DataFrame()
                
        model_name_display = f"{reported_model} (Run {run_idx})" if total_runs > 1 else reported_model
        datasets = group['dataset'].unique()
        
        for ds in datasets:
            model_ds_rows = df_discovered[
                (df_discovered['folder'] == folder) & 
                (df_discovered['filename_model'] == filename_model) & 
                (df_discovered['dataset'] == ds)
            ]
            sess_list = sorted(model_ds_rows['session'].unique())
            
            bench_rows = pd.DataFrame()
            if not df_bench.empty:
                ds_bench = df_bench[df_bench["dataset"] == ds]
                if not ds_bench.empty:
                    matched_rows = []
                    for idx, row in ds_bench.iterrows():
                        matched_sess = find_matching_session(row["timestamp"], sess_list)
                        if matched_sess == sess:
                            matched_rows.append(row)
                    if matched_rows:
                        bench_rows = pd.DataFrame(matched_rows)
                        
            run_files = {rk: {'step1': None, 'step2': None, 'step3': None, 'step4': None, 'validator': None, 'scheduler_log': None} for rk in run_keys}
            
            step_metrics = {
                rk: {
                    'step1_latency': None, 'step1_prompt_tokens': None, 'step1_completion_tokens': None,
                    'step2_latency': None, 'step2_prompt_tokens': None, 'step2_completion_tokens': None,
                    'step3_latency': None, 'step3_prompt_tokens': None, 'step3_completion_tokens': None,
                    'step4_latency': None
                } for rk in run_keys
            }
            
            ts_ds_dir = os.path.join(folder_path, "timestamp_path", ds)
            val_ds_dir = os.path.join(folder_path, "validator", ds)
            if os.path.exists(ts_ds_dir):
                # Step 1
                s1_files = [f for f in glob.glob(os.path.join(ts_ds_dir, f"step1_{filename_model}*{sess}.csv")) if "resource" not in os.path.basename(f)]
                if s1_files:
                    try:
                        df1 = pd.read_csv(s1_files[0])
                        for _, row in df1.iterrows():
                            rc = str(int(row['run_count']))
                            if rc in step_metrics:
                                res_l = row.get('script_duration_sec')
                                step_metrics[rc]['step1_latency'] = float(res_l) if pd.notnull(res_l) else None
                                step_metrics[rc]['step1_prompt_tokens'] = float(row.get('prompt_tokens', 0))
                                step_metrics[rc]['step1_completion_tokens'] = float(row.get('completion_tokens', 0))
                                run_files[rc]['step1'] = os.path.basename(s1_files[0])
                    except Exception as e:
                        print(f"      Error reading Step 1 CSV: {e}")
                
                # Step 2
                s2_files = [f for f in glob.glob(os.path.join(ts_ds_dir, f"step2_{filename_model}*{sess}.csv")) if "resource" not in os.path.basename(f)]
                if s2_files:
                    try:
                        df2 = pd.read_csv(s2_files[0])
                        for rc_val, group_s2 in df2.groupby('run_count'):
                            rc = str(int(rc_val))
                            if rc in step_metrics:
                                res_l = group_s2['script_duration_sec'].max()
                                step_metrics[rc]['step2_latency'] = float(res_l) if pd.notnull(res_l) else None
                                step_metrics[rc]['step2_prompt_tokens'] = float(group_s2.get('prompt_tokens', 0).sum())
                                step_metrics[rc]['step2_completion_tokens'] = float(group_s2.get('completion_tokens', 0).sum())
                                run_files[rc]['step2'] = os.path.basename(s2_files[0])
                    except Exception as e:
                        print(f"      Error reading Step 2 CSV: {e}")
                        
                # Step 3
                s3_files = [f for f in glob.glob(os.path.join(ts_ds_dir, f"step3_{filename_model}*{sess}.csv")) if "resource" not in os.path.basename(f)]
                if s3_files:
                    try:
                        df3 = pd.read_csv(s3_files[0])
                        for rc_val, group_s3 in df3.groupby('run_count'):
                            rc = str(int(rc_val))
                            if rc in step_metrics:
                                val_run_rows = group_s3[group_s3['step'] == 'validator_run']
                                if not val_run_rows.empty:
                                    res_l = val_run_rows['script_duration_sec'].values[0]
                                    step_metrics[rc]['step3_latency'] = float(res_l) if pd.notnull(res_l) else None
                                else:
                                    res_l = group_s3['script_duration_sec'].max()
                                    step_metrics[rc]['step3_latency'] = float(res_l) if pd.notnull(res_l) else None
                                
                                llm_calls = group_s3[group_s3['step'] == 'llm_call']
                                step_metrics[rc]['step3_prompt_tokens'] = float(llm_calls.get('prompt_tokens', 0).sum())
                                step_metrics[rc]['step3_completion_tokens'] = float(llm_calls.get('completion_tokens', 0).sum())
                                run_files[rc]['step3'] = os.path.basename(s3_files[0])
                    except Exception as e:
                        print(f"      Error reading Step 3 CSV: {e}")
                        
                # Step 4
                s4_files = glob.glob(os.path.join(ts_ds_dir, f"step4_resource_{filename_model}*{sess}.csv"))
                if s4_files:
                    try:
                        df4 = pd.read_csv(s4_files[0])
                        df4['dt'] = pd.to_datetime(df4['timestamp_ist'])
                        for rc_val, group_s4 in df4.groupby('run_count'):
                            rc = str(int(rc_val))
                            if rc in step_metrics:
                                start_row = group_s4[group_s4['event_type'] == 'start']
                                end_row = group_s4[group_s4['event_type'] == 'end']
                                if not start_row.empty and not end_row.empty:
                                    duration = (pd.to_datetime(end_row['dt'].values[0]) - pd.to_datetime(start_row['dt'].values[0])) / pd.Timedelta(seconds=1)
                                    step_metrics[rc]['step4_latency'] = float(duration)
                                run_files[rc]['step4'] = os.path.basename(s4_files[0])
                    except Exception as e:
                        print(f"      Error reading Step 4 CSV: {e}")

            cpu_mem_by_step_run = {
                'task_generator': {rk: {} for rk in run_keys},
                'code_generator': {rk: {} for rk in run_keys},
                'validator': {rk: {} for rk in run_keys},
                'scheduler': {rk: {} for rk in run_keys}
            }
            
            scheduler_start_times = {rk: None for rk in run_keys}
            
            if not bench_rows.empty:
                for _, row in bench_rows.iterrows():
                    step_name = row['step']
                    rc = str(int(row['run_count']))
                    if rc in run_keys and step_name in cpu_mem_by_step_run:
                        cpu_mem_by_step_run[step_name][rc] = {
                            'avg_cpu_percent': float(row['avg_cpu_percent']),
                            'peak_cpu_percent': float(row['peak_cpu_percent']),
                            'avg_memory_mb': float(row['avg_memory_mb']),
                            'peak_memory_mb': float(row['peak_memory_mb'])
                        }
                        if step_name == 'scheduler':
                            scheduler_start_times[rc] = row['timestamp']
                            
                        step_map = {
                            'task_generator': 'step1_latency',
                            'code_generator': 'step2_latency',
                            'validator': 'step3_latency',
                            'scheduler': 'step4_latency'
                        }
                        latency_key = step_map[step_name]
                        if step_metrics[rc][latency_key] is None:
                            step_metrics[rc][latency_key] = float(row['elapsed_time_sec'])
            else:
                # If bench_rows is empty, try to read resource metrics from local step*_resource_*.csv files
                if os.path.exists(ts_ds_dir):
                    import psutil
                    try:
                        total_mem_mb = psutil.virtual_memory().total / (1024 * 1024)
                    except Exception:
                        total_mem_mb = 16384.0 # default fallback
                    
                    step_res_mappings = {
                        'step1': 'task_generator',
                        'step2': 'code_generator',
                        'step3': 'validator',
                        'step4': 'scheduler'
                    }
                    
                    for step_prefix, step_name in step_res_mappings.items():
                        if step_prefix == 'step3':
                            val_sum_pattern = os.path.join(val_ds_dir, f"val_sum_*_{sess}_all_runs.json")
                            val_sum_files = glob.glob(val_sum_pattern)
                            val_model = None
                            if val_sum_files:
                                m_val = re.search(r'val_sum_(.+?)_' + re.escape(sess), os.path.basename(val_sum_files[0]))
                                if m_val:
                                    val_model = m_val.group(1)
                            if val_model:
                                res_pattern = os.path.join(ts_ds_dir, f"{step_prefix}_resource_{val_model}*{sess}.csv")
                            else:
                                res_pattern = os.path.join(ts_ds_dir, f"{step_prefix}_resource_*{sess}.csv")
                        else:
                            res_pattern = os.path.join(ts_ds_dir, f"{step_prefix}_resource_{filename_model}*{sess}.csv")
                            
                        res_files = glob.glob(res_pattern)
                        if res_files:
                            try:
                                df_res = pd.read_csv(res_files[0])
                                for rc_val, group_res in df_res.groupby('run_count'):
                                    rc = str(int(rc_val))
                                    if rc in run_keys:
                                        cpus = group_res['cpu_percent'].dropna().astype(float).tolist()
                                        mems = group_res['memory_percent'].dropna().astype(float).tolist()
                                        if cpus and mems:
                                            cpu_mem_by_step_run[step_name][rc] = {
                                                'avg_cpu_percent': float(np.mean(cpus)),
                                                'peak_cpu_percent': float(np.max(cpus)),
                                                'avg_memory_mb': float(np.mean(mems) * total_mem_mb / 100),
                                                'peak_memory_mb': float(np.max(mems) * total_mem_mb / 100)
                                            }
                            except Exception as e:
                                print(f"      Error reading step resource file {res_pattern}: {e}")

            val_metrics = {
                rk: {'tasks_generated': 0, 'code_generated': 0, 'validated_code': 0, 'executed_code': 0} for rk in run_keys
            }
            
            for rc in run_keys:
                if rc in cpu_mem_by_step_run['task_generator'] and cpu_mem_by_step_run['task_generator'][rc]:
                    if not bench_rows.empty:
                        tg_row = bench_rows[(bench_rows['step'] == 'task_generator') & (bench_rows['run_count'] == int(rc))]
                        if not tg_row.empty and tg_row['status'].values[0] == 'failed':
                            val_metrics[rc]['tasks_generated'] = 0
                            val_metrics[rc]['code_generated'] = 0
                            val_metrics[rc]['validated_code'] = 0
                            val_metrics[rc]['executed_code'] = 0
            
            detected_val_model = None
            if os.path.exists(val_ds_dir):
                all_runs_files = glob.glob(os.path.join(val_ds_dir, f"val_sum_{filename_model}_{sess}_all_runs.json"))
                if all_runs_files:
                    try:
                        with open(all_runs_files[0], "r") as f:
                            all_data = json.load(f)
                        runs_dict = all_data.get('runs', {})
                        for rc in run_keys:
                            if rc in runs_dict:
                                tasks_list = runs_dict[rc]
                                val_metrics[rc]['tasks_generated'] = len(tasks_list)
                                not_gen = sum(1 for t in tasks_list if "script file not found" in t.get("message", "").lower() or "script not found" in t.get("message", "").lower())
                                val_metrics[rc]['code_generated'] = len(tasks_list) - not_gen
                                val_metrics[rc]['validated_code'] = sum(1 for t in tasks_list if t.get('validator_passed', False) or t.get('status') == 'passed')
                                run_files[rc]['validator'] = os.path.basename(all_runs_files[0])
                    except Exception as e:
                        print(f"      Error reading all_runs.json: {e}")
                    else:
                        # Read val_model from JSON if present
                        try:
                            with open(all_runs_files[0], "r") as f:
                                all_data_meta = json.load(f)
                            detected_val_model = all_data_meta.get('val_model', all_data_meta.get('model', None))
                        except Exception:
                            pass
                else:
                    for rc in run_keys:
                        r_files = glob.glob(os.path.join(val_ds_dir, f"val_sum_{filename_model}_{sess}_run{rc}.json"))
                        if r_files:
                            try:
                                with open(r_files[0], "r") as f:
                                    r_data = json.load(f)
                                tasks_list = r_data.get('tasks', [])
                                val_metrics[rc]['tasks_generated'] = len(tasks_list)
                                not_gen = sum(1 for t in tasks_list if "script file not found" in t.get("message", "").lower() or "script not found" in t.get("message", "").lower())
                                val_metrics[rc]['code_generated'] = len(tasks_list) - not_gen
                                val_metrics[rc]['validated_code'] = sum(1 for t in tasks_list if t.get('validator_passed', False) or t.get('status') == 'passed')
                                run_files[rc]['validator'] = os.path.basename(r_files[0])
                            except Exception as e:
                                print(f"      Error reading run{rc}.json: {e}")
                            else:
                                # Read val_model from per-run JSON if present
                                if not detected_val_model:
                                    detected_val_model = r_data.get('val_model', r_data.get('model', None))
                                 
            for rc in run_keys:
                if val_metrics[rc]['validated_code'] > 0:
                    count, sched_log = get_scheduler_success_count(folder_path, filename_model, rc, scheduler_start_times[rc])
                    val_metrics[rc]['executed_code'] = count
                    run_files[rc]['scheduler_log'] = sched_log
                else:
                    val_metrics[rc]['executed_code'] = 0
                    
            for rc in run_keys:
                if any(run_files[rc].values()):
                    run_mapping_rows.append({
                        'reported_model': reported_model,
                        'model_run': model_name_display,
                        'dataset': ds,
                        'folder_name': folder,
                        'session_timestamp': sess,
                        'run_idx_in_session': rc,
                        'step1_file': run_files[rc]['step1'],
                        'step2_file': run_files[rc]['step2'],
                        'step3_file': run_files[rc]['step3'],
                        'step4_file': run_files[rc]['step4'],
                        'validator_file': run_files[rc]['validator'],
                        'scheduler_log': run_files[rc]['scheduler_log']
                    })

            step_names_map = {
                'step1_latency': ('task_generator', 'latency'),
                'step2_latency': ('code_generator', 'latency'),
                'step3_latency': ('validator', 'latency'),
                'step4_latency': ('scheduler', 'latency'),
                'step1_prompt_tokens': ('task_generator', 'prompt_tokens'),
                'step1_completion_tokens': ('task_generator', 'completion_tokens'),
                'step2_prompt_tokens': ('code_generator', 'prompt_tokens'),
                'step2_completion_tokens': ('code_generator', 'completion_tokens'),
                'step3_prompt_tokens': ('validator', 'prompt_tokens'),
                'step3_completion_tokens': ('validator', 'completion_tokens')
            }
            
            step_data = {
                'task_generator': {'latency': [], 'prompt_tokens': [], 'completion_tokens': [], 'avg_cpu': [], 'peak_cpu': [], 'avg_mem': [], 'peak_mem': []},
                'code_generator': {'latency': [], 'prompt_tokens': [], 'completion_tokens': [], 'avg_cpu': [], 'peak_cpu': [], 'avg_mem': [], 'peak_mem': []},
                'validator': {'latency': [], 'prompt_tokens': [], 'completion_tokens': [], 'avg_cpu': [], 'peak_cpu': [], 'avg_mem': [], 'peak_mem': []},
                'scheduler': {'latency': [], 'prompt_tokens': [0.0], 'completion_tokens': [0.0], 'avg_cpu': [], 'peak_cpu': [], 'avg_mem': [], 'peak_mem': []}
            }
            
            for rc in run_keys:
                for key, (step_name, metric_name) in step_names_map.items():
                    val = step_metrics[rc].get(key)
                    if val is not None:
                        step_data[step_name][metric_name].append(val)
                for step_name in step_data.keys():
                    if rc in cpu_mem_by_step_run[step_name] and cpu_mem_by_step_run[step_name][rc]:
                        c_m = cpu_mem_by_step_run[step_name][rc]
                        step_data[step_name]['avg_cpu'].append(c_m['avg_cpu_percent'])
                        step_data[step_name]['peak_cpu'].append(c_m['peak_cpu_percent'])
                        step_data[step_name]['avg_mem'].append(c_m['avg_memory_mb'])
                        step_data[step_name]['peak_mem'].append(c_m['peak_memory_mb'])
            
            for step_name, metrics in step_data.items():
                lat_med, lat_q1, lat_q3 = get_median_iqr(metrics['latency'])
                p_tok_med, p_tok_q1, p_tok_q3 = get_median_iqr(metrics['prompt_tokens'])
                c_tok_med, c_tok_q1, c_tok_q3 = get_median_iqr(metrics['completion_tokens'])
                
                tot_tok_runs = []
                for i in range(min(len(metrics['prompt_tokens']), len(metrics['completion_tokens']))):
                    tot_tok_runs.append(metrics['prompt_tokens'][i] + metrics['completion_tokens'][i])
                tot_tok_med, tot_tok_q1, tot_tok_q3 = get_median_iqr(tot_tok_runs)
                
                p_tps_runs = []
                c_tps_runs = []
                tot_tps_runs = []
                for i in range(min(len(metrics['prompt_tokens']), len(metrics['latency']))):
                    lat = metrics['latency'][i]
                    if lat and lat > 0:
                        p_tps_runs.append(metrics['prompt_tokens'][i] / lat)
                        c_tps_runs.append(metrics['completion_tokens'][i] / lat)
                        tot_tps_runs.append((metrics['prompt_tokens'][i] + metrics['completion_tokens'][i]) / lat)
                
                p_tps_med, p_tps_q1, p_tps_q3 = get_median_iqr(p_tps_runs)
                c_tps_med, c_tps_q1, c_tps_q3 = get_median_iqr(c_tps_runs)
                tot_tps_med, tot_tps_q1, tot_tps_q3 = get_median_iqr(tot_tps_runs)
                
                avg_cpu_med, avg_cpu_q1, avg_cpu_q3 = get_median_iqr(metrics['avg_cpu'])
                peak_cpu_med, peak_cpu_q1, peak_cpu_q3 = get_median_iqr(metrics['peak_cpu'])
                avg_mem_med, avg_mem_q1, avg_mem_q3 = get_median_iqr(metrics['avg_mem'])
                
                master_step_rows.append({
                    'folder_name': folder,
                    'model_name': model_name_display,
                    'val_model': detected_val_model or '',
                    'dataset': ds,
                    'session_timestamp': sess,
                    'step': step_name,
                    'latency_median': lat_med,
                    'latency_q1': lat_q1,
                    'latency_q3': lat_q3,
                    'prompt_tokens_median': p_tok_med,
                    'prompt_tokens_q1': p_tok_q1,
                    'prompt_tokens_q3': p_tok_q3,
                    'completion_tokens_median': c_tok_med,
                    'completion_tokens_q1': c_tok_q1,
                    'completion_tokens_q3': c_tok_q3,
                    'total_tokens_median': tot_tok_med,
                    'total_tokens_q1': tot_tok_q1,
                    'total_tokens_q3': tot_tok_q3,
                    'prompt_tokens_per_sec_median': p_tps_med,
                    'prompt_tokens_per_sec_q1': p_tps_q1,
                    'prompt_tokens_per_sec_q3': p_tps_q3,
                    'completion_tokens_per_sec_median': c_tps_med,
                    'completion_tokens_per_sec_q1': c_tps_q1,
                    'completion_tokens_per_sec_q3': c_tps_q3,
                    'total_tokens_per_sec_median': tot_tps_med,
                    'total_tokens_per_sec_q1': tot_tps_q1,
                    'total_tokens_per_sec_q3': tot_tps_q3,
                    'avg_cpu_percent_median': avg_cpu_med,
                    'avg_cpu_percent_q1': avg_cpu_q1,
                    'avg_cpu_percent_q3': avg_cpu_q3,
                    'peak_cpu_percent_median': peak_cpu_med,
                    'peak_cpu_percent_q1': peak_cpu_q1,
                    'peak_cpu_percent_q3': peak_cpu_q3,
                    'avg_memory_mb_median': avg_mem_med,
                    'avg_memory_mb_q1': avg_mem_q1,
                    'avg_memory_mb_q3': avg_mem_q3
                })

            run_latencies = []
            run_prompt_tokens = []
            run_completion_tokens = []
            run_total_tokens = []
            run_tasks_gen = []
            run_code_gen = []
            run_val_code = []
            run_exec_code = []
            run_val_succ_rate = []
            run_exec_succ_rate = []
            
            for rc in run_keys:
                if not any(run_files[rc].values()):
                    continue
                latencies = [
                    step_metrics[rc]['step1_latency'],
                    step_metrics[rc]['step2_latency'],
                    step_metrics[rc]['step3_latency'],
                    step_metrics[rc]['step4_latency']
                ]
                valid_lats = [l for l in latencies if l is not None]
                if valid_lats:
                    run_latencies.append(sum(valid_lats))
                else:
                    run_latencies.append(0.0)
                    
                p_tok = (step_metrics[rc]['step1_prompt_tokens'] or 0.0) + \
                        (step_metrics[rc]['step2_prompt_tokens'] or 0.0) + \
                        (step_metrics[rc]['step3_prompt_tokens'] or 0.0)
                c_tok = (step_metrics[rc]['step1_completion_tokens'] or 0.0) + \
                        (step_metrics[rc]['step2_completion_tokens'] or 0.0) + \
                        (step_metrics[rc]['step3_completion_tokens'] or 0.0)
                run_prompt_tokens.append(p_tok)
                run_completion_tokens.append(c_tok)
                run_total_tokens.append(p_tok + c_tok)
                
                tasks_gen = val_metrics[rc]['tasks_generated']
                code_gen = val_metrics[rc]['code_generated']
                val_code = val_metrics[rc]['validated_code']
                exec_code = val_metrics[rc]['executed_code']
                
                run_tasks_gen.append(tasks_gen)
                run_code_gen.append(code_gen)
                run_val_code.append(val_code)
                run_exec_code.append(exec_code)
                
                val_rate = val_code / code_gen if code_gen > 0 else 0.0
                exec_rate = exec_code / val_code if val_code > 0 else 0.0
                
                run_val_succ_rate.append(val_rate)
                run_exec_succ_rate.append(exec_rate)
                
            if run_latencies:
                lat_med, lat_q1, lat_q3 = get_median_iqr(run_latencies)
                p_tok_med, p_tok_q1, p_tok_q3 = get_median_iqr(run_prompt_tokens)
                c_tok_med, c_tok_q1, c_tok_q3 = get_median_iqr(run_completion_tokens)
                tot_tok_med, tot_tok_q1, tot_tok_q3 = get_median_iqr(run_total_tokens)
                
                tasks_med, tasks_q1, tasks_q3 = get_median_iqr(run_tasks_gen)
                code_med, code_q1, code_q3 = get_median_iqr(run_code_gen)
                val_med, val_q1, val_q3 = get_median_iqr(run_val_code)
                exec_med, exec_q1, exec_q3 = get_median_iqr(run_exec_code)
                
                val_rate_med, val_rate_q1, val_rate_q3 = get_median_iqr(run_val_succ_rate)
                exec_rate_med, exec_rate_q1, exec_rate_q3 = get_median_iqr(run_exec_succ_rate)
                
                master_run_rows.append({
                    'folder_name': folder,
                    'model_name': model_name_display,
                    'val_model': detected_val_model or '',
                    'dataset': ds,
                    'session_timestamp': sess,
                    'total_latency_sec_median': lat_med,
                    'total_latency_sec_q1': lat_q1,
                    'total_latency_sec_q3': lat_q3,
                    'total_prompt_tokens_median': p_tok_med,
                    'total_prompt_tokens_q1': p_tok_q1,
                    'total_prompt_tokens_q3': p_tok_q3,
                    'total_completion_tokens_median': c_tok_med,
                    'total_completion_tokens_q1': c_tok_q1,
                    'total_completion_tokens_q3': c_tok_q3,
                    'total_tokens_median': tot_tok_med,
                    'total_tokens_q1': tot_tok_q1,
                    'total_tokens_q3': tot_tok_q3,
                    'tasks_generated_total': sum(run_tasks_gen),
                    'tasks_generated_median': tasks_med,
                    'tasks_generated_q1': tasks_q1,
                    'tasks_generated_q3': tasks_q3,
                    'code_generated_total': sum(run_code_gen),
                    'code_generated_median': code_med,
                    'code_generated_q1': code_q1,
                    'code_generated_q3': code_q3,
                    'validated_code_total': sum(run_val_code),
                    'validated_code_median': val_med,
                    'validated_code_q1': val_q1,
                    'validated_code_q3': val_q3,
                    'executed_code_total': sum(run_exec_code),
                    'executed_code_median': exec_med,
                    'executed_code_q1': exec_q1,
                    'executed_code_q3': exec_q3,
                    'validation_success_rate_median': val_rate_med,
                    'validation_success_rate_q1': val_rate_q1,
                    'validation_success_rate_q3': val_rate_q3,
                    'execution_success_rate_median': exec_rate_med,
                    'execution_success_rate_q1': exec_rate_q1,
                    'execution_success_rate_q3': exec_rate_q3
                })

    if not master_step_rows:
        print("No metrics aggregated.")
        return

    df_master_step = pd.DataFrame(master_step_rows)
    df_master_run = pd.DataFrame(master_run_rows)

    df_master_step = round_dataframe(df_master_step)
    df_master_run = round_dataframe(df_master_run)

    df_master_step.to_csv(os.path.join(out_dir, "master_step_metrics.csv"), index=False)
    df_master_run.to_csv(os.path.join(out_dir, "master_run_metrics.csv"), index=False)

    print("\nWrote master Median/IQR CSV files:")
    print(f"  {os.path.join(out_dir, 'master_step_metrics.csv')}")
    print(f"  {os.path.join(out_dir, 'master_run_metrics.csv')}")

    # Generate CPU & Memory usage Median & IQR
    cpu_mem_cols = [
        'folder_name', 'model_name', 'dataset', 'session_timestamp', 'step',
        'avg_cpu_percent_median', 'avg_cpu_percent_q1', 'avg_cpu_percent_q3',
        'peak_cpu_percent_median', 'peak_cpu_percent_q1', 'peak_cpu_percent_q3',
        'avg_memory_mb_median', 'avg_memory_mb_q1', 'avg_memory_mb_q3'
    ]
    df_master_step[cpu_mem_cols].to_csv(os.path.join(out_dir, "1_cpu_memory_usage.csv"), index=False)

    # Token throughput
    token_cols = [
        'folder_name', 'model_name', 'dataset', 'session_timestamp', 'step',
        'prompt_tokens_median', 'prompt_tokens_q1', 'prompt_tokens_q3',
        'completion_tokens_median', 'completion_tokens_q1', 'completion_tokens_q3',
        'total_tokens_median', 'total_tokens_q1', 'total_tokens_q3',
        'prompt_tokens_per_sec_median', 'prompt_tokens_per_sec_q1', 'prompt_tokens_per_sec_q3',
        'completion_tokens_per_sec_median', 'completion_tokens_per_sec_q1', 'completion_tokens_per_sec_q3',
        'total_tokens_per_sec_median', 'total_tokens_per_sec_q1', 'total_tokens_per_sec_q3'
    ]
    df_master_step[token_cols].to_csv(os.path.join(out_dir, "2_token_throughput.csv"), index=False)

    # End-to-end step latency
    latency_cols = [
        'folder_name', 'model_name', 'dataset', 'session_timestamp', 'step',
        'latency_median', 'latency_q1', 'latency_q3'
    ]
    df_master_step[latency_cols].to_csv(os.path.join(out_dir, "3_step_latency.csv"), index=False)

    # Validation success rate
    val_succ_cols = [
        'folder_name', 'model_name', 'dataset', 'session_timestamp',
        'validation_success_rate_median', 'validation_success_rate_q1', 'validation_success_rate_q3'
    ]
    df_master_run[val_succ_cols].to_csv(os.path.join(out_dir, "4_validation_success_rate.csv"), index=False)

    # Execution success rate
    exec_succ_cols = [
        'folder_name', 'model_name', 'dataset', 'session_timestamp',
        'execution_success_rate_median', 'execution_success_rate_q1', 'execution_success_rate_q3'
    ]
    df_master_run[exec_succ_cols].to_csv(os.path.join(out_dir, "5_execution_success_rate.csv"), index=False)

    # Pipeline counts
    pipeline_cols = [
        'folder_name', 'model_name', 'dataset', 'session_timestamp',
        'tasks_generated_total', 'tasks_generated_median', 'tasks_generated_q1', 'tasks_generated_q3',
        'code_generated_total', 'code_generated_median', 'code_generated_q1', 'code_generated_q3',
        'validated_code_total', 'validated_code_median', 'validated_code_q1', 'validated_code_q3',
        'executed_code_total', 'executed_code_median', 'executed_code_q1', 'executed_code_q3'
    ]
    df_master_run[pipeline_cols].to_csv(os.path.join(out_dir, "6_pipeline_counts.csv"), index=False)

    if run_mapping_rows:
        df_run_mapping = pd.DataFrame(run_mapping_rows)
        df_run_mapping.to_csv(os.path.join(out_dir, "run_mapping_details.csv"), index=False)
        print(f"Wrote run mapping details to {os.path.join(out_dir, 'run_mapping_details.csv')}")

    print("Wrote all Median & IQR summary CSV files successfully!")

if __name__ == "__main__":
    main()
