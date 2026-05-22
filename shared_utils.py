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


def ensure_csv_with_headers(csv_path: str, fieldnames: List[str]) -> bool:
    """
    Ensure CSV file exists with headers. Creates file if missing.
    
    Args:
        csv_path: Path to CSV file
        fieldnames: List of column names
        
    Returns:
        True if file was created, False if it already existed
    """
    import os
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    
    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    
    if not file_exists:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        return True
    
    return False
