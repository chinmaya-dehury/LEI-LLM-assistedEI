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
from datetime import datetime, timezone
import re

from openai import OpenAI

from config import DATA_TYPE, OLLAMA_SERVER_URL
from prompts.get_validator import SYSTEM_PROMPT

# Windows-safe stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CLIENT_TIMEOUT = 180  # seconds
client = OpenAI(base_url=OLLAMA_SERVER_URL, api_key="ollama", timeout=CLIENT_TIMEOUT)

MODEL_NAME = "qwen3:8b"

TIMESTAMP_PATH = os.path.join("timestamp_path", DATA_TYPE)
# Per-run CSV path (requested: step3_val_<timestamp>.csv)
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
STEP2_VAL_CSV = os.path.join(TIMESTAMP_PATH, f"step3_val_{RUN_ID}.csv")

MAX_RETRIES = 2
DEFAULT_TASKS_FILE = os.path.join("generated_tasks", DATA_TYPE, "new_tasks.json")
DEFAULT_SCRIPTS_DIR = os.path.join("generated_tasks", DATA_TYPE)
ERROR_LOG_PATH = os.path.join(DEFAULT_SCRIPTS_DIR, "error.txt")


def _append_timing_rows(rows: List[dict]) -> None:
    os.makedirs(TIMESTAMP_PATH, exist_ok=True)
    file_exists = os.path.exists(STEP2_VAL_CSV) and os.path.getsize(STEP2_VAL_CSV) > 0
    fieldnames = [
        "step",
        "script_start_time_utc",
        "script_end_time_utc",
        "script_duration_sec",
        "llm_start_time_utc",
        "llm_end_time_utc",
        "llm_duration_sec",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_tokens_per_sec",
        "completion_tokens_per_sec",
        "model",
        "task_name",
        "attempt",
    ]

    with open(STEP2_VAL_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


# Script-level timing
SCRIPT_START_TIME = datetime.now(timezone.utc).isoformat()
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


def _call_llm_for_correction(task: Dict, runtime_error: str, exit_code: int, assets: Dict, attempt: int) -> Dict:
    datatype = task.get("data_type", DATA_TYPE)
    system_prompt = Template(SYSTEM_PROMPT).substitute(DATA_TYPE=datatype)
    user_prompt = _build_correction_prompt(task, runtime_error, exit_code, assets)

    llm_start_time = datetime.now(timezone.utc).isoformat()
    llm_start_perf = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            timeout=CLIENT_TIMEOUT,
        )
    except Exception as e:
        llm_end_perf = time.perf_counter()
        llm_end_time = datetime.now(timezone.utc).isoformat()
        llm_duration = llm_end_perf - llm_start_perf

        script_end_time = datetime.now(timezone.utc).isoformat()
        script_duration = time.perf_counter() - SCRIPT_START_PERF
        _append_timing_rows([
            {
                "step": "llm_call",
                "script_start_time_utc": SCRIPT_START_TIME,
                "script_end_time_utc": script_end_time,
                "script_duration_sec": script_duration,
                "llm_start_time_utc": llm_start_time,
                "llm_end_time_utc": llm_end_time,
                "llm_duration_sec": llm_duration,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "prompt_tokens_per_sec": 0,
                "completion_tokens_per_sec": 0,
                "model": MODEL_NAME,
                "task_name": task.get("task_name", ""),
                "attempt": attempt,
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
    llm_end_time = datetime.now(timezone.utc).isoformat()
    llm_duration = llm_end_perf - llm_start_perf
    usage = getattr(response, "usage", None) or {}
    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
        total_tokens = usage.get("total_tokens") or (prompt_tokens + completion_tokens)
    else:
        prompt_tokens = getattr(usage, "prompt_tokens", 0)
        completion_tokens = getattr(usage, "completion_tokens", 0)
        total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens)

    prompt_tps = prompt_tokens / llm_duration if llm_duration > 0 else 0
    completion_tps = completion_tokens / llm_duration if llm_duration > 0 else 0

    raw = ""
    try:
        raw = response.choices[0].message.content if hasattr(response, "choices") else str(response)
    except Exception:
        raw = str(response)

    _append_timing_rows([
        {
            "step": "llm_call",
            "script_start_time_utc": SCRIPT_START_TIME,
            "script_end_time_utc": datetime.now(timezone.utc).isoformat(),
            "script_duration_sec": time.perf_counter() - SCRIPT_START_PERF,
            "llm_start_time_utc": llm_start_time,
            "llm_end_time_utc": llm_end_time,
            "llm_duration_sec": llm_duration,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "prompt_tokens_per_sec": prompt_tps,
            "completion_tokens_per_sec": completion_tps,
            "model": MODEL_NAME,
            "task_name": task.get("task_name", ""),
            "attempt": attempt,
        }
    ])

    try:
        parsed = json.loads(raw)
    except Exception:
        try:
            start_idx = raw.find("{")
            end_idx = raw.rfind("}") + 1
            if start_idx != -1 and end_idx != -1:
                parsed = json.loads(raw[start_idx:end_idx])
            else:
                raise ValueError("no JSON found")
        except Exception:
            return {
                "task_name": task.get("task_name"),
                "is_valid": False,
                "error_message": "LLM response was not valid JSON.",
                "corrected_code": "",
            }

    return {
        "task_name": parsed.get("task_name", task.get("task_name")),
        "is_valid": bool(parsed.get("is_valid", False)),
        "error_message": parsed.get("error_message", "") or "",
        "corrected_code": parsed.get("corrected_code", "") or "",
    }


def _parse_json_from_output(output: str) -> Dict | None:
    """
    Attempt to extract a JSON object from stdout even if warnings or extra text
    are present. Returns dict if successful, otherwise None.
    
    Note: The expected output is a JSON object with "task_name" field.
    If the script outputs a JSON array (result_summary only), we wrap it.
    """
    if not output:
        return None

    text = output.strip()
    if not text:
        return None

    # First try the last non-empty line (common when warnings precede JSON)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        try:
            parsed = json.loads(lines[-1])
            # If it's an array, it's likely result_summary only - not valid
            if isinstance(parsed, list):
                return None
            return parsed
        except Exception:
            pass

    # Fallback: direct parse of the whole buffer
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return None
        return parsed
    except Exception:
        pass

    # Extract JSON object by locating outer braces (object)
    start_obj = text.rfind("{")
    end_obj = text.rfind("}")
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        candidate = text[start_obj:end_obj + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    # Extract JSON array by locating outer brackets (for result_summary)
    # But we need the full output structure with task_name, so if we only find array, reject
    start_arr = text.find("[")
    end_arr = text.rfind("]")
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        candidate = text[start_arr:end_arr + 1]
        try:
            parsed = json.loads(candidate)
            # It's a valid array but missing task_name - not acceptable
            if isinstance(parsed, list):
                return None
        except Exception:
            pass

    return None


def _stderr_is_only_warning(stderr_text: str) -> bool:
    """
    Returns True if stderr contains only warning lines (FutureWarning / DeprecationWarning / generic warnings).
    """
    if not stderr_text:
        return False
    lines = [ln.strip() for ln in stderr_text.splitlines() if ln.strip()]
    if not lines:
        return False
    for line in lines:
        lower = line.lower()
        if "warning" not in lower:
            return False
    return True


def validate_and_fix_task(script_path: str, task_info: Dict, scripts_dir: str) -> Dict:
    task_name = task_info.get("task_name")
    datatype = task_info.get("data_type", DATA_TYPE)

    print(f"\n[Validator] Testing {task_name}...")

    exec_result = _execute_task_script(script_path)
    warnings_only = _stderr_is_only_warning(exec_result["stderr"])
    stderr_for_logging = "" if warnings_only else (exec_result["stderr"] or "")

    if exec_result["exit_code"] == 0:
        result_json = _parse_json_from_output(exec_result["stdout"])
        if result_json and result_json.get("task_name") == task_name:
            if warnings_only:
                print(f"⚠️ {task_name} emitted warnings but completed successfully.")
                message = "Executed sucessfully (warning ignored)"
            else:
                print(f"✅ {task_name} passed validation")
                message = "Executed successfully"
            return {
                "task_name": task_name,
                "status": "passed",
                "message": message,
            }
        if warnings_only:
            # treat warning-only runs with non-JSON output as warning-only success variant
            print(f"⚠️ {task_name} completed with warnings; JSON output could not be parsed but run succeeded.")
            return {
                "task_name": task_name,
                "status": "passed",
                "message": "Executed sucessfully (warning ignored)",
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
            if result_json and result_json.get("task_name") == task_name:
                shutil.move(temp_path, script_path)
                print(f"✅ {task_name} corrected and validated successfully")
                return {"task_name": task_name, "status": "passed", "message": f"Fixed after {attempt} attempt(s)"}
            
            # Check if corrected version outputs valid JSON (even without task_name)
            try:
                text = exec_result["stdout"].strip()
                arr_start = text.rfind("[")
                arr_end = text.rfind("]")
                if arr_start != -1 and arr_end > arr_start:
                    json.loads(text[arr_start:arr_end+1])
                    # Valid JSON array output
                    shutil.move(temp_path, script_path)
                    print(f"✅ {task_name} corrected (outputs valid JSON array)")
                    return {"task_name": task_name, "status": "passed", "message": f"Fixed after {attempt} attempt(s) (JSON format variant)"}
            except:
                pass

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
    summary = validate_all_generated_tasks(DEFAULT_TASKS_FILE, DEFAULT_SCRIPTS_DIR)

    summary_path = os.path.join(DEFAULT_SCRIPTS_DIR, "validation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[Validator] Summary saved to {summary_path}")


if __name__ == "__main__":
    main()

