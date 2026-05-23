"""
shared_utils.py
---------------
Common utility functions shared across all pipeline steps.
Consolidates: model sanitization, JSON extraction, timing/CSV logging, env vars.
"""

import json
import csv
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


# IST Timezone (India Standard Time)
IST = timezone(timedelta(hours=5, minutes=30))


def sanitize_model_name(model: str) -> str:
    """Sanitize model name for use in filenames."""
    return (
        (model or "model")
        .replace(" ", "_")
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def extract_first_json_object(text: str) -> dict:
    """
    Extract first JSON object from text that may contain extra content.
    Handles code fences (```json ... ```) and surrounding text.
    
    Args:
        text: Raw text from LLM that may contain JSON + other content
        
    Returns:
        Parsed JSON object as dict
        
    Raises:
        ValueError: If no valid JSON object found
        json.JSONDecodeError: If JSON parsing fails
    """
    if not isinstance(text, str):
        raise ValueError("Input is not a string")

    s = text.strip()

    # Strip ``` fences if present
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if "```" in s:
            s = s.rsplit("```", 1)[0].strip()

    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object start '{' found in text")

    decoder = json.JSONDecoder()
    obj, _end = decoder.raw_decode(s[start:])
    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON value is not an object")
    return obj


def extract_json_blob(text: str) -> str:
    """
    Extract a JSON object string from text that may contain extra content.
    Returns the JSON string, not parsed.
    """
    if not isinstance(text, str):
        return ""
    
    s = text.strip()
    
    # Strip ``` fences if present
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if "```" in s:
            s = s.rsplit("```", 1)[0].strip()
    
    start = s.find("{")
    if start == -1:
        return ""
    
    try:
        decoder = json.JSONDecoder()
        obj, end = decoder.raw_decode(s[start:])
        return s[start:start + end]
    except Exception:
        return ""


def get_environment_vars() -> Dict[str, str]:
    """
    Get RUN_ID and RUN_COUNT from environment, or generate/default them.
    
    Returns:
        Dict with keys: 'RUN_ID', 'RUN_COUNT'
    """
    run_id = os.environ.get("RUN_ID") or datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    run_count = os.environ.get("RUN_COUNT") or ""
    return {"RUN_ID": run_id, "RUN_COUNT": run_count}


def setup_timing_paths(data_type: str, step_name: str, model_name: str) -> Dict[str, str]:
    """
    Set up all timing/CSV-related paths for a given step.
    
    Args:
        data_type: The DATA_TYPE (e.g., 'temp_humidity', 'air_quality')
        step_name: Step identifier (e.g., 'step1', 'step2', 'step3', 'step4')
        model_name: The LLM model name
        
    Returns:
        Dict with keys:
            - 'TIMESTAMP_PATH': Base path for timestamped files
            - 'STEP_CSV': CSV file for step metrics
            - 'RESOURCE_CSV': CSV file for resource metrics
            - 'RUN_ID': Run ID
            - 'SANITIZED_MODEL': Sanitized model name
    """
    env_vars = get_environment_vars()
    run_id = env_vars["RUN_ID"]
    sanitized_model = sanitize_model_name(model_name)
    
    timestamp_path = os.path.join("timestamp_path", data_type)
    step_csv = os.path.join(timestamp_path, f"{step_name}_{sanitized_model}_{run_id}.csv")
    resource_csv = os.path.join(timestamp_path, f"{step_name}_resource_{sanitized_model}_{run_id}.csv")
    
    return {
        "TIMESTAMP_PATH": timestamp_path,
        "STEP_CSV": step_csv,
        "RESOURCE_CSV": resource_csv,
        "RUN_ID": run_id,
        "SANITIZED_MODEL": sanitized_model,
    }


def append_timing_rows_to_csv(csv_path: str, rows: list, fieldnames: list) -> None:
    """
    Append rows to a CSV file, creating header if file doesn't exist.
    
    Args:
        csv_path: Path to CSV file
        rows: List of dicts to write (one per row)
        fieldnames: List of column names for the CSV
    """
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0

    with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_context_for_data_type(data_type: str) -> Dict[str, Any]:
    """
    Load sample data, metadata, and context for a given data type.
    
    Args:
        data_type: The DATA_TYPE (e.g., 'temp_humidity', 'air_quality')
        
    Returns:
        Dict with keys: 'sample_data', 'metadata', 'context'
    """
    base = os.path.join("data", data_type)
    sample_path = os.path.join(base, "sample_data.csv")
    meta_path = os.path.join(base, "metadata.json")
    context_path = os.path.join(base, "context.txt")

    sample_data = ""
    metadata = {}
    context = ""

    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            sample_data = f.read()

    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            context = f.read()

    return {
        "sample_data": sample_data,
        "metadata": metadata,
        "context": context,
    }


def truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars with ellipsis if needed."""
    if not isinstance(text, str):
        return ""
    return text if len(text) <= max_chars else (text[:max_chars] + "\n... [truncated] ...")


def normalize_code_string(code: str) -> str:
    """
    Convert JSON-escaped/code-fenced text into plain Python source.
    Handles: code fences, escaped newlines, tabs, etc.
    """
    if not isinstance(code, str):
        return ""
    s = code.strip()
    
    # Strip fenced blocks if present
    import re
    if s.startswith("```"):
        s = re.sub(r"^```(?:python)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
    
    # Unescape common sequences if they appear literally
    if "\\r\\n" in s or "\\n" in s or "\\t" in s:
        s = s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    
    return s


def get_current_time_ist() -> str:
    """Get current time in IST timezone as ISO format string."""
    return datetime.now(IST).isoformat()


def get_current_time_perf() -> float:
    """Get current performance counter (for timing measurements)."""
    import time
    return time.perf_counter()


def load_resource_summary(resource_summary_path: str = "resource_stat/resource_usage_summary.json") -> Dict[str, Any]:
    """
    Load resource usage summary from JSON file.
    
    Returns:
        Dict with keys: resource_generated_at, resource_last_checked, avg_cpu_1m, avg_mem_1m, avg_cpu_5m, avg_mem_5m
    """
    default_vals = {
        "resource_generated_at": "",
        "resource_last_checked": "",
        "avg_cpu_1m": "",
        "avg_mem_1m": "",
        "avg_cpu_5m": "",
        "avg_mem_5m": "",
    }
    
    try:
        with open(resource_summary_path, "r", encoding="utf-8") as rf:
            rs = json.load(rf)
            result = {
                "resource_generated_at": rs.get("generated_at", ""),
                "resource_last_checked": rs.get("last_checked", ""),
            }
            sw = rs.get("summary_windows", {}) or {}
            w1 = sw.get("1m", {}) or {}
            w5 = sw.get("5m", {}) or {}
            result["avg_cpu_1m"] = w1.get("avg_cpu", "")
            result["avg_mem_1m"] = w1.get("avg_mem", "")
            result["avg_cpu_5m"] = w5.get("avg_cpu", "")
            result["avg_mem_5m"] = w5.get("avg_mem", "")
            return result
    except Exception:
        return default_vals


def ensure_csv_with_headers(csv_path: str, fieldnames: list) -> bool:
    """
    Ensure CSV file exists with headers. Creates file if missing.
    
    Args:
        csv_path: Path to CSV file
        fieldnames: List of column names
        
    Returns:
        True if file was created, False if it already existed
    """
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    
    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    
    if not file_exists:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        return True
    
    return False


def write_task_generator_csv(csv_path: str, script_start_time: str, script_end_time: str, 
                             script_duration: float, llm_start_time: str, llm_end_time: str, 
                             llm_duration: float, prompt_tokens: int, completion_tokens: int, 
                             total_tokens: int, model_name: str, run_count: str) -> None:
    """
    Write task generator (step1) CSV row with resource summary.
    
    Args:
        csv_path: Path to step1 CSV file
        script_start_time: Script start time (IST ISO format)
        script_end_time: Script end time (IST ISO format)
        script_duration: Total script duration in seconds
        llm_start_time: LLM call start time (IST ISO format)
        llm_end_time: LLM call end time (IST ISO format)
        llm_duration: LLM call duration in seconds
        prompt_tokens: Input tokens count
        completion_tokens: Output tokens count
        total_tokens: Total tokens count
        model_name: LLM model name
        run_count: Run count identifier
    """
    resource_vals = load_resource_summary()
    fieldnames = [
        "step", "model", "run_count", "script_start_time_ist", "script_end_time_ist",
        "script_duration_sec", "llm_start_time_ist", "llm_end_time_ist", "llm_duration_sec",
        "prompt_tokens", "completion_tokens", "total_tokens", "prompt_tokens_per_sec",
        "completion_tokens_per_sec", "resource_generated_at", "resource_last_checked",
        "avg_cpu_1m", "avg_mem_1m", "avg_cpu_5m", "avg_mem_5m"
    ]
    prompt_tps = prompt_tokens / llm_duration if llm_duration > 0 else 0
    completion_tps = completion_tokens / llm_duration if llm_duration > 0 else 0
    
    append_timing_rows_to_csv(csv_path, [{
        "step": "llm_call",
        "model": model_name,
        "run_count": run_count,
        "script_start_time_ist": script_start_time,
        "script_end_time_ist": script_end_time,
        "script_duration_sec": script_duration,
        "llm_start_time_ist": llm_start_time,
        "llm_end_time_ist": llm_end_time,
        "llm_duration_sec": llm_duration,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_per_sec": prompt_tps,
        "completion_tokens_per_sec": completion_tps,
        **resource_vals,
    }], fieldnames)


def write_code_generator_csv(csv_path: str, script_start_time: str, script_end_time: str,
                             script_duration: float, llm_start_time: str, llm_end_time: str,
                             llm_duration: float, prompt_tokens: int, completion_tokens: int,
                             total_tokens: int, model_name: str, run_count: str, 
                             task_name: str = "") -> None:
    """
    Write code generator (step2) CSV row with resource summary and task info.
    
    Args:
        csv_path: Path to step2 CSV file
        script_start_time: Script start time (IST ISO format)
        script_end_time: Script end time (IST ISO format)
        script_duration: Total script duration in seconds
        llm_start_time: LLM call start time (IST ISO format)
        llm_end_time: LLM call end time (IST ISO format)
        llm_duration: LLM call duration in seconds
        prompt_tokens: Input tokens count
        completion_tokens: Output tokens count
        total_tokens: Total tokens count
        model_name: LLM model name
        run_count: Run count identifier
        task_name: Name of the task being processed
    """
    resource_vals = load_resource_summary()
    fieldnames = [
        "step", "model", "run_count", "task_name", "script_start_time_ist", "script_end_time_ist",
        "script_duration_sec", "llm_start_time_ist", "llm_end_time_ist", "llm_duration_sec",
        "prompt_tokens", "completion_tokens", "total_tokens", "prompt_tokens_per_sec",
        "completion_tokens_per_sec", "resource_generated_at", "resource_last_checked",
        "avg_cpu_1m", "avg_mem_1m", "avg_cpu_5m", "avg_mem_5m"
    ]
    prompt_tps = prompt_tokens / llm_duration if llm_duration > 0 else 0
    completion_tps = completion_tokens / llm_duration if llm_duration > 0 else 0
    
    append_timing_rows_to_csv(csv_path, [{
        "step": "code_gen",
        "model": model_name,
        "run_count": run_count,
        "task_name": task_name,
        "script_start_time_ist": script_start_time,
        "script_end_time_ist": script_end_time,
        "script_duration_sec": script_duration,
        "llm_start_time_ist": llm_start_time,
        "llm_end_time_ist": llm_end_time,
        "llm_duration_sec": llm_duration,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_per_sec": prompt_tps,
        "completion_tokens_per_sec": completion_tps,
        **resource_vals,
    }], fieldnames)


def write_validator_csv(csv_path: str, script_start_time: str, script_end_time: str,
                        script_duration: float, llm_start_time: str, llm_end_time: str,
                        llm_duration: float, prompt_tokens: int, completion_tokens: int,
                        total_tokens: int, model_name: str, run_count: str,
                        task_name: str = "", validation_status: str = "") -> None:
    """
    Write validator (step3) CSV row with resource summary, task info, and validation status.
    
    Args:
        csv_path: Path to step3 CSV file
        script_start_time: Script start time (IST ISO format)
        script_end_time: Script end time (IST ISO format)
        script_duration: Total script duration in seconds
        llm_start_time: LLM call start time (IST ISO format)
        llm_end_time: LLM call end time (IST ISO format)
        llm_duration: LLM call duration in seconds
        prompt_tokens: Input tokens count
        completion_tokens: Output tokens count
        total_tokens: Total tokens count
        model_name: LLM model name
        run_count: Run count identifier
        task_name: Name of the task being validated
        validation_status: Validation result (e.g., "passed", "corrected", "failed")
    """
    resource_vals = load_resource_summary()
    fieldnames = [
        "step", "model", "run_count", "task_name", "validation_status", "script_start_time_ist",
        "script_end_time_ist", "script_duration_sec", "llm_start_time_ist", "llm_end_time_ist",
        "llm_duration_sec", "prompt_tokens", "completion_tokens", "total_tokens",
        "prompt_tokens_per_sec", "completion_tokens_per_sec", "resource_generated_at",
        "resource_last_checked", "avg_cpu_1m", "avg_mem_1m", "avg_cpu_5m", "avg_mem_5m"
    ]
    prompt_tps = prompt_tokens / llm_duration if llm_duration > 0 else 0
    completion_tps = completion_tokens / llm_duration if llm_duration > 0 else 0
    
    append_timing_rows_to_csv(csv_path, [{
        "step": "validate",
        "model": model_name,
        "run_count": run_count,
        "task_name": task_name,
        "validation_status": validation_status,
        "script_start_time_ist": script_start_time,
        "script_end_time_ist": script_end_time,
        "script_duration_sec": script_duration,
        "llm_start_time_ist": llm_start_time,
        "llm_end_time_ist": llm_end_time,
        "llm_duration_sec": llm_duration,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_per_sec": prompt_tps,
        "completion_tokens_per_sec": completion_tps,
        **resource_vals,
    }], fieldnames)


def write_scheduler_csv(csv_path: str, script_start_time: str, script_end_time: str,
                        script_duration: float, model_name: str, run_count: str,
                        task_name: str = "", execution_status: str = "") -> None:
    """
    Write scheduler (step4) CSV row with resource summary and execution info.
    
    Args:
        csv_path: Path to step4 CSV file
        script_start_time: Script start time (IST ISO format)
        script_end_time: Script end time (IST ISO format)
        script_duration: Task execution duration in seconds
        model_name: LLM model name (for consistency)
        run_count: Run count identifier
        task_name: Name of the task executed
        execution_status: Execution result (e.g., "success", "timeout", "error")
    """
    resource_vals = load_resource_summary()
    fieldnames = [
        "step", "model", "run_count", "task_name", "execution_status", "script_start_time_ist",
        "script_end_time_ist", "script_duration_sec", "resource_generated_at", "resource_last_checked",
        "avg_cpu_1m", "avg_mem_1m", "avg_cpu_5m", "avg_mem_5m"
    ]
    
    append_timing_rows_to_csv(csv_path, [{
        "step": "execute",
        "model": model_name,
        "run_count": run_count,
        "task_name": task_name,
        "execution_status": execution_status,
        "script_start_time_ist": script_start_time,
        "script_end_time_ist": script_end_time,
        "script_duration_sec": script_duration,
        **resource_vals,
    }], fieldnames)


def write_scheduler_detailed_row(csv_path: str, task_name: str, status: str, return_code: int = None,
                                  script_start_time: str = "", script_end_time: str = "",
                                  script_duration: float = 0.0, model_name: str = "", 
                                  run_count: str = "") -> None:
    """
    Write a detailed scheduler/executor CSV row for task execution tracking.
    Used by edge_scheduler_sequential.py for logging task runs.
    
    Args:
        csv_path: Path to scheduler CSV file
        task_name: Name of the task executed
        status: Execution status (success, failed, timeout, error)
        return_code: Process return code (None, 0, or error code)
        script_start_time: Task start time (IST ISO format)
        script_end_time: Task end time (IST ISO format)
        script_duration: Task execution duration in seconds
        model_name: LLM model name (for consistency)
        run_count: Run count identifier
    """
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    
    fieldnames = [
        "step", "model", "run_count", "task_name",
        "script_start_time_ist", "script_end_time_ist", "script_duration_sec",
        "status", "return_code",
    ]
    
    append_timing_rows_to_csv(csv_path, [{
        "step": "task_run",
        "model": model_name,
        "run_count": run_count,
        "task_name": task_name,
        "script_start_time_ist": script_start_time,
        "script_end_time_ist": script_end_time,
        "script_duration_sec": script_duration if script_duration else "",
        "status": status,
        "return_code": return_code if return_code is not None else "",
    }], fieldnames)


def write_validator_detailed_row(csv_path: str, step: str, model_name: str, run_count: str,
                                  task_name: str, status: str, attempt: str = "",
                                  script_start_time: str = "", script_end_time: str = "",
                                  script_duration: float = 0.0, llm_start_time: str = "",
                                  llm_end_time: str = "", llm_duration: float = 0.0,
                                  prompt_tokens: int = 0, completion_tokens: int = 0,
                                  total_tokens: int = 0) -> None:
    """
    Write a detailed validator CSV row with multiple fields for tracking validation steps.
    Handles various validation statuses: initial_run, llm_call, llm_call_failed, etc.
    
    Args:
        csv_path: Path to validator CSV file
        step: Step identifier (e.g., "initial_run", "llm_call", "llm_call_failed", "validation")
        model_name: LLM model name
        run_count: Run count identifier
        task_name: Name of the task being validated
        status: Validation status (e.g., "passed", "failed", "initial_validation")
        attempt: Attempt number (can be empty string for non-retry steps)
        script_start_time: Script start time (IST ISO format)
        script_end_time: Script end time (IST ISO format)
        script_duration: Total duration in seconds
        llm_start_time: LLM call start time (empty if no LLM call)
        llm_end_time: LLM call end time (empty if no LLM call)
        llm_duration: LLM call duration in seconds (0 if no LLM call)
        prompt_tokens: Input tokens count (0 if no LLM call)
        completion_tokens: Output tokens count (0 if no LLM call)
        total_tokens: Total tokens count (0 if no LLM call)
    """
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    
    fieldnames = [
        "step", "model", "run_count", "task_name", "status", "attempt",
        "script_start_time_ist", "script_end_time_ist", "script_duration_sec",
        "llm_start_time_ist", "llm_end_time_ist", "llm_duration_sec",
        "prompt_tokens", "completion_tokens", "total_tokens",
        "prompt_tokens_per_sec", "completion_tokens_per_sec",
    ]
    
    # Calculate tokens per second
    prompt_tps = prompt_tokens / llm_duration if llm_duration > 0 else ""
    completion_tps = completion_tokens / llm_duration if llm_duration > 0 else ""
    
    append_timing_rows_to_csv(csv_path, [{
        "step": step,
        "model": model_name,
        "run_count": run_count,
        "task_name": task_name,
        "status": status,
        "attempt": attempt,
        "script_start_time_ist": script_start_time,
        "script_end_time_ist": script_end_time,
        "script_duration_sec": script_duration if script_duration else "",
        "llm_start_time_ist": llm_start_time,
        "llm_end_time_ist": llm_end_time,
        "llm_duration_sec": llm_duration if llm_duration else "",
        "prompt_tokens": prompt_tokens if prompt_tokens else "",
        "completion_tokens": completion_tokens if completion_tokens else "",
        "total_tokens": total_tokens if total_tokens else "",
        "prompt_tokens_per_sec": prompt_tps,
        "completion_tokens_per_sec": completion_tps,
    }], fieldnames)
