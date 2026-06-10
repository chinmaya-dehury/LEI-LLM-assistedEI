"""
edge_scheduler_sequential.py
------------------------------
Production-grade task orchestration system for edge device task execution.

Architecture:
  APScheduler (scheduling layer)
    ↓
  Task Discovery (find tasks to execute)
    ↓
  Task Queue (manage task ordering)
    ↓
  ProcessPoolExecutor (concurrent execution)
    ↓
  subprocess execution (task isolation)
    ↓
  Validation + Logging + Metrics

Author: Dr. Chinmaya Dehury
Modified: 25-05-2026 (Refactored to production-grade orchestration)
"""

import os
import sys
import json
import subprocess
import time
import signal
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from queue import Queue, PriorityQueue
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
from threading import Lock, Event
import traceback

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logging.warning("APScheduler not installed. Install with: pip install apscheduler")

from config import DATA_TYPE, DEFAULT_MODEL
from shared_utils import (
    sanitize_model_name,
    get_environment_vars,
    setup_timing_paths,
    write_scheduler_detailed_row,
    IST,
)
from resource_monitor import log_resource_metrics


# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

TASKS_DIR = os.path.join("generated_tasks", DATA_TYPE)
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Environment and timing setup
env_vars = get_environment_vars()
RUN_ID = env_vars["RUN_ID"]
RUN_COUNT = env_vars["RUN_COUNT"]
timing_paths = setup_timing_paths(DATA_TYPE, "step4", DEFAULT_MODEL)
STEP4_CSV = timing_paths["STEP_CSV"]
RESOURCE_CSV = timing_paths["RESOURCE_CSV"]

# Logging setup
SCRIPT_START_TIME = datetime.now(IST).isoformat()
SCRIPT_START_PERF = time.perf_counter()

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(LOG_DIR, f"edge_execution_{sanitize_model_name(DEFAULT_MODEL)}_run{RUN_COUNT}_{timestamp}.log")

# Configure Python logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global shutdown event
SHUTDOWN_EVENT = Event()
scheduler_lock = Lock()


# ============================================================================
# TASK DISCOVERY LAYER
# ============================================================================

class TaskDiscovery:
    """Discovers and manages task discovery from filesystem."""
    
    def __init__(self, tasks_dir: str):
        self.tasks_dir = Path(tasks_dir)
    
    def discover_all_tasks(self) -> List[Path]:
        """Discover all executable Python tasks."""
        if not self.tasks_dir.exists():
            logger.error(f"Tasks directory not found: {self.tasks_dir}")
            return []
        
        task_files = sorted(self.tasks_dir.glob("*.py"))
        logger.info(f"Discovered {len(task_files)} tasks in {self.tasks_dir}")
        return task_files
    
    def discover_failed_tasks(self, failed_dir: str = None) -> List[Path]:
        """Discover tasks that previously failed (for retry)."""
        if failed_dir is None:
            failed_dir = self.tasks_dir / "failed"
        
        failed_path = Path(failed_dir)
        if not failed_path.exists():
            return []
        
        return sorted(failed_path.glob("*.py"))


# ============================================================================
# TASK QUEUE LAYER
# ============================================================================

class TaskQueue:
    """Manages task prioritization and ordering."""
    
    def __init__(self, max_retries: int = 2):
        self.queue = PriorityQueue()
        self.max_retries = max_retries
        self.lock = Lock()
    
    def enqueue(self, task_path: Path, priority: int = 0, retry_count: int = 0):
        """Add task to queue with optional priority."""
        with self.lock:
            self.queue.put((priority, task_path, retry_count))
            logger.debug(f"Queued task: {task_path.name} (priority={priority}, retry={retry_count})")
    
    def get_next(self) -> Optional[Tuple[Path, int]]:
        """Get next task from queue."""
        try:
            _, task_path, retry_count = self.queue.get(block=False)
            return task_path, retry_count
        except:
            return None
    
    def size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()


# ============================================================================
# TASK EXECUTION LAYER
# ============================================================================

class TaskExecutor:
    """Executes individual tasks in isolated subprocess."""
    
    TIMEOUT = int(os.environ.get("EDGE_TASK_TIMEOUT_SECONDS", "10"))  # seconds
    
    @staticmethod
    def execute(task_path: Path) -> Dict:
        """
        Execute a task in isolated subprocess.
        
        Returns:
            Dict with keys: stdout, stderr, return_code, duration, parsed_json
        """
        start_time = datetime.now(IST).isoformat()
        start_perf = time.perf_counter()
        
        try:
            result = subprocess.run(
                [sys.executable, str(task_path)],
                capture_output=True,
                text=True,
                timeout=TaskExecutor.TIMEOUT,
                env=os.environ.copy()
            )
            
            duration = time.perf_counter() - start_perf
            
            # Try to parse JSON output
            parsed_json = None
            if result.stdout:
                try:
                    parsed_json = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    pass
            
            return {
                "start_time": start_time,
                "end_time": datetime.now(IST).isoformat(),
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "parsed_json": parsed_json,
                "success": result.returncode == 0,
            }
        
        except subprocess.TimeoutExpired:
            duration = time.perf_counter() - start_perf
            return {
                "start_time": start_time,
                "end_time": datetime.now(IST).isoformat(),
                "duration": duration,
                "stdout": "",
                "stderr": f"Task timeout after {TaskExecutor.TIMEOUT}s",
                "return_code": -1,
                "parsed_json": None,
                "success": False,
            }
        
        except Exception as e:
            duration = time.perf_counter() - start_perf
            return {
                "start_time": start_time,
                "end_time": datetime.now(IST).isoformat(),
                "duration": duration,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}\n{traceback.format_exc()}",
                "return_code": -1,
                "parsed_json": None,
                "success": False,
            }


# ============================================================================
# VALIDATION LAYER
# ============================================================================

class TaskValidator:
    """Validates task execution results."""
    
    @staticmethod
    def looks_like_error(stdout: str, stderr: str) -> bool:
        """Detect error indicators in output."""
        combined = ((stdout or "") + "\n" + (stderr or "")).lower()
        error_indicators = [
            "error", "exception", "traceback", "failed",
            "input file not found", "error:", "typeerror",
            "nameerror", "keyerror", "indexerror"
        ]
        return any(ind in combined for ind in error_indicators)
    
    @staticmethod
    def json_has_error(payload: dict) -> bool:
        """Check if parsed JSON indicates error."""
        if not isinstance(payload, dict):
            return False
        
        status = str(payload.get("status", "")).lower()
        if payload.get("error") or status in {"failed", "error"}:
            return True
        
        result = payload.get("result_summary")
        if isinstance(result, dict):
            result_status = str(result.get("status", "")).lower()
            if result_status in {"failed", "error"} or result.get("error"):
                return True
        
        return False
    
    @staticmethod
    def validate_result(execution_result: Dict) -> Tuple[bool, str]:
        """
        Validate task execution result.
        
        Returns:
            (is_valid, status_message)
        """
        if execution_result["return_code"] == -1:
            return False, execution_result["stderr"]
        
        if execution_result["parsed_json"] is not None:
            if TaskValidator.json_has_error(execution_result["parsed_json"]):
                return False, "JSON payload indicates error"
            if execution_result["return_code"] == 0:
                return True, "Valid JSON output"
            return False, f"Non-zero exit code: {execution_result['return_code']}"
        
        detected_error = TaskValidator.looks_like_error(
            execution_result["stdout"],
            execution_result["stderr"]
        )
        
        if execution_result["return_code"] == 0 and not detected_error:
            return True, "Execution successful"
        
        return False, execution_result["stderr"] or "Execution failed"


# ============================================================================
# LOGGING/METRICS LAYER
# ============================================================================

class ExecutionLogger:
    """Handles logging and CSV metrics for task execution with enhanced output display."""
    
    def __init__(self, csv_path: str, model_name: str, run_count: str):
        self.csv_path = csv_path
        self.model_name = model_name
        self.run_count = run_count
        self.lock = Lock()
        self.task_counter = 0
        self.success_count = 0
        self.failure_count = 0
    
    def _limit_output(self, text: str, max_lines: int = 50) -> str:
        """Limit output to max lines and add indicator if truncated."""
        if not text:
            return ""
        lines = text.split("\n")
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
        return text
    
    def _format_output_section(self, title: str, content: str, is_error: bool = False) -> str:
        """Format output section with visual separators."""
        if not content:
            return ""
        
        separator = "─" * 70
        content_limited = self._limit_output(content, max_lines=50)
        
        if is_error:
            return f"\n{title}:\n{separator}\n{content_limited}\n{separator}"
        else:
            return f"\n{title}:\n{separator}\n{content_limited}\n{separator}"
    
    def _format_json_output(self, json_obj: dict, max_lines: int = 30) -> str:
        """Format JSON output with pretty printing."""
        try:
            json_str = json.dumps(json_obj, indent=2, ensure_ascii=False)
            return self._limit_output(json_str, max_lines=max_lines)
        except:
            return str(json_obj)
    
    def log_execution(self, task_name: str, execution_result: Dict, is_valid: bool, task_num: int = 1, total_tasks: int = 1):
        """Log task execution to CSV and file with enhanced output."""
        with self.lock:
            self.task_counter += 1
            status = "success" if is_valid else "failed"
            if is_valid:
                self.success_count += 1
            else:
                self.failure_count += 1
            
            # Write to CSV
            write_scheduler_detailed_row(
                csv_path=self.csv_path,
                task_name=task_name,
                status=status,
                return_code=execution_result["return_code"],
                script_start_time=execution_result["start_time"],
                script_end_time=execution_result["end_time"],
                script_duration=execution_result["duration"],
                model_name=self.model_name,
                run_count=self.run_count
            )
    
    def log_task_details(self, task_name: str, execution_result: Dict, task_num: int = 1, total_tasks: int = 1):
        """Log detailed task execution with enhanced formatting."""
        is_valid = execution_result["success"]
        status_text = "SUCCESS" if is_valid else "FAILED"
        status_marker = "[OK]" if is_valid else "[FAILED]"
        duration = execution_result["duration"]
        return_code = execution_result["return_code"]
        
        # Task header
        header = f"\n{'=' * 70}\n"
        header += f"[TASK] {task_name} [{task_num}/{total_tasks}]\n"
        header += f"[TIME] {execution_result['start_time']}\n"
        header += f"{status_marker} Status: {status_text}\n"
        header += f"[DURATION] {duration:.3f} seconds\n"
        header += f"[CODE] Return Code: {return_code}\n"
        header += f"{'=' * 70}"
        
        print(header)
        logger.info(header)
        
        # Output sections
        if execution_result["parsed_json"] is not None:
            json_output = self._format_json_output(execution_result["parsed_json"])
            output_section = f"\n[OUTPUT] JSON OUTPUT:\n{'-' * 70}\n{json_output}\n{'-' * 70}"
            print(output_section)
            logger.info(output_section)
        elif execution_result["stdout"]:
            stdout_output = self._limit_output(execution_result["stdout"].strip(), max_lines=100)
            output_section = f"\n[OUTPUT] STDOUT OUTPUT:\n{'-' * 70}\n{stdout_output}\n{'-' * 70}"
            print(output_section)
            logger.info(output_section)
        
        # Error section (if any)
        if execution_result["stderr"]:
            stderr_output = self._limit_output(execution_result["stderr"].strip(), max_lines=50)
            error_section = f"\n[ERROR] ERROR OUTPUT:\n{'-' * 70}\n{stderr_output}\n{'-' * 70}"
            print(error_section)
            logger.warning(error_section)
        
        # Summary box
        summary = f"\n{'-' * 70}\n"
        summary += f"Task: {task_name} | Status: {status_text} | Duration: {duration:.3f}s\n"
        summary += f"{'-' * 70}\n"
        
        print(summary)
        logger.info(summary)
    
    def log_summary(self, total_tasks: int, start_time_perf: float):
        """Log execution summary."""
        total_duration = time.perf_counter() - start_time_perf
        success_rate = (self.success_count / total_tasks * 100) if total_tasks > 0 else 0
        
        summary = f"\n{'=' * 70}\n"
        summary += f"[STATS] EXECUTION SUMMARY\n"
        summary += f"{'=' * 70}\n"
        summary += f"Total Tasks: {total_tasks}\n"
        summary += f"[OK] Successful: {self.success_count}\n"
        summary += f"[FAILED] Failed: {self.failure_count}\n"
        summary += f"[OUTPUT] Success Rate: {success_rate:.1f}%\n"
        summary += f"[DURATION] Total Duration: {total_duration:.2f} seconds\n"
        summary += f"{'=' * 70}\n"
        
        print(summary)
        logger.info(summary)


# ============================================================================
# ORCHESTRATION LAYER
# ============================================================================

class TaskOrchestrator:
    """Main orchestration engine using ProcessPoolExecutor for concurrent execution."""
    
    def __init__(self, tasks_dir: str, worker_pool_size: int = 4, max_retries: int = 2):
        self.discovery = TaskDiscovery(tasks_dir)
        self.task_queue = TaskQueue(max_retries=max_retries)
        self.executor_pool = ProcessPoolExecutor(max_workers=worker_pool_size)
        self.logger = ExecutionLogger(STEP4_CSV, DEFAULT_MODEL, RUN_COUNT)
        self.max_retries = max_retries
        self.worker_pool_size = worker_pool_size
        self.total_tasks = 0
        self.task_counter = 0
        
        # APScheduler setup (optional, for advanced scheduling)
        self.scheduler = None
        if APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
        
        self.active_tasks = {}
        self.completed_tasks = []
        self.failed_tasks = []
    
    def discover_tasks(self) -> List[Path]:
        """Discover all available tasks."""
        return self.discovery.discover_all_tasks()
    
    def queue_tasks(self, task_paths: List[Path]):
        """Queue all discovered tasks."""
        self.total_tasks = len(task_paths)
        for idx, task_path in enumerate(task_paths):
            # Priority: earlier tasks have higher priority (lower number)
            priority = idx
            self.task_queue.enqueue(task_path, priority=priority, retry_count=0)
        
        logger.info(f"Queued {len(task_paths)} tasks for execution")
        print(f"\n[TASK] Total Tasks to Execute: {self.total_tasks}\n")
    
    def execute_single_task(self, task_path: Path, retry_count: int = 0, task_num: int = 1, total_tasks: int = 1) -> Tuple[bool, Dict]:
        """Execute a single task and validate result with enhanced output."""
        task_name = task_path.stem
        
        print(f"\n[WAIT] Executing [{task_num}/{total_tasks}]: {task_name}")
        logger.info(f"Executing [{task_num}/{total_tasks}]: {task_name} (retry={retry_count})")
        
        # Execute task in subprocess
        execution_result = TaskExecutor.execute(task_path)
        
        # Validate result
        is_valid, status_msg = TaskValidator.validate_result(execution_result)
        
        # Log execution with detailed output
        self.logger.log_execution(task_name, execution_result, is_valid, task_num, total_tasks)
        self.logger.log_task_details(task_name, execution_result, task_num, total_tasks)
        
        return is_valid, execution_result
    
    def run_concurrent(self):
        """Execute all queued tasks concurrently."""
        print(f"\n{'=' * 70}")
        print(f"[LAUNCH] STARTING CONCURRENT EXECUTION")
        print(f"{'=' * 70}")
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting concurrent task execution")
        logger.info(f"Worker pool size: {self.worker_pool_size}")
        logger.info(f"Max retries per task: {self.max_retries}")
        logger.info(f"Total tasks to execute: {self.total_tasks}")
        logger.info(f"{'='*60}\n")
        
        futures = {}
        task_metadata = {}
        
        # Submit initial batch of tasks
        while self.task_queue.size() > 0 and len(futures) < self.worker_pool_size:
            task_info = self.task_queue.get_next()
            if task_info:
                task_path, retry_count = task_info
                self.task_counter += 1
                future = self.executor_pool.submit(
                    self.execute_single_task, task_path, retry_count, self.task_counter, self.total_tasks
                )
                futures[future] = task_path
                task_metadata[future] = {"retry_count": retry_count, "task_num": self.task_counter}
        
        # Process completed tasks and queue retries
        while futures or self.task_queue.size() > 0:
            if SHUTDOWN_EVENT.is_set():
                logger.info("Shutdown event received, cancelling pending tasks...")
                for future in futures:
                    future.cancel()
                break
            
            # Wait for any task to complete
            done = set()
            try:
                done, _ = as_completed(futures, timeout=1) if futures else (set(), set())
            except:
                pass
            
            for future in done:
                task_path = futures.pop(future)
                retry_count = task_metadata.pop(future)["retry_count"]
                
                try:
                    is_valid, execution_result = future.result()
                    task_name = task_path.stem
                    
                    if is_valid:
                        self.completed_tasks.append(task_name)
                    else:
                        # Retry logic
                        if retry_count < self.max_retries:
                            logger.warning(
                                f"Task {task_name} failed, retrying... ({retry_count + 1}/{self.max_retries})"
                            )
                            self.task_counter += 1
                            future = self.executor_pool.submit(
                                self.execute_single_task, task_path, retry_count + 1, self.task_counter, self.total_tasks
                            )
                            futures[future] = task_path
                            task_metadata[future] = {"retry_count": retry_count + 1, "task_num": self.task_counter}
                        else:
                            self.failed_tasks.append(task_name)
                            logger.error(f"Task {task_name} failed permanently after {self.max_retries} retries")
                
                except Exception as e:
                    logger.error(f"Error processing task {task_path}: {e}\n{traceback.format_exc()}")
                    self.failed_tasks.append(task_path.stem)
            
            # Submit more tasks if slots available
            while self.task_queue.size() > 0 and len(futures) < self.worker_pool_size:
                task_info = self.task_queue.get_next()
                if task_info:
                    task_path, retry_count = task_info
                    self.task_counter += 1
                    future = self.executor_pool.submit(
                        self.execute_single_task, task_path, retry_count, self.task_counter, self.total_tasks
                    )
                    futures[future] = task_path
                    task_metadata[future] = {"retry_count": retry_count, "task_num": self.task_counter}
        
        # Print and log summary
        self.logger.log_summary(self.total_tasks, SCRIPT_START_PERF)
    
    def run_scheduled(self, interval_minutes: int = 60, max_runs: int = None):
        """Execute tasks on a schedule using APScheduler.
        
        Args:
            interval_minutes: Minutes between task executions
            max_runs: Maximum number of scheduled runs (None = infinite)
        """
        if not APSCHEDULER_AVAILABLE:
            logger.error("APScheduler is not installed. Install with: pip install apscheduler")
            return
        
        if not self.scheduler:
            self.scheduler = BackgroundScheduler()
        
        run_count = {"count": 0}
        
        def scheduled_task():
            """Wrapper for scheduled execution."""
            run_count["count"] += 1
            print(f"\n{'=' * 70}")
            print(f"[TIME] SCHEDULED RUN #{run_count['count']} - {datetime.now(IST).isoformat()}")
            print(f"{'=' * 70}\n")
            logger.info(f"Starting scheduled run #{run_count['count']}")
            
            # Reset state for new run
            self.completed_tasks.clear()
            self.failed_tasks.clear()
            self.task_counter = 0
            
            # Re-discover and queue tasks
            task_paths = self.discover_tasks()
            self.queue_tasks(task_paths)
            
            # Execute tasks
            self.run_concurrent()
            
            # Stop scheduler if max runs reached
            if max_runs and run_count["count"] >= max_runs:
                logger.info(f"Reached max runs ({max_runs}), stopping scheduler")
                self.scheduler.shutdown()
        
        try:
            logger.info(f"Scheduling tasks every {interval_minutes} minutes")
            print(f"\n[SCHEDULE] Scheduler configured: Every {interval_minutes} minutes")
            if max_runs:
                print(f"[SCHEDULE] Max runs: {max_runs}")
            print(f"[SCHEDULE] Press Ctrl+C to stop\n")
            
            self.scheduler.add_job(
                scheduled_task,
                'interval',
                minutes=interval_minutes,
                id='task_scheduler'
            )
            
            self.scheduler.start()
            
            # Keep running
            while self.scheduler.running:
                time.sleep(1)
        
        except (KeyboardInterrupt, SystemExit):
            logger.info("Stopping scheduler due to interrupt")
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown()
        except Exception as e:
            logger.error(f"Scheduler error: {e}\n{traceback.format_exc()}")
    
    def shutdown(self):
        """Gracefully shutdown orchestrator."""
        logger.info("Shutting down task orchestrator...")
        
        if self.executor_pool:
            self.executor_pool.shutdown(wait=True)
        
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
        
        logger.info("Orchestrator shutdown complete")


# ============================================================================
# SIGNAL HANDLING & LIFECYCLE
# ============================================================================

def signal_handler(signum, frame):
    """Handle graceful shutdown on signal."""
    logger.info(f"\nReceived signal {signum}, initiating graceful shutdown...")
    SHUTDOWN_EVENT.set()


def main():
    """Main entry point with support for one-time and scheduled execution."""
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Print startup banner
        banner = f"""
{'=' * 70}
[LAUNCH] EDGE TASK ORCHESTRATOR - PRODUCTION EDITION
{'=' * 70}
[DATE] Start Time: {datetime.now(IST).isoformat()}
[PACKAGE] Data Type: {DATA_TYPE}
[MODEL] Model: {DEFAULT_MODEL}
[FOLDER] Tasks Directory: {TASKS_DIR}
[CONFIG] Worker Pool Size: 4
[DURATION] Max Retries: 2
{'=' * 70}
        """
        print(banner)
        logger.info(banner)
        
        # Log resource metrics at start
        log_resource_metrics(RESOURCE_CSV, "step4_scheduler", "start", 
                            model_name=DEFAULT_MODEL, run_count=RUN_COUNT)
        
        # Initialize orchestrator
        orchestrator = TaskOrchestrator(TASKS_DIR, worker_pool_size=4, max_retries=2)
        
        # Discover tasks
        task_paths = orchestrator.discover_tasks()
        
        if not task_paths:
            logger.error(f"No tasks found in {TASKS_DIR}. Exiting.")
            print(f"\n[ERROR] No tasks found in {TASKS_DIR}\n")
            return
        
        # Check for scheduling mode
        # Set via environment: SCHEDULER_MODE=once (default) or SCHEDULER_MODE=recurring
        # SCHEDULER_INTERVAL_MINUTES=60 (default)
        # SCHEDULER_MAX_RUNS=10 (default=infinite)
        scheduler_mode = os.environ.get("SCHEDULER_MODE", "once").lower()
        scheduler_interval = int(os.environ.get("SCHEDULER_INTERVAL_MINUTES", "60"))
        scheduler_max_runs = os.environ.get("SCHEDULER_MAX_RUNS", "")
        scheduler_max_runs = int(scheduler_max_runs) if scheduler_max_runs else None
        
        if scheduler_mode == "recurring" and APSCHEDULER_AVAILABLE:
            print(f"\n[SCHEDULE] SCHEDULING MODE: Recurring (every {scheduler_interval} minutes)")
            if scheduler_max_runs:
                print(f"[SCHEDULE] Max runs: {scheduler_max_runs}\n")
            logger.info(f"Running in scheduled mode: every {scheduler_interval} minutes")
            
            # Queue tasks for first run
            orchestrator.queue_tasks(task_paths)
            
            # Run scheduled execution
            orchestrator.run_scheduled(interval_minutes=scheduler_interval, max_runs=scheduler_max_runs)
        else:
            # One-time execution
            if scheduler_mode == "recurring" and not APSCHEDULER_AVAILABLE:
                print("\n[WARNING] APScheduler not installed. Running in one-time mode.")
                print("Install APScheduler with: pip install apscheduler\n")
                logger.warning("APScheduler not available, falling back to one-time execution")
            
            print(f"\n[PLAY] EXECUTION MODE: One-Time\n")
            logger.info("Running in one-time execution mode")
            
            # Queue and execute tasks
            orchestrator.queue_tasks(task_paths)
            orchestrator.run_concurrent()
            
            # Shutdown
            orchestrator.shutdown()
        
        # Log resource metrics at end
        log_resource_metrics(RESOURCE_CSV, "step4_scheduler", "end",
                            model_name=DEFAULT_MODEL, run_count=RUN_COUNT)
        
        # Print final summary
        final_summary = f"""
{'=' * 70}
[OK] ORCHESTRATOR COMPLETED
{'=' * 70}
[DATE] End Time: {datetime.now(IST).isoformat()}
[DURATION] Total Duration: {time.perf_counter() - SCRIPT_START_PERF:.2f} seconds
[OUTPUT] Success Rate: {(orchestrator.logger.success_count / orchestrator.total_tasks * 100 if orchestrator.total_tasks > 0 else 0):.1f}%
[LOG] Log File: {log_file}
[OUTPUT] CSV Output: {STEP4_CSV}
{'=' * 70}
        """
        print(final_summary)
        logger.info(final_summary)
        
    except Exception as e:
        logger.error(f"Fatal error in orchestrator: {e}\n{traceback.format_exc()}")
        print(f"\n[ERROR] FATAL ERROR: {str(e)}\n")
        raise
    finally:
        SHUTDOWN_EVENT.set()


if __name__ == "__main__":
    main()

