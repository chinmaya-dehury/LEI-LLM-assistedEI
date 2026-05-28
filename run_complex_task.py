"""
Run a complex task executor and display results.

Usage:
    python run_complex_task.py air_quality_and_wind_pattern_analysis
    python run_complex_task.py --list
"""

import sys
import json
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).parent
COMPLEX_TASKS_DIR = BASE_DIR / "generated_tasks" / "complex"


def list_available_tasks():
    """List all available complex task executors."""
    if not COMPLEX_TASKS_DIR.exists():
        print(f"[ERROR] Complex tasks directory not found: {COMPLEX_TASKS_DIR}")
        return
    
    executors = sorted(COMPLEX_TASKS_DIR.glob("*_executor.py"))
    
    if not executors:
        print("[INFO] No complex task executors found")
        print(f"[INFO] Generate them first: python -m complex_task_synthesis.orchestration")
        return
    
    print(f"\n{'=' * 80}")
    print(f"AVAILABLE COMPLEX TASK EXECUTORS")
    print(f"{'=' * 80}\n")
    
    for idx, executor in enumerate(executors, 1):
        task_name = executor.stem.replace("_executor", "")
        print(f"{idx:2}. {task_name}")
    
    print(f"\n{'=' * 80}")
    print(f"RUN A TASK:")
    print(f"  python run_complex_task.py TASK_NAME")
    print(f"  Example: python run_complex_task.py {executors[0].stem.replace('_executor', '')}")
    print(f"{'=' * 80}\n")


def run_complex_task(task_name: str):
    """Run a complex task executor and display results."""
    
    # Normalize task name
    task_name = task_name.lower().replace("-", "_")
    executor_path = COMPLEX_TASKS_DIR / f"{task_name}_executor.py"
    
    if not executor_path.exists():
        print(f"\n[ERROR] Complex task executor not found: {task_name}")
        print(f"[INFO] Available at: {executor_path}")
        print(f"\nAvailable tasks:")
        list_available_tasks()
        return
    
    print(f"\n{'=' * 80}")
    print(f"[EXECUTE] Running Complex Task: {task_name}")
    print(f"{'=' * 80}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(executor_path)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(result.stdout)
        
        if result.stderr:
            print(f"\n[STDERR]:\n{result.stderr}")
        
        if result.returncode == 0:
            print(f"\n[OK] Task completed successfully")
        else:
            print(f"\n[ERROR] Task failed with return code: {result.returncode}")
        
        return result.returncode == 0
    
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Task execution timeout (>300s)")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to execute task: {e}")
        return False


def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        print("\n[USAGE] python run_complex_task.py TASK_NAME")
        print("[USAGE] python run_complex_task.py --list")
        list_available_tasks()
        return
    
    if sys.argv[1] in ["--list", "-l", "list"]:
        list_available_tasks()
        return
    
    task_name = sys.argv[1]
    success = run_complex_task(task_name)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
