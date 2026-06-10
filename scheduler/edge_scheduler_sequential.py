"""
edge_executor.py
----------------
This script simulates the behavior of an Edge Device in an LLM-assisted
Edge Intelligence architecture. It automatically executes all generated
Python programs in the `generated_tasks/{DATA_TYPE}` directory and logs the output,
errors, and execution times in a timestamped log file.

Author: Dr. Chinmaya Dehury
Date: 2025-10-09

Last Modified: 14-12-2025
"""

import os
import sys
import csv
# Add parent directory to path so we can import config
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import subprocess
import time
from datetime import datetime, timezone
from config import DATA_TYPE, DEFAULT_MODEL
import json


def _sanitize_model_name(model: str) -> str:
    """Sanitize model name for use in filenames using a shorter version."""
    if not model:
        return "model"
    # Take only the model prefix before ':' to keep filenames clean and short
    short_model = model.split(":")[0]
    return (
        short_model
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


from resource_monitor import log_resource_metrics

# Placeholders for global variables populated in main()
TASKS_DIR = None
LOG_DIR = None
RUN_ID = None
RUN_COUNT = None
SANITIZED_MODEL = None
log_file = None
TIMESTAMP_PATH = None
STEP4_CSV = None
RESOURCE_CSV = None
SCRIPT_START_TIME = None
SCRIPT_START_PERF = None

def log(msg):
    """Helper function to append messages to the log file and print them."""
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def _append_step4_rows(rows):
    os.makedirs(TIMESTAMP_PATH, exist_ok=True)
    file_exists = os.path.exists(STEP4_CSV) and os.path.getsize(STEP4_CSV) > 0
    fieldnames = [
        "step",
        "model",
        "run_count",
        "task_name",
        "script_start_time_ist",
        "script_end_time_ist",
        "script_duration_sec",
        "status",
        "return_code",
    ]

    with open(STEP4_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)

def execute_task(task_path):
    """Execute a single Python task and log results."""
    start_time_utc = datetime.now(timezone.utc).isoformat()
    start_perf = time.perf_counter()
    status = "unknown"
    return_code = None
    log(f"\n Executing: {task_path}")
    log(f"   Start Time: {datetime.now().strftime('%H:%M:%S')}")
    log(f"   Scheduler python: {sys.executable}")

    def looks_like_error(stdout: str, stderr: str) -> bool:
        s = ((stdout or "") + "\n" + (stderr or "")).lower()
        indicators = [
            "error",
            "exception",
            "traceback",
            "failed",
            "input file not found",
            "error:"
        ]
        return any(ind in s for ind in indicators)

    def log_multiline(prefix: str, text: str):
        if not text:
            return
        for line in text.splitlines():
            log(f"{prefix}{line}")

    def json_has_error(payload):
        if isinstance(payload, dict):
            status_val = str(payload.get("status", "")).lower()
            if payload.get("error") or status_val in {"failed", "error"}:
                return True
            result = payload.get("result_summary")
            if isinstance(result, dict):
                result_status = str(result.get("status", "")).lower()
                if result_status in {"failed", "error"} or result.get("error"):
                    return True
        return False

    max_exec_retries = 3
    for attempt in range(max_exec_retries):
        try:
            result = subprocess.run(
                [sys.executable, task_path],
                capture_output=True,
                text=True,
                timeout=int(os.environ.get("EDGE_TASK_TIMEOUT_SECONDS", "10")),  # seconds
                env=os.environ
            )
            duration = time.perf_counter() - start_perf

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            return_code = result.returncode

            # Catch ModuleNotFoundError during task execution
            if "modulenotfounderror" in stderr.lower() or "no module named" in stderr.lower():
                import re
                match = re.search(r"No module named ['\"]([^'\"]+)['\"]", stderr)
                missing_module = None
                if match:
                    missing_module = match.group(1).split('.')[0]
                else:
                    match_alt = re.search(r"No module named ([^\s]+)", stderr)
                    if match_alt:
                        missing_module = match_alt.group(1).split('.')[0]
                
                if missing_module:
                    log(f"[Dynamic Dependency - LEI Executor] Installing missing package: {missing_module}...")
                    try:
                        subprocess.run(
                            [sys.executable, "-m", "pip", "install", missing_module],
                            check=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        # Append to requirements.txt if present
                        req_path = os.path.join(parent_dir, "requirements.txt")
                        if os.path.exists(req_path):
                            with open(req_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            if missing_module not in content:
                                if content and not content.endswith('\n'):
                                    with open(req_path, "a", encoding="utf-8") as f:
                                        f.write("\n")
                                with open(req_path, "a", encoding="utf-8") as f:
                                    f.write(f"{missing_module}\n")
                        continue
                    except Exception as ex:
                        log(f"[WARNING - LEI Executor] Failed to install package {missing_module}: {ex}")

            parsed_json = None
            if stdout:
                try:
                    parsed_json = json.loads(stdout)
                except json.JSONDecodeError:
                    parsed_json = None

            if parsed_json is not None:
                status_val = str(parsed_json.get("status", "")).lower()
                explicit_failed = status_val in {"failed", "error"}
                if result.returncode == 0 and not explicit_failed:
                    log("    Status: SUCCESS")
                    log(f"   Duration: {duration:.2f} sec")
                    log("   Output (JSON):")
                    log_multiline("      ", json.dumps(parsed_json, ensure_ascii=False, indent=2))
                    status = "success"
                else:
                    log("    Status: FAILED")
                    log(f"   Duration: {duration:.2f} sec")
                    log("   Error (JSON):")
                    log_multiline("      ", json.dumps(parsed_json, ensure_ascii=False, indent=2))
                    status = "failed"
            else:
                detected_error = looks_like_error(stdout, stderr)
                success = (result.returncode == 0) and (not detected_error)

                if success:
                    log("    Status: SUCCESS")
                    log(f"   Duration: {duration:.2f} sec")
                    if stdout:
                        log("   Output:")
                        log_multiline("      ", stdout)
                    status = "success"
                else:
                    log("   Status: FAILED")
                    log(f"   Duration: {duration:.2f} sec")
                    if stderr:
                        log("   Error (stderr):")
                        log_multiline("      ", stderr)
                    elif stdout:
                        log("   Error (stdout):")
                        log_multiline("      ", stdout)
                    status = "failed"
            break  # Break retry loop if execution finishes (with success or real failure)

        except subprocess.TimeoutExpired:
            log(f"    Status: TIMEOUT (script exceeded {int(os.environ.get('EDGE_TASK_TIMEOUT_SECONDS', '10'))}s)")
            status = "timeout"
            return_code = -1
            break
        except Exception as e:
            log(f"    Unexpected Error: {str(e)}")
            status = "error"
            return_code = -1
            break

    end_time_ist = datetime.now(timezone.utc).isoformat()
    duration = time.perf_counter() - start_perf
    _append_step4_rows([
        {
            "step": "task_run",
            "model": DEFAULT_MODEL,
            "run_count": RUN_COUNT,
            "task_name": os.path.splitext(os.path.basename(task_path))[0],
            "script_start_time_ist": start_time_utc,
            "script_end_time_ist": end_time_ist,
            "script_duration_sec": duration,
            "status": status,
            "return_code": return_code if return_code is not None else "",
        }
    ])

    log("-" * 60)

def main() -> int:
    global TASKS_DIR, LOG_DIR, RUN_ID, RUN_COUNT, SANITIZED_MODEL, log_file, TIMESTAMP_PATH, STEP4_CSV, RESOURCE_CSV, SCRIPT_START_TIME, SCRIPT_START_PERF

    from resource_monitor import log_resource_metrics

    TASKS_DIR = os.environ.get("LEI_TASKS_DIR", "generated_tasks/"+DATA_TYPE)
    LOG_DIR = "logs"
    os.makedirs(LOG_DIR, exist_ok=True)

    # Use RUN_ID from environment (passed from pipeline) or generate new one
    RUN_ID = os.environ.get("RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # Optional run count (passed from pipeline)
    RUN_COUNT = os.environ.get("RUN_COUNT") or ""
    SANITIZED_MODEL = _sanitize_model_name(DEFAULT_MODEL)

    # Create a timestamped log file with model name and run count
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"edge_execution_{SANITIZED_MODEL}_run{RUN_COUNT}_{timestamp}.log")
    TIMESTAMP_PATH = os.path.join("timestamp_path", DATA_TYPE)
    # Per-run CSV path with model name and run ID (step4 = scheduler)
    STEP4_CSV = os.path.join(TIMESTAMP_PATH, f"step4_{SANITIZED_MODEL}_{RUN_ID}.csv")

    # Script-level timing
    SCRIPT_START_TIME = datetime.now(timezone.utc).isoformat()
    SCRIPT_START_PERF = time.perf_counter()

    # Log resource metrics at start
    RESOURCE_CSV = os.path.join(TIMESTAMP_PATH, f"step4_resource_{SANITIZED_MODEL}_{RUN_ID}.csv")
    log_resource_metrics(RESOURCE_CSV, "step4_scheduler", "start", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)

    # Ensure CSV exists (at least header) even if no tasks run
    _append_step4_rows([])
    
    log(f" Edge Executor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Scanning directory: {TASKS_DIR}")

    if not os.path.exists(TASKS_DIR):
        log(f" ERROR: Directory '{TASKS_DIR}' not found. Nothing to execute.")
        return 1

    task_files = [f for f in os.listdir(TASKS_DIR) if f.endswith(".py")]

    if not task_files:
        log(f" No Python tasks found in {TASKS_DIR}. Exiting.")
        return 0

    log(f"Found {len(task_files)} tasks to execute.")
    log("=" * 60)

    for idx, task in enumerate(sorted(task_files), start=1):
        log(f"\n Task {idx} of {len(task_files)}")
        task_path = os.path.join(TASKS_DIR, task)
        execute_task(task_path)

    log("\n All tasks executed. Check the log file for details.")
    log(f"Log file saved at: {log_file}")

    # Log resource metrics at end
    log_resource_metrics(RESOURCE_CSV, "step4_scheduler", "end", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)
    return 0

if __name__ == "__main__":
    sys.exit(main())