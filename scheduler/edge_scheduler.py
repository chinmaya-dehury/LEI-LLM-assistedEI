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
Modified: 23-05-2026 (Refactored to production-grade orchestration)
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
    
    TIMEOUT = 120  # seconds
    
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
    """Handles logging and CSV metrics for task execution."""
    
    def __init__(self, csv_path: str, model_name: str, run_count: str):
        self.csv_path = csv_path
        self.model_name = model_name
        self.run_count = run_count
        self.lock = Lock()
    
    def log_execution(self, task_name: str, execution_result: Dict, is_valid: bool):
        """Log task execution to CSV and file."""
        with self.lock:
            status = "success" if is_valid else "failed"
            
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
            
            logger.info(
                f"Task {task_name}: {status.upper()} "
                f"(duration={execution_result['duration']:.2f}s, "
                f"return_code={execution_result['return_code']})"
            )
    
    def log_task_details(self, task_name: str, execution_result: Dict, output_sample: int = 500):
        """Log detailed task execution information."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Task: {task_name}")
        logger.info(f"Duration: {execution_result['duration']:.2f}s")
        logger.info(f"Return Code: {execution_result['return_code']}")
        
        if execution_result["stdout"]:
            stdout_sample = execution_result["stdout"][:output_sample]
            logger.info(f"Output: {stdout_sample}...")
        
        if execution_result["stderr"]:
            stderr_sample = execution_result["stderr"][:output_sample]
            logger.warning(f"Errors: {stderr_sample}...")


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
        for idx, task_path in enumerate(task_paths):
            # Priority: earlier tasks have higher priority (lower number)
            priority = idx
            self.task_queue.enqueue(task_path, priority=priority, retry_count=0)
        
        logger.info(f"Queued {len(task_paths)} tasks for execution")
    
    def execute_single_task(self, task_path: Path, retry_count: int = 0) -> Tuple[bool, Dict]:
        """Execute a single task and validate result."""
        task_name = task_path.stem
        
        logger.info(f"\nExecuting task: {task_name} (retry={retry_count})")
        
        # Execute task in subprocess
        execution_result = TaskExecutor.execute(task_path)
        
        # Validate result
        is_valid, status_msg = TaskValidator.validate_result(execution_result)
        
        # Log execution
        self.logger.log_execution(task_name, execution_result, is_valid)
        self.logger.log_task_details(task_name, execution_result)
        
        return is_valid, execution_result
    
    def run_concurrent(self):
        """Execute all queued tasks concurrently."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting concurrent task execution")
        logger.info(f"Worker pool size: {self.worker_pool_size}")
        logger.info(f"Max retries per task: {self.max_retries}")
        logger.info(f"{'='*60}\n")
        
        futures = {}
        task_metadata = {}
        
        # Submit initial batch of tasks
        while self.task_queue.size() > 0 and len(futures) < self.worker_pool_size:
            task_info = self.task_queue.get_next()
            if task_info:
                task_path, retry_count = task_info
                future = self.executor_pool.submit(
                    self.execute_single_task, task_path, retry_count
                )
                futures[future] = task_path
                task_metadata[future] = {"retry_count": retry_count}
        
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
                            self.task_queue.enqueue(task_path, priority=100, retry_count=retry_count + 1)
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
                    future = self.executor_pool.submit(
                        self.execute_single_task, task_path, retry_count
                    )
                    futures[future] = task_path
                    task_metadata[future] = {"retry_count": retry_count}
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Execution Summary:")
        logger.info(f"  Completed: {len(self.completed_tasks)}")
        logger.info(f"  Failed: {len(self.failed_tasks)}")
        logger.info(f"  Total: {len(self.completed_tasks) + len(self.failed_tasks)}")
        logger.info(f"{'='*60}\n")
    
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
    """Main entry point."""
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Log resource metrics at start
        log_resource_metrics(RESOURCE_CSV, "step4_scheduler", "start", 
                            model_name=DEFAULT_MODEL, run_count=RUN_COUNT)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Edge Task Orchestrator Started")
        logger.info(f"Start Time: {datetime.now(IST).isoformat()}")
        logger.info(f"Data Type: {DATA_TYPE}")
        logger.info(f"Tasks Directory: {TASKS_DIR}")
        logger.info(f"Worker Pool Size: 4")
        logger.info(f"{'='*60}\n")
        
        # Initialize orchestrator
        orchestrator = TaskOrchestrator(TASKS_DIR, worker_pool_size=4, max_retries=2)
        
        # Discover tasks
        task_paths = orchestrator.discover_tasks()
        
        if not task_paths:
            logger.error(f"No tasks found in {TASKS_DIR}. Exiting.")
            return
        
        # Queue tasks for execution
        orchestrator.queue_tasks(task_paths)
        
        # Execute tasks concurrently
        orchestrator.run_concurrent()
        
        # Shutdown
        orchestrator.shutdown()
        
        # Log resource metrics at end
        log_resource_metrics(RESOURCE_CSV, "step4_scheduler", "end",
                            model_name=DEFAULT_MODEL, run_count=RUN_COUNT)
        
        logger.info(f"\nEdge Task Orchestrator Completed")
        logger.info(f"End Time: {datetime.now(IST).isoformat()}")
        logger.info(f"Total Duration: {time.perf_counter() - SCRIPT_START_PERF:.2f}s")
        logger.info(f"Log file: {log_file}")
        
    except Exception as e:
        logger.error(f"Fatal error in orchestrator: {e}\n{traceback.format_exc()}")
        raise
    finally:
        SHUTDOWN_EVENT.set()


if __name__ == "__main__":
    main()

