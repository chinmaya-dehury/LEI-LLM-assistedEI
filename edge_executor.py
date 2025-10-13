"""
edge_executor.py
----------------
This script simulates the behavior of an Edge Device in an LLM-assisted
Edge Intelligence architecture. It automatically executes all generated
Python programs in the `generated_tasks/` directory and logs the output,
errors, and execution times in a timestamped log file.

Author: Dr. Bivas Panigrahi
Date: 2025-10-09
"""

import os
import subprocess
import time
from datetime import datetime

# === Configuration ===
TASKS_DIR = "generated_tasks"
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
    log(f"\n🟢 Executing: {task_path}")
    log(f"   Start Time: {datetime.now().strftime('%H:%M:%S')}")

    try:
        # Run the script as a subprocess
        result = subprocess.run(
            ["python", task_path],
            capture_output=True,
            text=True,
            timeout=120  # seconds
        )
        duration = time.time() - start_time

        if result.returncode == 0:
            log("   ✅ Status: SUCCESS")
            log(f"   Duration: {duration:.2f} sec")
            log(f"   Output:\n{result.stdout.strip()}")
        else:
            log("   ❌ Status: FAILED")
            log(f"   Duration: {duration:.2f} sec")
            log(f"   Error:\n{result.stderr.strip()}")

    except subprocess.TimeoutExpired:
        log("   ⚠️ Status: TIMEOUT (script exceeded 120s)")
    except Exception as e:
        log(f"   💥 Unexpected Error: {str(e)}")

    log("-" * 60)

def main():
    log(f"🚀 Edge Executor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Scanning directory: {TASKS_DIR}")

    if not os.path.exists(TASKS_DIR):
        log(f"❌ ERROR: Directory '{TASKS_DIR}' not found. Nothing to execute.")
        return

    task_files = [f for f in os.listdir(TASKS_DIR) if f.endswith(".py")]

    if not task_files:
        log("⚠️ No Python tasks found in generated_tasks/. Exiting.")
        return

    log(f"Found {len(task_files)} tasks to execute.")
    log("=" * 60)

    for idx, task in enumerate(sorted(task_files), start=1):
        log(f"\n▶️ Task {idx} of {len(task_files)}")
        task_path = os.path.join(TASKS_DIR, task)
        execute_task(task_path)

    log("\n✅ All tasks executed. Check the log file for details.")
    log(f"Log file saved at: {log_file}")

if __name__ == "__main__":
    main()
