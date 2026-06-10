import os
import sys
import time
import csv
import shutil
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
import psutil
import json

# IST Timezone setup
IST = timezone(timedelta(hours=5, minutes=30))

# Clear proxy settings to ensure direct LAN access to local Ollama
for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(key, None)

# Paths setup
LEI_DIR = Path(__file__).resolve().parent
DATA_DIR = LEI_DIR / "data"
RESULTS_DIR = LEI_DIR / "results"
RESULTS_CSV_PATH = RESULTS_DIR / "benchmark_results_v3.csv"
SUMMARY_CSV_PATH = RESULTS_DIR / "benchmark_summary_v3.csv"

# Pre-load dotenv from LEI directory
try:
    from dotenv import load_dotenv
    load_dotenv(LEI_DIR / ".env")
except ImportError:
    pass

# Ensure results directory exists
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Comparison parameters
MODELS = [
    "qwen2.5-coder:7b-instruct-q8_0",
    "deepseek-coder:6.7b-instruct-q8_0",
    "codegemma:7b-instruct-v1.1-q8_0",
    "granite-code:8b-instruct-q8_0",
    "yi-coder:9b-chat-q8_0",
    "codellama:7b-instruct-q8_0"
]

#DATASETS = ["agri-data", "air-quality", "lab-data", "meteo-data"]
DATASETS = ["lab-data", "meteo-data"]
NUM_RUNS = 1

# 1. Resource Profiler (0.1s interval)
class ResourceProfiler:
    """High-frequency resource profiler using a background thread."""
    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = None
        self.cpu_samples = []
        self.memory_samples = []  # In Bytes
        self.start_time = 0.0
        self.end_time = 0.0
        self.process = psutil.Process()

    def _profile_loop(self):
        self.process.cpu_percent(interval=None)
        while not self._stop_event.is_set():
            try:
                cpu = self.process.cpu_percent(interval=None)
                mem = self.process.memory_info().rss
                
                # Accrue child process stats (e.g. validator executions or scheduler tasks)
                for child in self.process.children(recursive=True):
                    try:
                        cpu += child.cpu_percent(interval=None)
                        mem += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                self.cpu_samples.append(cpu)
                self.memory_samples.append(mem)
            except Exception:
                pass
            time.sleep(self.interval)

    def start(self):
        self.cpu_samples.clear()
        self.memory_samples.clear()
        self._stop_event.clear()
        self.start_time = time.perf_counter()
        
        self._thread = threading.Thread(target=self._profile_loop, daemon=True)
        self._thread.start()

    def stop(self, label: str = None, results_dir: Path = None) -> dict:
        self.end_time = time.perf_counter()
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            
        elapsed_time = self.end_time - self.start_time
        
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0.0
        peak_cpu = max(self.cpu_samples) if self.cpu_samples else 0.0
        
        mem_mb = [m / (1024 * 1024) for m in self.memory_samples]
        avg_mem = sum(mem_mb) / len(mem_mb) if mem_mb else 0.0
        peak_mem = max(mem_mb) if mem_mb else 0.0
        
        # Save individual sample CSVs under samples/ if requested
        if label and self.cpu_samples and results_dir:
            try:
                samples_dir = results_dir / "samples"
                samples_dir.mkdir(parents=True, exist_ok=True)
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                csv_path = samples_dir / f"{label}_{timestamp_str}.csv"
                
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["time_offset_sec", "cpu_percent", "memory_rss_mb"])
                    for idx, (cpu_val, mem_val) in enumerate(zip(self.cpu_samples, mem_mb)):
                        time_offset = round(idx * self.interval, 2)
                        writer.writerow([time_offset, round(cpu_val, 2), round(mem_val, 2)])
            except Exception as e:
                print(f"[WARNING] Could not save raw resource samples: {e}")
        
        return {
            "elapsed_time_sec": round(elapsed_time, 3),
            "avg_cpu_percent": round(avg_cpu, 2),
            "peak_cpu_percent": round(peak_cpu, 2),
            "avg_memory_mb": round(avg_mem, 2),
            "peak_memory_mb": round(peak_mem, 2)
        }

# 2. Directory Cleaner
def clean_lei_directories(dataset_name: str, keep_tasks_list: bool = True, keep_error_log: bool = False):
    generated_dir = LEI_DIR / "generated_tasks" / dataset_name
    output_dir = LEI_DIR / "output" / dataset_name
    
    if output_dir.exists():
        try:
            shutil.rmtree(output_dir)
        except Exception:
            pass
            
    if generated_dir.exists():
        for file_path in generated_dir.glob("*"):
            if file_path.is_file():
                if keep_tasks_list and file_path.name == "tasks_list.json":
                    continue
                if keep_error_log and file_path.name in ("error.csv", "error.txt"):
                    continue
                try:
                    file_path.unlink()
                except Exception:
                    pass

# 3. Script Runner in Isolated process (CWD + env)
def _run_lei_script_in_process(script_path: Path, env_override: dict) -> int:
    import sys
    import os
    import importlib.util
    import io
    
    old_env = os.environ.copy()
    old_sys_path = list(sys.path)
    old_cwd = os.getcwd()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        # Silence printing to console
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        os.chdir(str(LEI_DIR))

        for k, v in env_override.items():
            os.environ[k] = str(v)
            
        lei_dir_str = str(LEI_DIR)
        if lei_dir_str not in sys.path:
            sys.path.insert(0, lei_dir_str)
            
        script_dir = str(script_path.parent)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
            
        for mod_name in ['config', 'shared_utils']:
            if mod_name in sys.modules:
                try:
                    importlib.reload(sys.modules[mod_name])
                except Exception:
                    pass
                    
        module_name = script_path.stem
        sys.modules.pop(module_name, None)
        
        spec = importlib.util.spec_from_file_location(module_name, str(script_path))
        if spec is None or spec.loader is None:
            raise FileNotFoundError(f"Cannot load script at {script_path}")
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, "main"):
            ret = module.main()
        else:
            ret = 0
            
        if ret is None:
            ret = 0
        return ret
    except Exception as e:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print(f"[ERROR in Script {script_path.name}] {e}")
        raise e
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        os.environ.clear()
        os.environ.update(old_env)
        sys.path = old_sys_path
        os.chdir(old_cwd)

# 4. Result Recording
def save_benchmark_row(results_csv_path: Path, stats: dict):
    results_csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = results_csv_path.exists() and results_csv_path.stat().st_size > 0
    
    fieldnames = [
        "timestamp",
        "dataset",
        "model",
        "run_count",
        "step",
        "elapsed_time_sec",
        "avg_cpu_percent",
        "peak_cpu_percent",
        "avg_memory_mb",
        "peak_memory_mb",
        "status"
    ]
    
    with open(results_csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(stats)

# 5. Summarization
def calculate_mean_std(values: list) -> tuple:
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = variance ** 0.5
    return round(mean, 3), round(std, 3)

def generate_summary(results_csv_path: Path, summary_csv_path: Path):
    if not results_csv_path.exists():
        return
    
    data = []
    with open(results_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
            
    # Group by (dataset, model, step)
    groups = {}
    for row in data:
        key = (row["dataset"], row["model"], row["step"])
        if key not in groups:
            groups[key] = []
        groups[key].append(row)
        
    summary_rows = []
    for (dataset, model, step), rows in sorted(groups.items()):
        times = [float(r["elapsed_time_sec"]) for r in rows]
        cpus = [float(r["avg_cpu_percent"]) for r in rows]
        mems = [float(r["avg_memory_mb"]) for r in rows]
        
        t_mean, t_std = calculate_mean_std(times)
        cpu_mean, cpu_std = calculate_mean_std(cpus)
        mem_mean, mem_std = calculate_mean_std(mems)
        
        summary_rows.append({
            "dataset": dataset,
            "model": model,
            "step": step,
            "runs_count": len(rows),
            "elapsed_time_mean": t_mean,
            "elapsed_time_std": t_std,
            "avg_cpu_mean": cpu_mean,
            "avg_cpu_std": cpu_std,
            "avg_memory_mean": mem_mean,
            "avg_memory_std": mem_std
        })
        
    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset", "model", "step", "runs_count",
        "elapsed_time_mean", "elapsed_time_std",
        "avg_cpu_mean", "avg_cpu_std",
        "avg_memory_mean", "avg_memory_std"
    ]
    with open(summary_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
        
    # Print console summary
    print("\n" + "=" * 100)
    print(f"BENCHMARK v3 SUMMARY TABLE (Mean ± Std Dev)")
    print("=" * 100)
    print(f"{'Dataset':<12} | {'Model':<30} | {'Step':<20} | {'Time (s)':<15} | {'CPU (%)':<15} | {'Memory (MB)':<15}")
    print("-" * 100)
    for row in summary_rows:
        t_str = f"{row['elapsed_time_mean']} ± {row['elapsed_time_std']}"
        cpu_str = f"{row['avg_cpu_mean']} ± {row['avg_cpu_std']}"
        mem_str = f"{row['avg_memory_mean']} ± {row['avg_memory_std']}"
        print(f"{row['dataset']:<12} | {row['model']:<30} | {row['step']:<20} | {t_str:<15} | {cpu_str:<15} | {mem_str:<15}")
    print("=" * 100 + "\n")

# 6. Main Runner
def main():
    print(f"================ STARTING LEI BENCHMARK v3 ================")
    print(f"Datasets: {DATASETS}")
    print(f"Models: {MODELS}")
    print(f"Runs: {NUM_RUNS} per combination\n")
    
    # Ensure raw datasets exist
    for d in DATASETS:
        if not (DATA_DIR / d).exists():
            print(f"[ERROR] Dataset {d} not found in {DATA_DIR}")
            sys.exit(1)
            
    run_id = "lei_v3_bench_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for dataset in DATASETS:
        dataset_results_dir = RESULTS_DIR / dataset
        dataset_results_dir.mkdir(parents=True, exist_ok=True)
        
        for model in MODELS:
            print(f"\nProcessing Model: {model} on Dataset: {dataset}...")
            
            for r in range(1, NUM_RUNS + 1):
                print(f"  Run {r}/{NUM_RUNS}...")
                
                # Keep error.csv for run > 1 (self-correction feedback)
                keep_err = (r > 1)
                clean_lei_directories(dataset, keep_tasks_list=False, keep_error_log=keep_err)
                
                # Environment override for this run
                env_override = {
                    "DATA_TYPE": dataset,
                    "LLM_PROVIDER": "ollama",
                    "LLM_MODEL": model,
                    "LLM_VAL_MODEL": model,
                    "RUN_ID": run_id,
                    "RUN_COUNT": str(r),
                }
                
                # Step 1: Task Generator
                try:
                    stats_step1 = run_step_with_profiling(
                        "task_generator",
                        LEI_DIR / "task_generator.py",
                        env_override,
                        r,
                        dataset,
                        model,
                        dataset_results_dir
                    )
                    save_benchmark_row(RESULTS_CSV_PATH, stats_step1)
                    if stats_step1["status"] == "failed":
                        print("    [ABORT] task_generator failed. Skipping remaining steps for this run.")
                        continue
                except Exception as e:
                    print(f"    [ABORT] task_generator threw exception: {e}")
                    continue
                    
                # Step 2: Code Generator
                try:
                    stats_step2 = run_step_with_profiling(
                        "code_generator",
                        LEI_DIR / "code_generator.py",
                        env_override,
                        r,
                        dataset,
                        model,
                        dataset_results_dir
                    )
                    save_benchmark_row(RESULTS_CSV_PATH, stats_step2)
                    if stats_step2["status"] == "failed":
                        print("    [ABORT] code_generator failed. Skipping remaining steps for this run.")
                        continue
                except Exception as e:
                    print(f"    [ABORT] code_generator threw exception: {e}")
                    continue
                    
                # Step 3: Validator
                try:
                    stats_step3 = run_step_with_profiling(
                        "validator",
                        LEI_DIR / "validator.py",
                        env_override,
                        r,
                        dataset,
                        model,
                        dataset_results_dir
                    )
                    save_benchmark_row(RESULTS_CSV_PATH, stats_step3)
                    if stats_step3["status"] == "failed":
                        print("    [ABORT] validator failed. Skipping remaining steps for this run.")
                        continue
                except Exception as e:
                    print(f"    [ABORT] validator threw exception: {e}")
                    continue
                    
                # Step 4: Edge Scheduler (Parallel Scheduler)
                try:
                    stats_step4 = run_step_with_profiling(
                        "scheduler",
                        LEI_DIR / "scheduler" / "edge_scheduler.py",
                        env_override,
                        r,
                        dataset,
                        model,
                        dataset_results_dir
                    )
                    save_benchmark_row(RESULTS_CSV_PATH, stats_step4)
                except Exception as e:
                    print(f"    [ERROR] scheduler threw exception: {e}")
                    
    # Generate summary CSV and console tables
    generate_summary(RESULTS_CSV_PATH, SUMMARY_CSV_PATH)
    print("\n================ BENCHMARK v3 COMPLETED ================\n")

def run_step_with_profiling(step_name: str, script_path: Path, env_override: dict, run_num: int, dataset_name: str, model_name: str, results_dir: Path) -> dict:
    profiler = ResourceProfiler(interval=0.1)
    profiler.start()
    
    start_time = datetime.now(IST).isoformat()
    t_start = time.time()
    status = "success"
    
    try:
        ret = _run_lei_script_in_process(script_path, env_override)
        if ret != 0:
            status = "failed"
    except Exception:
        status = "failed"
        
    duration = time.time() - t_start
    stats = profiler.stop(label=f"LEI_{step_name}_run{run_num}", results_dir=results_dir)
    
    stats.update({
        "timestamp": start_time,
        "dataset": dataset_name,
        "model": model_name,
        "run_count": run_num,
        "step": step_name,
        "elapsed_time_sec": round(duration, 3),
        "status": status
    })
    
    return stats

if __name__ == "__main__":
    main()
