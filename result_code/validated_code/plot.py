import os
import sys
import time
import subprocess
import csv
import psutil
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(CODE_DIR, "resource_usage_with_time.csv")
SUMMARY_PATH = os.path.join(CODE_DIR, "resource_usage_summary_by_dataset.csv")

MEM_LIMIT_MB = 200
CPU_LIMIT_PCT = 30

COLOR_MAP = {
    "agri-data": "#2ca02c",      
    "air-quality": "#1f77b4",    
    "lab-data": "#ff7f0e",       
    "meteo-data": "#9467bd",     
    "unknown": "#7f7f7f"         
}

DATASET_ORDER = ["agri-data", "air-quality", "lab-data", "meteo-data"]

PROFILE_FROM_SCRATCH = True

def monitor_script(script_info):
    script_name, script_path, dataset = script_info

    p = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    cpu_samples = []
    mem_samples = []
    num_cores = psutil.cpu_count() or 1
    start_time = time.perf_counter()

    try:
        proc = psutil.Process(p.pid)
        proc.cpu_percent(interval=None)

        while time.perf_counter() - start_time < 60.0:
            if p.poll() is not None:
                break
            try:
                cpu = proc.cpu_percent(interval=None)
                norm_cpu = cpu / num_cores
                mem = proc.memory_info().rss / (1024 * 1024)

                cpu_samples.append(norm_cpu)
                mem_samples.append(mem)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(0.01)
    except Exception:
        pass
    finally:
        try:
            p.terminate()
            p.wait(timeout=1)
        except Exception:
            pass

    exec_time = time.perf_counter() - start_time

    if not cpu_samples:
        cpu_samples = [0.0]
    if not mem_samples:
        mem_samples = [0.0]

    return {
        "script": script_name,
        "dataset": dataset,
        "median_cpu": float(pd.Series(cpu_samples).median()),
        "peak_cpu": max(cpu_samples),
        "median_mem": float(pd.Series(mem_samples).median()),
        "peak_mem": max(mem_samples),
        "exec_time": exec_time,
    }


def _build_dataset_summary(results):
    df = pd.DataFrame(results)
    if df.empty:
        return df

    summary = (
        df.groupby("dataset", dropna=False)
        .agg(
            script_count=("script", "count"),
            exec_time_median_s=("exec_time", "median"),
            peak_cpu_median_pct=("peak_cpu", "median"),
            peak_cpu_max_pct=("peak_cpu", "max"),
            peak_mem_median_mb=("peak_mem", "median"),
            peak_mem_max_mb=("peak_mem", "max"),
        )
        .reset_index()
    )

    summary["dataset"] = pd.Categorical(summary["dataset"], categories=DATASET_ORDER, ordered=True)
    summary = summary.sort_values("dataset").reset_index(drop=True)
    summary["dataset"] = summary["dataset"].astype(str)

    return summary


def _print_dataset_summary(summary):
    if summary.empty:
        print("No profiling rows available for dataset summary.")
        return

    print("\n--- DATASET SUMMARY ---")
    for row in summary.to_dict(orient="records"):
        print(
            f"{row['dataset']}: scripts={int(row['script_count'])}, "
            f"exec_time_median={row['exec_time_median_s']:.4f}s, "
            f"peak_cpu_median={row['peak_cpu_median_pct']:.2f}%, "
            f"peak_cpu_max={row['peak_cpu_max_pct']:.2f}%, "
            f"peak_mem_median={row['peak_mem_median_mb']:.2f}MB, "
            f"peak_mem_max={row['peak_mem_max_mb']:.2f}MB"
        )

def main():
    if not PROFILE_FROM_SCRATCH and os.path.isfile(CSV_PATH):
        print(f"Loading existing profiling data from {CSV_PATH}")
        results = []
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for k in ["peak_cpu", "peak_mem", "exec_time"]:
                    row[k] = float(row[k])
                for k in ["median_cpu", "median_mem"]:
                    if k in row and row[k] not in (None, ""):
                        row[k] = float(row[k])
                    else:
                        legacy_key = "avg_cpu" if k == "median_cpu" else "avg_mem"
                        if legacy_key in row and row[legacy_key] not in (None, ""):
                            row[k] = float(row[legacy_key])
                        else:
                            row[k] = 0.0
                results.append(row)
        print(f"  -> {len(results)} code samples loaded.")
    else:
        script_tasks = []
        for root, dirs, files in os.walk(CODE_DIR):
            for f in files:
                if f.endswith(".py") and f not in ("plot.py", "monitor_and_plot.py"):
                    path = os.path.join(root, f)
                    rel = os.path.relpath(root, CODE_DIR)
                    dataset = rel.split(os.sep)[0]
                    if dataset not in COLOR_MAP:
                        dataset = "unknown"
                    script_tasks.append((f, path, dataset))

        print(f"Found {len(script_tasks)} scripts to profile. Running in parallel (max_workers=8)...")

        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(monitor_script, task): task for task in script_tasks}
            for fut in as_completed(futures):
                res = fut.result()
                results.append(res)
                print(f"  Profiled {res['script']} -> CPU: {res['peak_cpu']:.2f}%, MEM: {res['peak_mem']:.2f} MB, TIME: {res['exec_time']:.4f} s")

        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["script", "dataset", "median_cpu", "peak_cpu", "median_mem", "peak_mem", "exec_time"])
            writer.writeheader()
            writer.writerows(results)
        print(f"\nSaved raw data to {CSV_PATH}")

    summary = _build_dataset_summary(results)
    if not summary.empty:
        summary.to_csv(SUMMARY_PATH, index=False)
        print(f"Saved dataset summary to {SUMMARY_PATH}")
    _print_dataset_summary(summary)

if __name__ == "__main__":
    main()
