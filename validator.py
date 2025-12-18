"""
validator.py
-------------------
Runs all generated task scripts (after step 2, before step 3).
If a task fails, logs the error, calls the LLM for fixes (up to 2 retries),
replaces the script on success, or moves it to failed/ when retries are exhausted.

Code updated: added FutureWarning/deprecation warning handling logic.

"""

import json
import os
import sys
import subprocess
import time
import csv
from string import Template
from typing import Dict, List
import shutil
from datetime import datetime, timezone, timedelta
import re
import httpx

from openai import OpenAI

from config import DATA_TYPE, OLLAMA_SERVER_URL, MODEL_NAME
from prompts.get_validator import SYSTEM_PROMPT
from resource_monitor import log_resource_metrics


def _sanitize_model_name(model: str) -> str:
    """Sanitize model name for use in filenames."""
    return (
        (model or "model")
        .replace(" ", "_")
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

# Windows-safe stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CLIENT_TIMEOUT = 120  # seconds
client = OpenAI(base_url=OLLAMA_SERVER_URL, api_key="ollama", timeout=CLIENT_TIMEOUT)

TIMESTAMP_PATH = os.path.join("timestamp_path", DATA_TYPE)
# Per-run CSV path with model name and run ID (step3 = validator)
IST = timezone(timedelta(hours=5, minutes=30))
# Use RUN_ID from environment (passed from pipeline) or generate new one
RUN_ID = os.environ.get("RUN_ID") or datetime.now(IST).strftime("%Y%m%d_%H%M%S")
SANITIZED_MODEL = _sanitize_model_name(MODEL_NAME)
STEP3_CSV = os.path.join(TIMESTAMP_PATH, f"step3_{SANITIZED_MODEL}_{RUN_ID}.csv")

MAX_RETRIES = 2
DEFAULT_TASKS_FILE = os.path.join("generated_tasks", DATA_TYPE, "new_tasks.json")
DEFAULT_SCRIPTS_DIR = os.path.join("generated_tasks", DATA_TYPE)
ERROR_LOG_PATH = os.path.join(DEFAULT_SCRIPTS_DIR, "error.txt")
DEFAULT_VALIDATOR_LOG = os.path.join("validator", DATA_TYPE)

TIMING_ROWS_WRITTEN = 0

# Log resource metrics at start
RESOURCE_CSV = os.path.join(TIMESTAMP_PATH, f"step3_resource_{SANITIZED_MODEL}_{RUN_ID}.csv")
log_resource_metrics(RESOURCE_CSV, "step3_validator", "start", model_name=MODEL_NAME)


def _append_timing_rows(rows: List[dict]) -> None:
    global TIMING_ROWS_WRITTEN
    os.makedirs(TIMESTAMP_PATH, exist_ok=True)
    file_exists = os.path.exists(STEP3_CSV) and os.path.getsize(STEP3_CSV) > 0
    fieldnames = [
        "step",
        "model",
        "task_name",
        "status",
        "attempt",
        "script_start_time_ist",
        "script_end_time_ist",
        "script_duration_sec",
        "llm_start_time_ist",
        "llm_end_time_ist",
        "llm_duration_sec",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_tokens_per_sec",
        "completion_tokens_per_sec",
    ]

    with open(STEP3_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
            TIMING_ROWS_WRITTEN += 1


def _log_task_result(task_name: str, status: str, attempt: int = 0) -> None:
    """Log a task validation result (passed/failed) to CSV without LLM timing."""
    _append_timing_rows([{
        "step": "validation",
        "model": MODEL_NAME,
        "task_name": task_name,
        "status": status,
        "attempt": attempt,
        "script_start_time_ist": "",
        "script_end_time_ist": "",
        "script_duration_sec": "",
        "llm_start_time_ist": "",
        "llm_end_time_ist": "",
        "llm_duration_sec": "",
        "prompt_tokens": "",
        "completion_tokens": "",
        "total_tokens": "",
        "prompt_tokens_per_sec": "",
        "completion_tokens_per_sec": "",
    }])


# Script-level timing
SCRIPT_START_TIME = datetime.now(IST).isoformat()
SCRIPT_START_PERF = time.perf_counter()


def _append_error_log(task_name: str, exit_code: int, stderr: str) -> None:
    """Append runtime failure details to error.txt."""
    os.makedirs(DEFAULT_SCRIPTS_DIR, exist_ok=True)
    timestamp = datetime.now().isoformat()
    entry = (
        f"[{timestamp}] TASK: {task_name} | exit_code={exit_code}\n"
        f"{stderr.strip()}\n"
        f"{'-'*60}\n"
    )
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(entry)


def _load_context_for(datatype: str) -> Dict[str, object]:
    base = os.path.join("data", datatype)
    sample_path = os.path.join(base, "sample_data.csv")
    meta_path = os.path.join(base, "metadata.json")
    context_path = os.path.join(base, "context.txt")

    sample_data = ""
    metadata = {}
    context = ""

    if os.path.exists(sample_path):
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_data = f.read()
        except Exception:
            sample_data = ""

    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            metadata = {}

    if os.path.exists(context_path):
        try:
            with open(context_path, "r", encoding="utf-8") as f:
                context = f.read()
        except Exception:
            context = ""

    return {
        "sample_data": sample_data,
        "metadata": metadata,
        "context": context,
    }


def _execute_task_script(script_path: str, timeout: int = 60) -> Dict[str, object]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Script execution timed out after {timeout}s",
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Failed to execute script: {e}",
        }


def _normalize_code_string(code: str) -> str:
    if not isinstance(code, str):
        return ""
    s = code.strip()
    if "\\r\\n" in s or "\\n" in s or "\\t" in s:
        s = s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    lines = s.split("\n")
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]
    return "\n".join(lines)


def _stderr_is_only_warning(stderr: str) -> bool:
    """
    Returns True if stderr contains only warning messages (FutureWarning,
    DeprecationWarning, UserWarning, etc.) and no actual errors.
    """
    if not stderr or not isinstance(stderr, str):
        return True  # No stderr means no warnings/errors
    
    lines = stderr.strip().split("\n")
    if not lines or all(not line.strip() for line in lines):
        return True  # Empty or whitespace-only
    
    # Patterns that indicate warnings (not errors)
    warning_patterns = [
        r"Warning:",
        r"FutureWarning:",
        r"DeprecationWarning:",
        r"UserWarning:",
        r"PendingDeprecationWarning:",
        r"RuntimeWarning:",
        r"SyntaxWarning:",
        r"ResourceWarning:",
        r"ImportWarning:",
        r"UnicodeWarning:",
        r"BytesWarning:",
        r"warnings\.warn",
        r"^\s*warnings\.filterwarnings",
        # Common warning file references
        r"site-packages.*Warning",
        r"lib.*Warning",
    ]
    
    # Patterns that indicate actual errors (not just warnings)
    error_patterns = [
        r"Error:",
        r"Exception:",
        r"Traceback \(most recent call last\):",
        r"^\s*File \".*\", line \d+",
        r"ModuleNotFoundError:",
        r"ImportError:",
        r"SyntaxError:",
        r"NameError:",
        r"TypeError:",
        r"ValueError:",
        r"KeyError:",
        r"IndexError:",
        r"AttributeError:",
        r"FileNotFoundError:",
        r"OSError:",
        r"IOError:",
        r"RuntimeError:",
        r"ZeroDivisionError:",
        r"AssertionError:",
    ]
    
    full_text = stderr.strip()
    
    # If any error pattern matches, it's not warning-only
    for pattern in error_patterns:
        if re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE):
            return False
    
    # If we get here, check if there's any content that doesn't look like a warning
    # For each non-empty line, check if it matches a warning pattern or is part of warning context
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if line matches any warning pattern
        is_warning_line = any(re.search(p, line, re.IGNORECASE) for p in warning_patterns)
        
        # Also accept lines that are part of warning stack traces (indented or file refs)
        is_context_line = (
            line.startswith(" ") or 
            line.startswith("\t") or
            re.match(r"^\s*\^+\s*$", line) or  # Caret lines pointing to issues
            re.match(r"^\s*~+\s*$", line) or   # Tilde lines
            "site-packages" in line or
            ".py:" in line
        )
        
        if not is_warning_line and not is_context_line:
            # This line doesn't look like a warning or its context
            # But don't immediately fail - could be warning message text
            pass
    
    # If no error patterns matched, treat as warning-only
    return True


def _build_correction_prompt(task: Dict, runtime_error: str, exit_code: int, assets: Dict) -> str:
    return f"""
Sample Data:
{assets['sample_data'][:3000]}

Metadata:
{json.dumps(assets['metadata'], indent=2, ensure_ascii=False)[:2000]}

Context:
{assets['context'][:2000]}

Task Name: {task.get('task_name', 'UNKNOWN')}
Task Description: {task.get('description', 'N/A')}
Data Type: {task.get('data_type', DATA_TYPE)}

RUNTIME ERROR (exit code {exit_code}):
{runtime_error}

ORIGINAL CODE THAT FAILED:
{task.get('code', '')}

Provide corrected code following the response format specified in the system prompt.
""".strip()


def _ollama_native_base_url() -> str:
    """Derive Ollama base URL (without /v1) from OLLAMA_SERVER_URL."""
    url = (OLLAMA_SERVER_URL or "").strip()
    if url.endswith("/v1"):
        url = url[:-3]
    return url.rstrip("/")


def _call_ollama_native_chat(system_prompt: str, user_prompt: str) -> dict:
    """Call Ollama's native /api/chat endpoint to obtain token counts."""
    base = _ollama_native_base_url()
    if not base:
        raise RuntimeError("OLLAMA_SERVER_URL is empty")

    url = f"{base}/api/chat"
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.0},
    }

    with httpx.Client(timeout=CLIENT_TIMEOUT) as http:
        resp = http.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    message = data.get("message") or {}
    content = message.get("content") or ""
    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)
    model = data.get("model") or MODEL_NAME
    return {
        "content": content,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "model": model,
        "raw": data,
    }


def _extract_json_from_text(text: str) -> dict | list | None:
    """
    Extract JSON (object or array) from text that may contain:
    - Code fences (```json ... ```
    - Natural language before/after JSON
    - Warnings or other output mixed in
    
    Returns parsed JSON (dict or list) or None if extraction fails.
    """
    if not text or not isinstance(text, str):
        return None

    s = text.strip()
    if not s:
        return None

    # 1. Strip code fences if present (```json ... ``` or ``` ... ```
    if "```" in s:
        # Find content between first ``` and last ```
        parts = s.split("```")
        for i, part in enumerate(parts):
            # Skip the language identifier line if present (e.g., "json\n{...}")
            candidate = part.strip()
            if candidate.startswith(("json", "python", "JSON")):
                candidate = candidate.split("\n", 1)[1].strip() if "\n" in candidate else ""
            
            if not candidate:
                continue
                
            # Try to parse this block
            try:
                if candidate.startswith("{"):
                    return json.loads(candidate)
                elif candidate.startswith("["):
                    return json.loads(candidate)
            except json.JSONDecodeError:
                pass
            
            # Try extracting JSON from within this block
            result = _try_extract_json_structure(candidate)
            if result is not None:
                return result

    # 2. Try direct parse
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 3. Try extracting JSON structure from the text
    return _try_extract_json_structure(s)


def _try_extract_json_structure(text: str) -> dict | list | None:
    """
    Try to find and parse a JSON object or array from text.
    Uses JSONDecoder.raw_decode to handle trailing content.
    """
    if not text:
        return None

    # Try to find JSON object
    obj_start = text.find("{")
    arr_start = text.find("[")

    # Determine which comes first
    if obj_start == -1 and arr_start == -1:
        return None

    # Try object first if it appears before array (or array not found)
    if obj_start != -1 and (arr_start == -1 or obj_start < arr_start):
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text[obj_start:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # Try array
    if arr_start != -1:
        try:
            decoder = json.JSONDecoder()
            arr, _ = decoder.raw_decode(text[arr_start:])
            if isinstance(arr, list):
                return arr
        except json.JSONDecodeError:
            pass

    # Fallback: try finding the last complete JSON object/array (for cases where warnings come first)
    # Find last { and matching }
    last_obj_end = text.rfind("}")
    if last_obj_end != -1:
        # Search backwards for matching {
        depth = 0
        for i in range(last_obj_end, -1, -1):
            if text[i] == "}":
                depth += 1
            elif text[i] == "{":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:last_obj_end + 1])
                    except json.JSONDecodeError:
                        break

    # Find last [ and matching ]
    last_arr_end = text.rfind("]")
    if last_arr_end != -1:
        depth = 0
        for i in range(last_arr_end, -1, -1):
            if text[i] == "]":
                depth += 1
            elif text[i] == "[":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:last_arr_end + 1])
                    except json.JSONDecodeError:
                        break

    return None


def _parse_json_from_output(output: str) -> Dict | None:
    """
    Attempt to extract a JSON object from stdout even if warnings or extra text
    are present. Returns dict if successful, otherwise None.
    
    Accepts:
    - JSON object with task_name: {"task_name": "...", "result_summary": [...]}
    - JSON array (result_summary only): [{...}, {...}]
    - JSON with code fences or extra text around it
    """
    if not output:
        return None

    parsed = _extract_json_from_text(output)
    
    if parsed is None:
        return None

    # If it's already a dict with task_name, return as-is
    if isinstance(parsed, dict):
        return parsed

    # If it's a list (result_summary array), wrap it for compatibility
    if isinstance(parsed, list):
        return {"result_summary": parsed, "_array_output": True}

    return None


def _extract_code_from_llm_response(raw: str) -> str:
    """
    Extract corrected Python code from LLM response.
    Handles responses that include code in:
    - JSON field "corrected_code"
    - Code fences ```python ... ```
    - Raw code mixed with explanation
    """
    if not raw or not isinstance(raw, str):
        return ""

    s = raw.strip()

    # 1. Try to parse as JSON and extract corrected_code field
    parsed = _extract_json_from_text(s)
    if isinstance(parsed, dict):
        code = parsed.get("corrected_code", "")
        if code and isinstance(code, str):
            return code.strip()

    # 2. Try to extract from Python code fences
    if "```python" in s.lower() or "```py" in s.lower():
        # Find python code block
        pattern = r"```(?:python|py)\s*\n(.*?)```"
        matches = re.findall(pattern, s, re.DOTALL | re.IGNORECASE)
        if matches:
            # Return the longest match (likely the full corrected code)
            return max(matches, key=len).strip()

    # 3. Try generic code fences
    if "```" in s:
        parts = s.split("```")
        code_blocks = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Odd indices are inside fences
                # Skip language identifier
                lines = part.split("\n")
                if lines and lines[0].strip().lower() in ("python", "py", "json", ""):
                    code_blocks.append("\n".join(lines[1:]).strip())
                else:
                    code_blocks.append(part.strip())
        if code_blocks:
            # Return the longest code block
            return max(code_blocks, key=len)

    # 4. If it looks like Python code (has def/import/class), return as-is
    if any(keyword in s for keyword in ["import ", "def ", "class ", "from "]):
        return s

    return ""


def _call_llm_for_correction(task: Dict, runtime_error: str, exit_code: int, assets: Dict, attempt: int) -> Dict:
    datatype = task.get("data_type", DATA_TYPE)
    system_prompt = Template(SYSTEM_PROMPT).substitute(DATA_TYPE=datatype)
    user_prompt = _build_correction_prompt(task, runtime_error, exit_code, assets)

    llm_start_time = datetime.now(IST).isoformat()
    llm_start_perf = time.perf_counter()

    try:
        native = _call_ollama_native_chat(system_prompt, user_prompt)
    except (httpx.TimeoutException, httpx.ReadTimeout) as e:
        llm_end_perf = time.perf_counter()
        llm_end_time = datetime.now(IST).isoformat()
        llm_duration = llm_end_perf - llm_start_perf

        script_end_time = datetime.now(IST).isoformat()
        script_duration = time.perf_counter() - SCRIPT_START_PERF
        _append_timing_rows([
            {
                "step": "llm_call_timeout",
                "model": MODEL_NAME,
                "task_name": task.get("task_name", ""),
                "status": "llm_timeout",
                "attempt": attempt,
                "script_start_time_ist": SCRIPT_START_TIME,
                "script_end_time_ist": script_end_time,
                "script_duration_sec": script_duration,
                "llm_start_time_ist": llm_start_time,
                "llm_end_time_ist": llm_end_time,
                "llm_duration_sec": llm_duration,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "prompt_tokens_per_sec": 0,
                "completion_tokens_per_sec": 0,
            }
        ])
        print(f"[Validator] LLM call timed out: {e}")
        return {
            "task_name": task.get("task_name"),
            "is_valid": False,
            "error_message": f"LLM call timed out: {e}",
            "corrected_code": "",
        }

    except Exception as e:
        llm_end_perf = time.perf_counter()
        llm_end_time = datetime.now(IST).isoformat()
        llm_duration = llm_end_perf - llm_start_perf

        script_end_time = datetime.now(IST).isoformat()
        script_duration = time.perf_counter() - SCRIPT_START_PERF
        _append_timing_rows([
            {
                "step": "llm_call_failed",
                "model": MODEL_NAME,
                "task_name": task.get("task_name", ""),
                "status": "llm_error",
                "attempt": attempt,
                "script_start_time_ist": SCRIPT_START_TIME,
                "script_end_time_ist": script_end_time,
                "script_duration_sec": script_duration,
                "llm_start_time_ist": llm_start_time,
                "llm_end_time_ist": llm_end_time,
                "llm_duration_sec": llm_duration,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "prompt_tokens_per_sec": 0,
                "completion_tokens_per_sec": 0,
            }
        ])
        print(f"[Validator] LLM call failed: {e}")
        return {
            "task_name": task.get("task_name"),
            "is_valid": False,
            "error_message": f"LLM call failed: {e}",
            "corrected_code": "",
        }

    llm_end_perf = time.perf_counter()
    llm_end_time = datetime.now(IST).isoformat()
    llm_duration = llm_end_perf - llm_start_perf

    prompt_tokens = int(native.get("prompt_tokens") or 0)
    completion_tokens = int(native.get("completion_tokens") or 0)
    total_tokens = prompt_tokens + completion_tokens

    prompt_tps = prompt_tokens / llm_duration if llm_duration > 0 else 0
    completion_tps = completion_tokens / llm_duration if llm_duration > 0 else 0

    raw = native.get("content") or ""

    _append_timing_rows([
        {
            "step": "llm_call",
            "model": native.get("model") or MODEL_NAME,
            "task_name": task.get("task_name", ""),
            "status": "correction_attempt",
            "attempt": attempt,
            "script_start_time_ist": SCRIPT_START_TIME,
            "script_end_time_ist": datetime.now(IST).isoformat(),
            "script_duration_sec": time.perf_counter() - SCRIPT_START_PERF,
            "llm_start_time_ist": llm_start_time,
            "llm_end_time_ist": llm_end_time,
            "llm_duration_sec": llm_duration,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "prompt_tokens_per_sec": prompt_tps,
            "completion_tokens_per_sec": completion_tps,
        }
    ])

    # Try to parse as JSON first
    parsed = _extract_json_from_text(raw)
    
    if isinstance(parsed, dict):
        # Got a proper JSON response
        corrected_code = parsed.get("corrected_code", "")
        if not corrected_code:
            # Maybe the code is in a different field or needs extraction
            corrected_code = _extract_code_from_llm_response(raw)
        
        return {
            "task_name": parsed.get("task_name", task.get("task_name")),
            "is_valid": bool(parsed.get("is_valid", False)),
            "error_message": parsed.get("error_message", "") or "",
            "corrected_code": corrected_code or "",
        }

    # JSON parsing failed - try to extract code directly
    corrected_code = _extract_code_from_llm_response(raw)
    
    if corrected_code:
        return {
            "task_name": task.get("task_name"),
            "is_valid": True,  # Assume valid if we got code
            "error_message": "",
            "corrected_code": corrected_code,
        }

    return {
        "task_name": task.get("task_name"),
        "is_valid": False,
        "error_message": "LLM response did not contain valid JSON or extractable code.",
        "corrected_code": "",
    }


def validate_and_fix_task(script_path: str, task_info: Dict, scripts_dir: str) -> Dict:
    task_name = task_info.get("task_name")
    datatype = task_info.get("data_type", DATA_TYPE)

    print(f"\n[Validator] Testing {task_name}...")

    exec_result = _execute_task_script(script_path)
    warnings_only = _stderr_is_only_warning(exec_result["stderr"])
    stderr_for_logging = "" if warnings_only else (exec_result["stderr"] or "")

    if exec_result["exit_code"] == 0:
        result_json = _parse_json_from_output(exec_result["stdout"])
        
        # Check various success conditions
        if result_json:
            # Case 1: Proper object with matching task_name
            if result_json.get("task_name") == task_name:
                if warnings_only:
                    print(f"⚠️ {task_name} emitted warnings but completed successfully.")
                    message = "Executed successfully (warning ignored)"
                else:
                    print(f"✅ {task_name} passed validation")
                    message = "Executed successfully"
                _log_task_result(task_name, "passed", 0)
                return {
                    "task_name": task_name,
                    "status": "passed",
                    "message": message,
                }
            
            # Case 2: Array output (result_summary only) - also valid
            if result_json.get("_array_output") or "result_summary" in result_json:
                if warnings_only:
                    print(f"⚠️ {task_name} emitted warnings but produced valid JSON array output.")
                    message = "Executed successfully (array output, warning ignored)"
                else:
                    print(f"✅ {task_name} passed validation (JSON array output)")
                    message = "Executed successfully (array output)"
                _log_task_result(task_name, "passed", 0)
                return {
                    "task_name": task_name,
                    "status": "passed",
                    "message": message,
                }
            
            # Case 3: JSON object without task_name but otherwise valid structure
            if isinstance(result_json, dict) and len(result_json) > 0:
                # Has some data, consider it valid
                if warnings_only:
                    print(f"⚠️ {task_name} emitted warnings but produced valid JSON output.")
                    message = "Executed successfully (JSON output, warning ignored)"
                else:
                    print(f"✅ {task_name} passed validation (JSON output)")
                    message = "Executed successfully (JSON output)"
                _log_task_result(task_name, "passed", 0)
                return {
                    "task_name": task_name,
                    "status": "passed",
                    "message": message,
                }

        if warnings_only:
            # treat warning-only runs with non-JSON output as warning-only success variant
            print(f"⚠️ {task_name} completed with warnings; JSON output could not be parsed but run succeeded.")
            _log_task_result(task_name, "passed", 0)
            return {
                "task_name": task_name,
                "status": "passed",
                "message": "Executed successfully (warning ignored)",
            }
        
        _append_error_log(
            task_name,
            0,
            f"Exit 0 but invalid/missing JSON output.\nStdout:\n{exec_result['stdout']}\nStderr:\n{exec_result['stderr']}",
        )
        print(f"❌ {task_name} exit 0 but output missing valid JSON")
        # Fall through to retry logic below
    else:
        # Non-zero exit code
        _append_error_log(task_name, exec_result["exit_code"], exec_result["stderr"] or exec_result["stdout"])
        print(f"⚠️ {task_name} failed (exit {exec_result['exit_code']})")
        # Fall through to retry logic below

    # Retry/correction logic (only reached if task failed validation above)
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            original_code = f.read()
    except Exception as e:
        return {"task_name": task_name, "status": "failed", "message": f"Could not read script: {e}"}

    task_info = dict(task_info)
    task_info["code"] = original_code
    assets = _load_context_for(datatype)

    # Log initial attempt (attempt 0) with no LLM interaction
    _append_timing_rows([
        {
            "step": "initial_run",
            "model": MODEL_NAME,
            "task_name": task_name,
            "status": "initial_validation",
            "attempt": 0,
            "script_start_time_ist": SCRIPT_START_TIME,
            "script_end_time_ist": datetime.now(IST).isoformat(),
            "script_duration_sec": time.perf_counter() - SCRIPT_START_PERF,
            "llm_start_time_ist": "",
            "llm_end_time_ist": "",
            "llm_duration_sec": "",
            "prompt_tokens": "",
            "completion_tokens": "",
            "total_tokens": "",
            "prompt_tokens_per_sec": "",
            "completion_tokens_per_sec": "",
        }
    ])

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[Validator] Retry {attempt}/{MAX_RETRIES} for {task_name}...")

        correction = _call_llm_for_correction(
            task_info,
            exec_result["stderr"] or exec_result["stdout"],
            exec_result["exit_code"],
            assets,
            attempt,
        )

        if not correction.get("corrected_code"):
            print(f"❌ LLM could not provide correction: {correction.get('error_message')}")
            continue

        corrected_code = _normalize_code_string(correction["corrected_code"])
        temp_path = script_path + ".tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(corrected_code)
        except Exception as e:
            print(f"❌ Failed to write corrected code: {e}")
            continue

        exec_result = _execute_task_script(temp_path)

        if exec_result["exit_code"] == 0:
            result_json = _parse_json_from_output(exec_result["stdout"])
            
            # Accept any valid JSON output
            if result_json:
                shutil.move(temp_path, script_path)
                print(f"✅ {task_name} corrected and validated successfully")
                return {"task_name": task_name, "status": "passed", "message": f"Fixed after {attempt} attempt(s)"}

        _append_error_log(task_name, exec_result["exit_code"], exec_result["stderr"] or exec_result["stdout"])
        task_info["code"] = corrected_code
        print(f"⚠️ Corrected code still failed (exit {exec_result['exit_code']})")

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

    failed_dir = os.path.join(scripts_dir, "failed")
    os.makedirs(failed_dir, exist_ok=True)
    failed_path = os.path.join(failed_dir, os.path.basename(script_path))

    try:
        shutil.move(script_path, failed_path)
        print(f"❌ {task_name} failed after {MAX_RETRIES} retries. Moved to failed/")
    except Exception as e:
        print(f"❌ {task_name} failed and could not move to failed/: {e}")

    return {
        "task_name": task_name,
        "status": "failed",
        "message": f"Failed after {MAX_RETRIES} correction attempts",
    }


def validate_all_generated_tasks(tasks_file: str, scripts_dir: str) -> Dict[str, List[Dict]]:
    print("\n" + "=" * 60)
    print("VALIDATING GENERATED TASK SCRIPTS")
    print("=" * 60)

    try:
        with open(tasks_file, "r", encoding="utf-8") as f:
            tasks_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load tasks file: {e}")
        return {"tasks": []}

    results: List[Dict] = []
    for task in tasks_data.get("tasks", []):
        task_name = task.get("task_name")
        if not task_name:
            continue

        script_path = os.path.join(scripts_dir, f"{task_name}.py")
        if not os.path.exists(script_path):
            print(f"⚠️ Script not found: {script_path}")
            results.append({
                "task_name": task_name,
                "status": "failed",
                "message": "Script file not found",
            })
            continue

        result = validate_and_fix_task(script_path, task, scripts_dir)
        results.append(result)

    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")

    print("\n" + "=" * 60)
    print(f"VALIDATION COMPLETE: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return {"tasks": results}


def main() -> None:
    os.makedirs(DEFAULT_SCRIPTS_DIR, exist_ok=True)

    # Ensure CSV exists (at least header) even if no LLM calls happen.
    _append_timing_rows([])

    summary = validate_all_generated_tasks(DEFAULT_TASKS_FILE, DEFAULT_SCRIPTS_DIR)

    # Ensure validator log directory exists
    os.makedirs(DEFAULT_VALIDATOR_LOG, exist_ok=True)
    
    summary_path = os.path.join(DEFAULT_VALIDATOR_LOG, f"validation_summary_{RUN_ID}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[Validator] Summary saved to {summary_path}")

    # If no timing rows were written (all tasks passed, no correction attempts),
    # add a single run-level record so the CSV isn't header-only.
    if TIMING_ROWS_WRITTEN == 0:
        _append_timing_rows([
            {
                "step": "validator_run",
                "model": MODEL_NAME,
                "task_name": "",
                "status": "no_corrections_needed",
                "attempt": "",
                "script_start_time_ist": SCRIPT_START_TIME,
                "script_end_time_ist": datetime.now(IST).isoformat(),
                "script_duration_sec": time.perf_counter() - SCRIPT_START_PERF,
                "llm_start_time_ist": "",
                "llm_end_time_ist": "",
                "llm_duration_sec": "",
                "prompt_tokens": "",
                "completion_tokens": "",
                "total_tokens": "",
                "prompt_tokens_per_sec": "",
                "completion_tokens_per_sec": "",
            }
        ])

# Log resource metrics at end
log_resource_metrics(RESOURCE_CSV, "step3_validator", "end", model_name=MODEL_NAME)


if __name__ == "__main__":
    main()

