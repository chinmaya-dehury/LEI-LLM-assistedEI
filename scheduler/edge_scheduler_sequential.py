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
from shared_utils import (
    sanitize_model_name,
    get_environment_vars,
    setup_timing_paths,
    IST,
)


from resource_monitor import log_resource_metrics

# === Configuration ===
TASKS_DIR = "generated_tasks/"+DATA_TYPE
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Use RUN_ID from environment and setup timing paths
env_vars = get_environment_vars()
RUN_ID = env_vars["RUN_ID"]
RUN_COUNT = env_vars["RUN_COUNT"]
timing_paths = setup_timing_paths(DATA_TYPE, "step4", DEFAULT_MODEL)
TIMESTAMP_PATH = timing_paths["TIMESTAMP_PATH"]
STEP4_CSV = timing_paths["STEP_CSV"]
RESOURCE_CSV = timing_paths["RESOURCE_CSV"]

# Create a timestamped log file with model name and run count
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(LOG_DIR, f"edge_execution_{sanitize_model_name(DEFAULT_MODEL)}_run{RUN_COUNT}_{timestamp}.log")

# Script-level timing
SCRIPT_START_TIME = datetime.now(timezone.utc).isoformat()
SCRIPT_START_PERF = time.perf_counter()

# Log resource metrics at start
log_resource_metrics(RESOURCE_CSV, "step4_scheduler", "start", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)

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

    try:
        result = subprocess.run(
            [sys.executable, task_path],
            capture_output=True,
            text=True,
            timeout=120,  # seconds
            env=os.environ
        )
        duration = time.perf_counter() - start_perf

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        return_code = result.returncode

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

    except subprocess.TimeoutExpired:
        log("    Status: TIMEOUT (script exceeded 120s)")
        status = "timeout"
        return_code = -1
    except Exception as e:
        log(f"    Unexpected Error: {str(e)}")
        status = "error"
        return_code = -1

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

def main():
    # Ensure CSV exists (at least header) even if no tasks run
    _append_step4_rows([])
    
    log(f" Edge Executor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Scanning directory: {TASKS_DIR}")

    if not os.path.exists(TASKS_DIR):
        log(f" ERROR: Directory '{TASKS_DIR}' not found. Nothing to execute.")
        return

    task_files = [f for f in os.listdir(TASKS_DIR) if f.endswith(".py")]

    if not task_files:
        log(f" No Python tasks found in {TASKS_DIR}. Exiting.")
        return

    log(f"Found {len(task_files)} tasks to execute.")
    log("=" * 60)

    for idx, task in enumerate(sorted(task_files), start=1):
        log(f"\n Task {idx} of {len(task_files)}")
        task_path = os.path.join(TASKS_DIR, task)
        execute_task(task_path)
        print("Sleeping for 5 seconds before next task...\n\n")
        time.sleep(5) # brief pause between tasks

    log("\n All tasks executed. Check the log file for details.")
    log(f"Log file saved at: {log_file}")

    # Log resource metrics at end
    log_resource_metrics(RESOURCE_CSV, "step4_scheduler", "end", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)

if __name__ == "__main__":
    main()
