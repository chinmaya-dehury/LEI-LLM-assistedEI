"""
benchmark_runner_triple.py
--------------------------
Unified benchmarking runner that compares LEI, AutoGen, and LangGraph
side-by-side for 10 runs per discovered dataset.

Features:
- Dynamically discovers datasets inside the data/ folder.
- Clears terminal proxy variables to prevent network connection errors to local Ollama.
- Uses ResourceProfiler to profile CPU and Memory usage.
- Automatically copies and sets up the dataset for each framework benchmark.
- Outputs results dynamically inside each dataset's folder:
  `results/<dataset_name>/benchmark_results_triple.csv`
  `results/<dataset_name>/benchmark_summary_triple.csv`
- Prints a clean side-by-side comparative summary table.
"""

import os
import sys
import csv
import json
import shutil
import argparse
import time
import threading
from datetime import datetime
from pathlib import Path
import psutil

# 1. Clear terminal proxy environment variables at startup to prevent local Ollama connection issues
for var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    os.environ.pop(var, None)

# Setup paths
LEI_DIR = Path(__file__).resolve().parent
DATA_DIR = LEI_DIR / "data"

# Auto-detect sibling repositories
AUTOGEN_DIR = LEI_DIR.parent / "autogen"
LANGGRAPH_DIR = LEI_DIR.parent / "langgraph"

# Ensure autogen and langgraph exists
if not AUTOGEN_DIR.exists():
    print(f"[WARNING] Sibling autogen directory not found at {AUTOGEN_DIR}. Running benchmarks for autogen will be skipped.")
if not LANGGRAPH_DIR.exists():
    print(f"[WARNING] Sibling langgraph directory not found at {LANGGRAPH_DIR}. Running benchmarks for langgraph will be skipped.")

# 2. Resource Profiler
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

# 3. Dynamic Workflow Imports
def get_autogen_workflow():
    if not AUTOGEN_DIR.exists():
        return None
    autogen_benchmarks_path = AUTOGEN_DIR / "benchmarks"
    if str(autogen_benchmarks_path) not in sys.path:
        sys.path.insert(0, str(autogen_benchmarks_path))
    try:
        import autogen_workflow
        return autogen_workflow.run_autogen_workflow
    except Exception as e:
        print(f"[ERROR] Failed to import autogen_workflow: {e}")
        return None

def get_langgraph_workflow():
    if not LANGGRAPH_DIR.exists():
        return None
    langgraph_benchmarks_path = LANGGRAPH_DIR / "benchmarks"
    if str(langgraph_benchmarks_path) not in sys.path:
        sys.path.insert(0, str(langgraph_benchmarks_path))
    try:
        import langgraph_workflow
        return langgraph_workflow.run_langgraph_workflow
    except Exception as e:
        print(f"[ERROR] Failed to import langgraph_workflow: {e}")
        return None

# 4. Helper Functions for Dataset & Cleanups
def setup_dataset_for_framework(dest_benchmarks_dir: Path, dataset_name: str) -> Path:
    src_dir = DATA_DIR / dataset_name
    dest_dir = dest_benchmarks_dir / "datasets" / dataset_name
    
    if not src_dir.exists():
        raise FileNotFoundError(f"Dataset folder '{src_dir}' not found.")
        
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = ["sample_data.csv", "metadata.json", "content.txt"]
    for file in files:
        src_file = src_dir / file
        dest_file = dest_dir / file
        if src_file.exists():
            shutil.copy2(src_file, dest_file)
        else:
            if file == "content.txt":
                alt_file = src_dir / "context.txt"
                if alt_file.exists():
                    shutil.copy2(alt_file, dest_file)
                    continue
    return dest_dir

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

def clean_workflow_directories(output_dir: Path, codes_dir: Path):
    if output_dir.exists():
        try:
            shutil.rmtree(output_dir)
        except Exception:
            pass
    output_dir.mkdir(parents=True, exist_ok=True)
    codes_dir.mkdir(parents=True, exist_ok=True)

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
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        os.environ.clear()
        os.environ.update(old_env)
        sys.path = old_sys_path
        os.chdir(old_cwd)

# 5. Framework Execution Routines
def run_lei_benchmark(dataset_name: str, run_id: str, run_num: int, results_dir: Path, keep_error_txt: bool = True) -> dict:
    print(f"  [LEI Pipeline] Run {run_num}/10 starting...")
    clean_lei_directories(dataset_name, keep_tasks_list=False, keep_error_log=keep_error_txt)
    
    profiler = ResourceProfiler()
    profiler.start()
    
    lei_time_up_to_codegen = 0.0
    lei_time_val = 0.0
    t_start = time.time()
    try:
        env = {
            "DATA_TYPE": dataset_name,
            "RUN_ID": run_id,
            "RUN_COUNT": str(run_num),
        }
        
        ret1 = _run_lei_script_in_process(LEI_DIR / "task_generator.py", env)
        if ret1 != 0:
            raise RuntimeError(f"task_generator.py failed: return code {ret1}")
        
        ret2 = _run_lei_script_in_process(LEI_DIR / "code_generator.py", env)
        if ret2 != 0:
            raise RuntimeError(f"code_generator.py failed: return code {ret2}")
            
        lei_time_up_to_codegen = time.time() - t_start
        
        t_val_start = time.time()
        ret3 = _run_lei_script_in_process(LEI_DIR / "validator.py", env)
        lei_time_val = time.time() - t_val_start
        if ret3 != 0:
            raise RuntimeError(f"validator.py failed: return code {ret3}")
        
        ret4 = _run_lei_script_in_process(LEI_DIR / "scheduler" / "edge_scheduler.py", env)
        if ret4 != 0:
            raise RuntimeError(f"edge_scheduler.py failed: return code {ret4}")
    finally:
        stats = profiler.stop(label=f"LEI_run{run_num}", results_dir=results_dir)
    
    generated_dir = LEI_DIR / "generated_tasks" / dataset_name
    try:
        with open(generated_dir / "tasks_list.json", "r", encoding="utf-8") as f:
            tasks_list_data = json.load(f)
            tasks_generated = len(tasks_list_data.get("tasks", []))
    except Exception:
        tasks_generated = 0
        
    code_generated = tasks_generated
    code_passed = 0
    validator_passed = 0
    
    try:
        from shared_utils import sanitize_model_name
        # Fetch directly from config or defaults
        sys.path.insert(0, str(LEI_DIR))
        import config
        val_model = getattr(config, "LLM_VAL_MODEL", "gemma3:4b")
        sanitized_model = sanitize_model_name(val_model)
        
        summary_file = LEI_DIR / "validator" / dataset_name / f"validation_summary_{sanitized_model}_{run_id}_run{run_num}.json"
        if summary_file.exists():
            with open(summary_file, "r", encoding="utf-8") as sf:
                summary_data = json.load(sf)
                sum_info = summary_data.get("summary", {})
                code_generated = sum_info.get("code_generated", tasks_generated)
                code_passed = sum_info.get("code_passed", 0)
                validator_passed = sum_info.get("validator_passed", 0)
    except Exception as e:
        print(f"  [WARNING] Could not parse LEI validation summary: {e}")
    
    stats.update({
        "framework": "LEI",
        "tasks_generated": tasks_generated,
        "code_generated": code_generated,
        "code_passed": code_passed,
        "validator_passed": validator_passed,
        "lei_time_up_to_codegen": lei_time_up_to_codegen,
        "lei_time_val": lei_time_val
    })
    return stats

def run_autogen_benchmark(dataset_name: str, dataset_dir: Path, output_dir: Path, run_num: int, results_dir: Path) -> dict:
    print(f"  [AutoGen Workflow] Run {run_num}/10 starting...")
    autogen_codes_dir = output_dir / "autogen_codes"
    clean_workflow_directories(output_dir, autogen_codes_dir)
    
    run_workflow = get_autogen_workflow()
    if run_workflow is None:
        return {}
        
    profiler = ResourceProfiler()
    profiler.start()
    
    try:
        # Load env vars for child
        os.environ["DATA_TYPE"] = dataset_name
        workflow_output = run_workflow(dataset_dir, autogen_codes_dir)
        
        # Clean up output results in LEI folder
        lei_output_dir = LEI_DIR / "output" / dataset_name
        if lei_output_dir.exists():
            for file_path in lei_output_dir.glob("*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
    finally:
        stats = profiler.stop(label=f"AutoGen_run{run_num}", results_dir=results_dir)
    
    metrics = workflow_output.get("metrics", {}) if workflow_output else {}
    val_time = metrics.get("validation_time", 0.0)
    total_time = stats.get("elapsed_time_sec", 0.0)
    up_to_codegen = max(0.0, total_time - val_time)
    stats.update({
        "framework": "AutoGen",
        "tasks_generated": metrics.get("tasks_count", 0),
        "code_generated": metrics.get("code_generated", 0),
        "code_passed": metrics.get("code_passed", 0),
        "validator_passed": metrics.get("validator_passed", 0),
        "lei_time_up_to_codegen": round(up_to_codegen, 3),
        "lei_time_val": round(val_time, 3)
    })
    return stats

def run_langgraph_benchmark(dataset_name: str, dataset_dir: Path, output_dir: Path, run_num: int, results_dir: Path) -> dict:
    print(f"  [LangGraph Workflow] Run {run_num}/10 starting...")
    langgraph_codes_dir = output_dir / "langgraph_codes"
    clean_workflow_directories(output_dir, langgraph_codes_dir)
    
    run_workflow = get_langgraph_workflow()
    if run_workflow is None:
        return {}
        
    profiler = ResourceProfiler()
    profiler.start()
    
    try:
        os.environ["DATA_TYPE"] = dataset_name
        graph_output = run_workflow(dataset_dir, langgraph_codes_dir)
        
        # Clean up output results in LEI folder
        lei_output_dir = LEI_DIR / "output" / dataset_name
        if lei_output_dir.exists():
            for file_path in lei_output_dir.glob("*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
    finally:
        stats = profiler.stop(label=f"LangGraph_run{run_num}", results_dir=results_dir)
    
    metrics = graph_output.get("metrics", {}) if graph_output else {}
    val_time = metrics.get("validation_time", 0.0)
    total_time = stats.get("elapsed_time_sec", 0.0)
    up_to_codegen = max(0.0, total_time - val_time)
    stats.update({
        "framework": "LangGraph",
        "tasks_generated": metrics.get("tasks_count", 0),
        "code_generated": metrics.get("code_generated", 0),
        "code_passed": metrics.get("code_passed", 0),
        "validator_passed": metrics.get("validator_passed", 0),
        "lei_time_up_to_codegen": round(up_to_codegen, 3),
        "lei_time_val": round(val_time, 3)
    })
    return stats

# 6. Saving results
def save_benchmark_row(results_csv_path: Path, dataset_name: str, stats: dict):
    try:
        results_csv_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = results_csv_path.exists() and results_csv_path.stat().st_size > 0
        
        fieldnames = [
            "timestamp",
            "dataset",
            "framework",
            "tasks_generated",
            "code_generated",
            "code_passed",
            "validator_passed",
            "elapsed_time_sec",
            "lei_time_up_to_codegen",
            "lei_time_val",
            "avg_cpu_percent",
            "avg_memory_mb"
        ]
        
        with open(results_csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
                
            writer.writerow({
                "timestamp": datetime.now().isoformat(),
                "dataset": dataset_name,
                "framework": stats["framework"],
                "tasks_generated": stats["tasks_generated"],
                "code_generated": stats["code_generated"],
                "code_passed": stats["code_passed"],
                "validator_passed": stats["validator_passed"],
                "elapsed_time_sec": stats["elapsed_time_sec"],
                "lei_time_up_to_codegen": stats.get("lei_time_up_to_codegen", 0.0),
                "lei_time_val": stats.get("lei_time_val", 0.0),
                "avg_cpu_percent": stats["avg_cpu_percent"],
                "avg_memory_mb": stats["avg_memory_mb"]
            })
    except Exception as e:
        print(f"[WARNING] Could not save benchmark row: {e}")

def calculate_mean_std(values: list) -> tuple:
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = variance ** 0.5
    return round(mean, 2), round(std, 2)

def process_and_save_summary(lei_results: list, ag_results: list, lg_results: list, summary_csv_path: Path):
    # Extract values for LEI
    lei_tasks = [r["tasks_generated"] for r in lei_results]
    lei_gen = [r["code_generated"] for r in lei_results]
    lei_passed = [r["code_passed"] for r in lei_results]
    lei_val_passed = [r["validator_passed"] for r in lei_results]
    lei_time = [r["elapsed_time_sec"] for r in lei_results]
    lei_codegen_time = [r.get("lei_time_up_to_codegen", 0.0) for r in lei_results]
    lei_val_time = [r.get("lei_time_val", 0.0) for r in lei_results]
    lei_cpu = [r["avg_cpu_percent"] for r in lei_results]
    lei_mem = [r["avg_memory_mb"] for r in lei_results]

    # Extract values for AutoGen
    ag_tasks = [r["tasks_generated"] for r in ag_results] if ag_results else []
    ag_gen = [r["code_generated"] for r in ag_results] if ag_results else []
    ag_passed = [r["code_passed"] for r in ag_results] if ag_results else []
    ag_val_passed = [r["validator_passed"] for r in ag_results] if ag_results else []
    ag_time = [r["elapsed_time_sec"] for r in ag_results] if ag_results else []
    ag_codegen_time = [r.get("lei_time_up_to_codegen", 0.0) for r in ag_results] if ag_results else []
    ag_val_time = [r.get("lei_time_val", 0.0) for r in ag_results] if ag_results else []
    ag_cpu = [r["avg_cpu_percent"] for r in ag_results] if ag_results else []
    ag_mem = [r["avg_memory_mb"] for r in ag_results] if ag_results else []

    # Extract values for LangGraph
    lg_tasks = [r["tasks_generated"] for r in lg_results] if lg_results else []
    lg_gen = [r["code_generated"] for r in lg_results] if lg_results else []
    lg_passed = [r["code_passed"] for r in lg_results] if lg_results else []
    lg_val_passed = [r["validator_passed"] for r in lg_results] if lg_results else []
    lg_time = [r["elapsed_time_sec"] for r in lg_results] if lg_results else []
    lg_codegen_time = [r.get("lei_time_up_to_codegen", 0.0) for r in lg_results] if lg_results else []
    lg_val_time = [r.get("lei_time_val", 0.0) for r in lg_results] if lg_results else []
    lg_cpu = [r["avg_cpu_percent"] for r in lg_results] if lg_results else []
    lg_mem = [r["avg_memory_mb"] for r in lg_results] if lg_results else []

    # Calculate stats
    tasks_lei_m, tasks_lei_s = calculate_mean_std(lei_tasks)
    gen_lei_m, gen_lei_s = calculate_mean_std(lei_gen)
    passed_lei_m, passed_lei_s = calculate_mean_std(lei_passed)
    val_lei_m, val_lei_s = calculate_mean_std(lei_val_passed)
    time_lei_m, time_lei_s = calculate_mean_std(lei_time)
    lei_codegen_m, lei_codegen_s = calculate_mean_std(lei_codegen_time)
    lei_val_m, lei_val_s = calculate_mean_std(lei_val_time)
    cpu_lei_m, cpu_lei_s = calculate_mean_std(lei_cpu)
    mem_lei_m, mem_lei_s = calculate_mean_std(lei_mem)

    tasks_ag_m, tasks_ag_s = calculate_mean_std(ag_tasks)
    gen_ag_m, gen_ag_s = calculate_mean_std(ag_gen)
    passed_ag_m, passed_ag_s = calculate_mean_std(ag_passed)
    val_ag_m, val_ag_s = calculate_mean_std(ag_val_passed)
    time_ag_m, time_ag_s = calculate_mean_std(ag_time)
    ag_codegen_m, ag_codegen_s = calculate_mean_std(ag_codegen_time)
    ag_val_m, ag_val_s = calculate_mean_std(ag_val_time)
    cpu_ag_m, cpu_ag_s = calculate_mean_std(ag_cpu)
    mem_ag_m, mem_ag_s = calculate_mean_std(ag_mem)

    tasks_lg_m, tasks_lg_s = calculate_mean_std(lg_tasks)
    gen_lg_m, gen_lg_s = calculate_mean_std(lg_gen)
    passed_lg_m, passed_lg_s = calculate_mean_std(lg_passed)
    val_lg_m, val_lg_s = calculate_mean_std(lg_val_passed)
    time_lg_m, time_lg_s = calculate_mean_std(lg_time)
    lg_codegen_m, lg_codegen_s = calculate_mean_std(lg_codegen_time)
    lg_val_m, lg_val_s = calculate_mean_std(lg_val_time)
    cpu_lg_m, cpu_lg_s = calculate_mean_std(lg_cpu)
    mem_lg_m, mem_lg_s = calculate_mean_std(lg_mem)

    # Print comparative console table
    print("\n" + "=" * 80)
    print(f"COMPARATIVE BENCHMARKING SUMMARY (10 RUNS: Mean ± Std Dev)")
    print("=" * 80)
    print(f"{'Metric':<30} | {'LEI':<15} | {'AutoGen':<15} | {'LangGraph':<15}")
    print("-" * 80)
    print(f"{'Tasks Generated':<30} | {tasks_lei_m:<4} ± {tasks_lei_s:<6} | {tasks_ag_m:<4} ± {tasks_ag_s:<6} | {tasks_lg_m:<4} ± {tasks_lg_s:<6}")
    print(f"{'Code Generated':<30} | {gen_lei_m:<4} ± {gen_lei_s:<6} | {gen_ag_m:<4} ± {gen_ag_s:<6} | {gen_lg_m:<4} ± {gen_lg_s:<6}")
    print(f"{'Code Passed':<30} | {passed_lei_m:<4} ± {passed_lei_s:<6} | {passed_ag_m:<4} ± {passed_ag_s:<6} | {passed_lg_m:<4} ± {passed_lg_s:<6}")
    print(f"{'Validator Passed':<30} | {val_lei_m:<4} ± {val_lei_s:<6} | {val_ag_m:<4} ± {val_ag_s:<6} | {val_lg_m:<4} ± {val_lg_s:<6}")
    print(f"{'Elapsed Execution Time (s)':<30} | {time_lei_m:<4} ± {time_lei_s:<6} | {time_ag_m:<4} ± {time_ag_s:<6} | {time_lg_m:<4} ± {time_lg_s:<6}")
    print(f"{'  - Up to Code Gen':<30} | {lei_codegen_m:<4} ± {lei_codegen_s:<6} | {ag_codegen_m:<4} ± {ag_codegen_s:<6} | {lg_codegen_m:<4} ± {lg_codegen_s:<6}")
    print(f"{'  - Validation':<30} | {lei_val_m:<4} ± {lei_val_s:<6} | {ag_val_m:<4} ± {ag_val_s:<6} | {lg_val_m:<4} ± {lg_val_s:<6}")
    print(f"{'Average CPU Usage (%)':<30} | {cpu_lei_m:<4} ± {cpu_lei_s:<6} | {cpu_ag_m:<4} ± {cpu_ag_s:<6} | {cpu_lg_m:<4} ± {cpu_lg_s:<6}")
    print(f"{'Average Memory (RSS) (MB)':<30} | {mem_lei_m:<4} ± {mem_lei_s:<6} | {mem_ag_m:<4} ± {mem_ag_s:<6} | {mem_lg_m:<4} ± {mem_lg_s:<6}")
    print("=" * 80 + "\n")

    # Save summary CSV
    try:
        summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["metric", "lei_mean", "lei_std", "autogen_mean", "autogen_std", "langgraph_mean", "langgraph_std"]
        with open(summary_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            metrics_data = [
                ("tasks_generated", tasks_lei_m, tasks_lei_s, tasks_ag_m, tasks_ag_s, tasks_lg_m, tasks_lg_s),
                ("code_generated", gen_lei_m, gen_lei_s, gen_ag_m, gen_ag_s, gen_lg_m, gen_lg_s),
                ("code_passed", passed_lei_m, passed_lei_s, passed_ag_m, passed_ag_s, passed_lg_m, passed_lg_s),
                ("validator_passed", val_lei_m, val_lei_s, val_ag_m, val_ag_s, val_lg_m, val_lg_s),
                ("elapsed_time_sec", time_lei_m, time_lei_s, time_ag_m, time_ag_s, time_lg_m, time_lg_s),
                ("lei_time_up_to_codegen", lei_codegen_m, lei_codegen_s, ag_codegen_m, ag_codegen_s, lg_codegen_m, lg_codegen_s),
                ("lei_time_val", lei_val_m, lei_val_s, ag_val_m, ag_val_s, lg_val_m, lg_val_s),
                ("avg_cpu_percent", cpu_lei_m, cpu_lei_s, cpu_ag_m, cpu_ag_s, cpu_lg_m, cpu_lg_s),
                ("avg_memory_mb", mem_lei_m, mem_lei_s, mem_ag_m, mem_ag_s, mem_lg_m, mem_lg_s)
            ]
            for row in metrics_data:
                writer.writerow({
                    "metric": row[0],
                    "lei_mean": row[1],
                    "lei_std": row[2],
                    "autogen_mean": row[3],
                    "autogen_std": row[4],
                    "langgraph_mean": row[5],
                    "langgraph_std": row[6]
                })
        print(f"[OK] Statistical summary saved to: {summary_csv_path}")
    except Exception as e:
        print(f"[WARNING] Could not save summary CSV: {e}")

# 7. Main loop
def main():
    parser = argparse.ArgumentParser(description="Unified 3-Way Multi-Dataset Benchmarking.")
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of iterations to execute for each framework (default: 10)"
    )
    args = parser.parse_args()
    
    num_runs = args.runs
    
    # Pre-load dotenv from LEI directory
    try:
        from dotenv import load_dotenv
        load_dotenv(LEI_DIR / ".env")
    except ImportError:
        pass
        
    # Discover datasets
    if not DATA_DIR.exists():
        print(f"[ERROR] Datasets directory '{DATA_DIR}' not found.")
        sys.exit(1)
        
    datasets = sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])
    if not datasets:
        print(f"[ERROR] No datasets found inside '{DATA_DIR}'.")
        sys.exit(1)
        
    print(f"\n================ STARTING UNIFIED BENCHMARK ================")
    print(f"Detected datasets: {datasets}")
    print(f"Number of runs per framework: {num_runs}\n")

    for dataset_name in datasets:
        print(f"\n" + "#" * 80)
        print(f" PROCESSING DATASET: {dataset_name}")
        print("#" * 80)
        
        # Paths for results
        results_dir = LEI_DIR / "results" / dataset_name
        results_csv_path = results_dir / "benchmark_results_triple.csv"
        summary_csv_path = results_dir / "benchmark_summary_triple.csv"
        
        # Clean existing results inside this dataset's results dir
        if results_dir.exists():
            try:
                shutil.rmtree(results_dir)
            except Exception:
                pass
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup datasets for other frameworks
        try:
            if AUTOGEN_DIR.exists():
                setup_dataset_for_framework(AUTOGEN_DIR / "benchmarks", dataset_name)
                print(f"[OK] Dataset '{dataset_name}' setup completed for AutoGen.")
            if LANGGRAPH_DIR.exists():
                setup_dataset_for_framework(LANGGRAPH_DIR / "benchmarks", dataset_name)
                print(f"[OK] Dataset '{dataset_name}' setup completed for LangGraph.")
        except Exception as e:
            print(f"[ERROR] Failed to setup datasets for other frameworks: {e}")
            continue
            
        lei_results = []
        ag_results = []
        lg_results = []
        
        run_id = "benchmark_triple_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Run LEI consecutively 10 times
        for r in range(1, num_runs + 1):
            print(f"\n--- Iteration {r}/{num_runs} (LEI) for dataset '{dataset_name}' ---")
            try:
                # Keep error.csv for run > 1 so that we can incorporate errors from previous runs
                keep_err = (r > 1)
                lei_stats = run_lei_benchmark(dataset_name, run_id, r, results_dir, keep_error_txt=keep_err)
                save_benchmark_row(results_csv_path, dataset_name, lei_stats)
                lei_results.append(lei_stats)
            except Exception as e:
                print(f"  [ERROR] LEI run {r} failed: {e}")
                
        # 2. Run AutoGen consecutively 10 times
        if AUTOGEN_DIR.exists():
            for r in range(1, num_runs + 1):
                print(f"\n--- Iteration {r}/{num_runs} (AutoGen) for dataset '{dataset_name}' ---")
                try:
                    autogen_output_dir = AUTOGEN_DIR / "benchmarks" / "results" / dataset_name / "autogen"
                    autogen_dataset_dir = AUTOGEN_DIR / "benchmarks" / "datasets" / dataset_name
                    ag_stats = run_autogen_benchmark(dataset_name, autogen_dataset_dir, autogen_output_dir, r, results_dir)
                    if ag_stats:
                        save_benchmark_row(results_csv_path, dataset_name, ag_stats)
                        ag_results.append(ag_stats)
                except Exception as e:
                    print(f"  [ERROR] AutoGen run {r} failed: {e}")
                    
        # 3. Run LangGraph consecutively 10 times
        if LANGGRAPH_DIR.exists():
            for r in range(1, num_runs + 1):
                print(f"\n--- Iteration {r}/{num_runs} (LangGraph) for dataset '{dataset_name}' ---")
                try:
                    langgraph_output_dir = LANGGRAPH_DIR / "benchmarks" / "results" / dataset_name / "langgraph"
                    langgraph_dataset_dir = LANGGRAPH_DIR / "benchmarks" / "datasets" / dataset_name
                    lg_stats = run_langgraph_benchmark(dataset_name, langgraph_dataset_dir, langgraph_output_dir, r, results_dir)
                    if lg_stats:
                        save_benchmark_row(results_csv_path, dataset_name, lg_stats)
                        lg_results.append(lg_stats)
                except Exception as e:
                    print(f"  [ERROR] LangGraph run {r} failed: {e}")
                    
        # Calculate statistical comparison and print/save summaries
        process_and_save_summary(lei_results, ag_results, lg_results, summary_csv_path)

    print("\n================ BENCHMARK RUN COMPLETED ================\n")

if __name__ == "__main__":
    main()
