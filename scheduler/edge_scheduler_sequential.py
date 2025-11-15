"""
edge_executor.py
----------------
This script simulates the behavior of an Edge Device in an LLM-assisted
Edge Intelligence architecture. It automatically executes all generated
Python programs in the `generated_tasks/{DATA_TYPE}` directory and logs the output,
errors, and execution times in a timestamped log file.

Author: Dr. Chinmaya Dehury
Date: 2025-10-09

Last Modified: 15-11-2025
"""

import os
import sys
# Add parent directory to path so we can import config
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import subprocess
import time
from datetime import datetime
from config import DATA_TYPE
import json

# === Configuration ===
TASKS_DIR = "generated_tasks/"+DATA_TYPE
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Create a timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(LOG_DIR, f"edge_execution_{timestamp}.log")

def log(msg):
    """Helper function to append messages to the log file and print them."""
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def execute_task(task_path):
    """Execute a single Python task and log results."""
    start_time = time.time()
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
        duration = time.time() - start_time

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

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
            else:
                log("    Status: FAILED")
                log(f"   Duration: {duration:.2f} sec")
                log("   Error (JSON):")
                log_multiline("      ", json.dumps(parsed_json, ensure_ascii=False, indent=2))
        else:
            detected_error = looks_like_error(stdout, stderr)
            success = (result.returncode == 0) and (not detected_error)

            if success:
                log("    Status: SUCCESS")
                log(f"   Duration: {duration:.2f} sec")
                if stdout:
                    log("   Output:")
                    log_multiline("      ", stdout)
            else:
                log("   Status: FAILED")
                log(f"   Duration: {duration:.2f} sec")
                if stderr:
                    log("   Error (stderr):")
                    log_multiline("      ", stderr)
                elif stdout:
                    log("   Error (stdout):")
                    log_multiline("      ", stdout)

    except subprocess.TimeoutExpired:
        log("    Status: TIMEOUT (script exceeded 120s)")
    except Exception as e:
        log(f"    Unexpected Error: {str(e)}")

    log("-" * 60)

def main():
    log(f" Edge Executor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Scanning directory: {TASKS_DIR}")

    if not os.path.exists(TASKS_DIR):
        log(f" ERROR: Directory '{TASKS_DIR}' not found. Nothing to execute.")
        return

    task_files = [f for f in os.listdir(TASKS_DIR) if f.endswith(".py")]

    if not task_files:
        log(" No Python tasks found in {TASKS_DIR}. Exiting.")
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

if __name__ == "__main__":
    main()
