"""
code_generator.py
-------------------
This module contains functions to generate Python task code
based on LLM responses for edge devices in an LLM-assisted edge computing system.

Task_list.json may contain multiple tasks, however, we will call multiple LLM calls to generate code for each task separately.
Each generated task code will be saved as a separate .py file in the `generated_tasks/{DATA_TYPE}` directory.

Notes:
- Validator removed: this script only generates code.
- Processes 1 task per LLM call (more reliable with OpenRouter/free routes).
- Skips tasks whose .py already exists.
- Updates new_tasks.json statuses (code_generated / failed to generate correct code).

Modified on: 25-05-2026
"""

import os
import json
import sys
import time
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from config import LLM_BASE_URL, LLM_API_KEY, DATA_TYPE, DEFAULT_MODEL

from prompts.get_code import SYSTEM_PROMPT
from typing import List
import re
from resource_monitor import log_resource_metrics
from shared_utils import (
    sanitize_model_name,
    extract_json_blob,
    extract_first_json_object,
    get_environment_vars,
    setup_timing_paths,
    append_timing_rows_to_csv,
    validate_data_type_exists,
    write_code_generator_csv,
    IST,
)

import threading
file_lock = threading.Lock()

# Placeholders for global variables populated in main()
client = None
DATA_PATH = None
META_PATH = None
CONTEXT_PATH = None
OUTPUT_DIR = None
TASK_LIST_PATH = None
NEW_TASKS_PATH = None
RESOURCE_SUMMARY_PATH = None
RUN_ID = None
RUN_COUNT = None
TIMESTAMP_PATH = None
STEP2_CSV = None
RESOURCE_CSV = None
SCRIPT_START_TIME = None
SCRIPT_START_PERF = None

def _truncate(text: str, max_chars: int) -> str:
    if not isinstance(text, str):
        return ""
    return text if len(text) <= max_chars else (text[:max_chars] + "\n... [truncated] ...")


def get_previous_errors_for_task(task_dt: str, task_name: str) -> str:
    """Read previous errors for the task from error.csv (or fallback error.txt)."""
    custom_tasks_dir = os.environ.get("LEI_TASKS_DIR")
    if custom_tasks_dir:
        error_csv_path = os.path.join(custom_tasks_dir, "error.csv")
        error_txt_path = os.path.join(custom_tasks_dir, "error.txt")
    else:
        error_csv_path = os.path.join("generated_tasks", task_dt, "error.csv")
        error_txt_path = os.path.join("generated_tasks", task_dt, "error.txt")
    
    if os.path.exists(error_csv_path):
        try:
            import csv
            errors = []
            with open(error_csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("task_name") == task_name:
                        errors.append(row)
            
            if errors:
                # Sort errors by count descending (most common errors first)
                errors.sort(key=lambda x: int(x.get("count", "1")), reverse=True)
                
                formatted = []
                for idx, err in enumerate(errors):
                    count = err.get("count", "1")
                    exit_code = err.get("exit_code", "unknown")
                    msg = err.get("error_message", "").strip()
                    formatted.append(
                        f"Error #{idx+1} (Occurred {count} time(s), Exit Code {exit_code}):\n{msg}"
                    )
                return "\n\n".join(formatted)
        except Exception as e:
            print(f"[WARNING] Could not parse error.csv: {e}")
            
    if os.path.exists(error_txt_path):
        try:
            with open(error_txt_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            raw_entries = content.split("-" * 60)
            entries = []
            for entry in raw_entries:
                entry_stripped = entry.strip()
                if not entry_stripped:
                    continue
                if f"TASK: {task_name} |" in entry_stripped or f"TASK: {task_name}\n" in entry_stripped:
                    entries.append(entry_stripped)
            if entries:
                return "\n\n".join(entries[-2:])
        except Exception as e:
            print(f"[WARNING] Could not parse error.txt: {e}")
            
    return ""


def call_llm_for_task_code(task_payload: dict) -> dict:
    """
    Send a task (payload={"tasks":[...]}) to the LLM and return parsed JSON.
    Returns dict with {"tasks":[{"task_name":..., "code":...}]} or None on failure.
    """
    # Determine per-batch DATA_TYPE
    if isinstance(task_payload, dict) and task_payload.get("tasks"):
        task_dt = task_payload["tasks"][0].get("data_type", DATA_TYPE)
    else:
        task_dt = task_payload.get("data_type", DATA_TYPE)

    # Retrieve task name (since batch size is 1, take the first task)
    task_name = ""
    if isinstance(task_payload, dict) and task_payload.get("tasks") and len(task_payload["tasks"]) > 0:
        task_name = task_payload["tasks"][0].get("task_name", "")

    previous_errors = ""
    if task_dt and task_name:
        previous_errors = get_previous_errors_for_task(task_dt, task_name)

    previous_errors_section = ""
    if previous_errors:
        previous_errors_section = f"""
### CRITICAL: FIX PREVIOUS EXECUTION ERROR(S)
The previous attempt to generate code for this task failed validation.
Analyze the error(s) below carefully (paying attention to exit code, traceback, missing imports/variables, or capitalization of keys e.g., 'Label' vs 'label'), and write corrected code that specifically resolves these issues and avoids repeating them:
{previous_errors}
"""

    output_dir_str = os.environ.get("LEI_OUTPUT_DIR", os.path.join("output", task_dt)).replace("\\", "/")
    system_prompt = SYSTEM_PROMPT.replace("{DATA_TYPE}", task_dt).replace("{OUTPUT_DIR}", output_dir_str)

    task_list_payload = json.dumps(task_payload, ensure_ascii=False, indent=2) \
        if isinstance(task_payload, dict) else str(task_payload)

    # Load assets for this data_type
    sample_data = ""
    metadata = {}
    context = ""
    base = os.path.join("data", task_dt)
    try:
        p_data = os.path.join(base, "sample_data.csv")
        p_meta = os.path.join(base, "metadata.json")
        p_ctx = os.path.join(base, "context.txt")
        if os.path.exists(p_data):
            with open(p_data, "r", encoding="utf-8") as f: sample_data = f.read()
        if os.path.exists(p_meta):
            with open(p_meta, "r", encoding="utf-8") as f: metadata = json.load(f)
        if os.path.exists(p_ctx):
            with open(p_ctx, "r", encoding="utf-8") as f: context = f.read()
    except Exception:
        pass

    # Trim
    sample_data = _truncate(sample_data, 5000)
    context = _truncate(context, 3000)
    meta_text = _truncate(json.dumps(metadata, ensure_ascii=False, indent=2), 3000)

    user_prompt = f"""
Return ONLY JSON. No prose.

IMPORTANT:
- The very first character of your response MUST be '{{'.
- Put any extra text AFTER the JSON object (but ideally output only JSON).

Schema:
{{"tasks":[{{"task_name":"<name1>","description":"<task description>","code":"<python code string>"}},{{"task_name":"<name2>","description":"<task description>","code":"<python code string>"}}]}}

Rules:
- Escape all internal quotes in the code string properly.
- Omit tasks with empty code or description.
- If only one task provided, return one element.

Sample Data:
{sample_data}

Metadata:
{meta_text}

Context:
{context}

{previous_errors_section}

Tasks (<=2):
{task_list_payload}
""".strip()

    # Single-model call with timing capture
    response = None
    used_model = DEFAULT_MODEL
    errors = []
    llm_start_time = ""
    llm_end_time = ""
    llm_start_perf = None
    llm_duration = 0.0
    try:
        llm_start_time = datetime.now(IST).isoformat()
        llm_start_perf = time.perf_counter()
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            timeout=300,  # 5-minute timeout to prevent indefinite hanging
        )
    except Exception as e:
        errors.append(f"{DEFAULT_MODEL}: {repr(e)}")

    if llm_start_perf is not None:
        llm_end_perf = time.perf_counter()
        llm_end_time = datetime.now(IST).isoformat()
        llm_duration = llm_end_perf - llm_start_perf

    if response is None:
        print("[Generator] Model call failed (%.2fs)." % llm_duration)
        for line in errors:
            print(" -", line)

        script_end_time = datetime.now(IST).isoformat()
        script_duration = time.perf_counter() - SCRIPT_START_PERF

        # Log failed call timing
        with file_lock:
            write_code_generator_csv(
                STEP2_CSV,
                SCRIPT_START_TIME,
                script_end_time,
                script_duration,
                "",
                "",
                0,
                0,
                0,
                0,
                DEFAULT_MODEL,
                RUN_COUNT,
                "",
            )
        return None

    # Capture finish reason for diagnostics
    finish_reason = getattr(response.choices[0], "finish_reason", None) if getattr(response, "choices", None) else None
    print(f"[Generator] finish_reason={finish_reason!r}")

    raw_output = _get_llm_text_from_chat_completion(response)
    print(f"[Generator] Raw length={len(raw_output)}")

    # If empty, dump the full response for inspection and return None (caller will mark failed)
    if not raw_output.strip():
        _debug_dump_response(response, Path("output") / "debug", prefix="task_codegen_empty_content")
        print(
            "[Generator] Empty LLM output. Check finish_reason/max_tokens and OpenRouter model availability. "
            "Saved debug response to output/debug/task_codegen_empty_content.json"
        )
        print(f"[DEBUG] Response finish_reason: {finish_reason}")
        print(f"[DEBUG] Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}")
        return None

    # Parse using extract-first-json (tolerate extra text)
    tasks_json = None
    try:
        tasks_json = extract_first_json_object(raw_output)
        print(f"[DEBUG] Successfully extracted JSON from LLM response")
    except Exception as e:
        print(f"[DEBUG] Failed to extract JSON: {e}")

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

    script_end_time = datetime.now(IST).isoformat()
    script_duration = time.perf_counter() - SCRIPT_START_PERF

    # Log successful call timing
    task_names = ",".join([t.get("task_name", "") for t in task_payload.get("tasks", [])]) if isinstance(task_payload, dict) else ""
    with file_lock:
        write_code_generator_csv(
            STEP2_CSV,
            SCRIPT_START_TIME,
            script_end_time,
            script_duration,
            llm_start_time,
            llm_end_time,
            llm_duration,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            used_model,
            RUN_COUNT,
            task_names,
        )

    print(f"[Generator] Model '{used_model}' success in {llm_duration:.2f}s. Raw length={len(raw_output)}")

    # Attempt strict JSON parse
    def parse_json(text: str):
        try:
            return json.loads(text)
        except Exception:
            return None

    tasks_data = parse_json(raw_output)
    if not tasks_data:
        blob = _extract_json_blob(raw_output)
        if blob:
            tasks_data = parse_json(blob)

    # Fallback: synthesize JSON if model returned code blocks instead of JSON
    if not tasks_json:
        code_blocks = re.findall(r"```(?:python)?\s*(.+?)```", raw_output, flags=re.DOTALL | re.IGNORECASE)
        names = [t.get("task_name") for t in task_payload.get("tasks", [])]
        synthesized = []
        for idx, code in enumerate(code_blocks[:len(names)]):
            synthesized.append({"task_name": names[idx], "description": "", "code": code.strip()})
        if synthesized:
            tasks_json = {"tasks": synthesized}

    if not tasks_json or "tasks" not in tasks_json or not isinstance(tasks_json["tasks"], list):
        print("[Generator] Could not parse LLM output into tasks JSON.")
        print("[Generator] Attempting fallback: extracting code from code blocks...")
        _debug_dump_response(response, Path("output") / "debug", prefix="task_codegen_unparseable")
        
        # Fallback: try to extract code blocks from raw output
        code_blocks = re.findall(r"```(?:python)?\s*(.+?)```", raw_output, flags=re.DOTALL | re.IGNORECASE)
        if code_blocks:
            print(f"[Generator] Found {len(code_blocks)} code block(s) in output")
            # Return the first code block found
            cleaned = [{
                "task_name": task_payload.get("tasks", [{}])[0].get("task_name", "Unknown"),
                "description": task_payload.get("tasks", [{}])[0].get("description", ""),
                "code": code_blocks[0].strip()
            }]
            return {"tasks": cleaned}
        
        try:
            out_dir = Path("output") / "debug"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "task_codegen_unparseable_raw.txt").write_text(raw_output, encoding="utf-8")
        except Exception:
            pass
        return None

    # Clean / filter tasks (only keep ones with a name)
    cleaned = []
    requested_names = {t.get("task_name") for t in task_payload.get("tasks", [])}
    requested_order = [t.get("task_name") for t in task_payload.get("tasks", [])]
    for t in tasks_json["tasks"]:
        tn = (t.get("task_name") or "").strip()
        code = t.get("code") or ""
        description = t.get("description") or ""
        if not tn or tn not in requested_names:
            continue
        cleaned.append({"task_name": tn, "description": description, "code": code})

    # If names don’t match but counts do, map by index as a fallback
    if not cleaned and isinstance(tasks_json.get("tasks"), list):
        src = tasks_json["tasks"]
        n = min(len(src), len(requested_order))
        if n > 0:
            cleaned = [
                {"task_name": requested_order[i], "description": (src[i].get("description") or "").strip(), "code": (src[i].get("code") or "").strip()}
                for i in range(n)
                if isinstance(src[i], dict)
            ]

    if not cleaned:
        print("[Generator] Parsed output but found no matching tasks.")
        print(f"[DEBUG] Requested task names: {requested_order}")
        print(f"[DEBUG] Returned task names: {[t.get('task_name', '') for t in tasks_json.get('tasks', [])]}")
        return None

    return {"tasks": cleaned}


def update_task_status_in_file(all_tasks_payload, task_name, status_message):
    with file_lock:
        for task_entry in all_tasks_payload.get("tasks", []):
            if task_entry.get("task_name") == task_name:
                task_entry["status"] = status_message
                break
        # Update tasks_list.json persistent archive
        with open(TASK_LIST_PATH, "w", encoding="utf-8") as out_file:
            json.dump(all_tasks_payload, out_file, ensure_ascii=False, indent=2)

        # Update only the matching task in new_tasks.json (if it exists) to keep it decoupled from tasks_list.json history
        if os.path.exists(NEW_TASKS_PATH) and os.path.getsize(NEW_TASKS_PATH) > 0:
            try:
                with open(NEW_TASKS_PATH, "r", encoding="utf-8") as f:
                    new_tasks_payload = json.load(f)
            except Exception:
                new_tasks_payload = {"tasks": []}
            
            updated_new = False
            for task_entry in new_tasks_payload.get("tasks", []):
                if task_entry.get("task_name") == task_name:
                    task_entry["status"] = status_message
                    updated_new = True
                    break
            
            if updated_new:
                with open(NEW_TASKS_PATH, "w", encoding="utf-8") as out_file:
                    json.dump(new_tasks_payload, out_file, ensure_ascii=False, indent=2)


def normalize_code_string(code: str) -> str:
    """Convert JSON-escaped/code-fenced text into plain Python source."""
    if not isinstance(code, str):
        return ""
    s = code.strip()
    
    # Strip markdown code blocks robustly
    if s.startswith("```"):
        s = re.sub(r"^```(?:python)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
    elif "```python" in s:
        match = re.search(r"```python\s*(.+?)\s*```", s, flags=re.DOTALL | re.IGNORECASE)
        if match:
            s = match.group(1)
            
    # Remove literal backslash sequences that should be normal escapes
    s = s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    s = s.replace("\\'", "'").replace('\\"', '"')
    
    # Auto-repair common boolean/null typos
    s = re.sub(r'\bfalse\b', 'False', s)
    s = re.sub(r'\btrue\b', 'True', s)
    s = re.sub(r'\bnull\b', 'None', s)
    
    return s

def _extract_json_blob(text: str) -> str:
    """Extract a JSON object string from text that may contain extra content."""
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
        # Return the JSON string (from start to end of the decoded object)
        return s[start:start + end]
    except Exception:
        return ""



def _get_llm_text_from_chat_completion(response) -> str:
    """
    OpenRouter/OpenAI-compatible responses sometimes put the payload in tool_calls.
    This returns the best-effort textual payload to parse.
    """
    if not getattr(response, "choices", None):
        return ""

    choice0 = response.choices[0]
    msg = getattr(choice0, "message", None)
    if msg is None:
        return ""

    # Normal path
    content = getattr(msg, "content", None)
    if isinstance(content, str) and content.strip():
        return content

    # Some reasoning models/providers return text in a separate field
    reasoning = getattr(msg, "reasoning", None)
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning

    # Tool-call path (JSON is often in function.arguments)
    tool_calls = getattr(msg, "tool_calls", None) or []
    if tool_calls:
        tc0 = tool_calls[0]
        fn = getattr(tc0, "function", None)
        args = getattr(fn, "arguments", None) if fn else None
        if isinstance(args, str) and args.strip():
            return args

    # Last resort: inspect the raw dict (captures provider-specific fields)
    try:
        if hasattr(response, "model_dump"):
            dump = response.model_dump()
            ch0 = (dump.get("choices") or [{}])[0]
            msgd = ch0.get("message") or {}
            return (msgd.get("content") or msgd.get("reasoning") or "").strip()
    except Exception:
        pass

    # Nothing usable
    return ""


def _debug_dump_response(response, out_dir: Path, prefix: str = "llm_response") -> None:
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / f"{prefix}.json"
        # OpenAI SDK objects support model_dump_json() (pydantic) in recent versions
        if hasattr(response, "model_dump_json"):
            p.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        else:
            # fallback
            p.write_text(json.dumps(response, default=str, indent=2), encoding="utf-8")
    except Exception:
        # don't crash the pipeline due to debug logging
        pass
def main() -> int:
    global client, DATA_PATH, META_PATH, CONTEXT_PATH, OUTPUT_DIR, TASK_LIST_PATH, NEW_TASKS_PATH, RESOURCE_SUMMARY_PATH, RUN_ID, RUN_COUNT, TIMESTAMP_PATH, STEP2_CSV, RESOURCE_CSV, SCRIPT_START_TIME, SCRIPT_START_PERF

    # Ensure Unicode-safe stdout/stderr on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    from openai import OpenAI
    # Initialize the LLM client
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=120)

    # Validate that the DATA_TYPE folder exists with required files
    validate_data_type_exists(DATA_TYPE)

    # Paths
    BASE_PATH = f"data/{DATA_TYPE}/"
    DATA_PATH = os.path.join(BASE_PATH, "sample_data.csv")
    META_PATH = os.path.join(BASE_PATH, "metadata.json")
    CONTEXT_PATH = os.path.join(BASE_PATH, "context.txt")
    OUTPUT_DIR = os.environ.get("LEI_TASKS_DIR", os.path.join("generated_tasks", DATA_TYPE))
    TASK_LIST_PATH = os.path.join(OUTPUT_DIR, "tasks_list.json")  # Read from persistent task list
    NEW_TASKS_PATH = os.path.join(OUTPUT_DIR, "new_tasks.json")    # For status updates
    RESOURCE_SUMMARY_PATH = "resource_stat/resource_usage_summary.json"

    # Per-run CSV path with model name and run ID
    env_vars = get_environment_vars()
    RUN_ID = env_vars["RUN_ID"]
    RUN_COUNT = env_vars["RUN_COUNT"]
    timing_paths = setup_timing_paths(DATA_TYPE, "step2", DEFAULT_MODEL)
    TIMESTAMP_PATH = timing_paths["TIMESTAMP_PATH"]
    STEP2_CSV = timing_paths["STEP_CSV"]
    RESOURCE_CSV = timing_paths["RESOURCE_CSV"]

    # Step-level timing (for entire script)
    SCRIPT_START_TIME = datetime.now(IST).isoformat()
    SCRIPT_START_PERF = time.perf_counter()

    # Log resource metrics at start
    log_resource_metrics(RESOURCE_CSV, "step2_code_generator", "start", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)

    # ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ensure task list exists before trying to read it
    if not os.path.exists(TASK_LIST_PATH):
        print(f"[ERROR] Task list not found: {TASK_LIST_PATH}")
        print("Ensure task_generator.py has run and created tasks_list.json before running code_generator.py")
        return 1

    with open(TASK_LIST_PATH, "r", encoding="utf-8") as f:
        tasks_payload = json.load(f)

    # Load tasks to generate code for from new_tasks.json to only generate code for the current run's tasks
    if os.path.exists(NEW_TASKS_PATH) and os.path.getsize(NEW_TASKS_PATH) > 0:
        try:
            with open(NEW_TASKS_PATH, "r", encoding="utf-8") as f:
                new_tasks_data = json.load(f)
            pending_tasks = new_tasks_data.get("tasks", [])
            print(f"[INFO] Loaded {len(pending_tasks)} tasks from new_tasks.json for code generation.")
        except Exception as e:
            print(f"[WARNING] Failed to load new_tasks.json: {e}. Falling back to tasks_list.json")
            pending_tasks = tasks_payload.get("tasks", [])
    else:
        pending_tasks = tasks_payload.get("tasks", [])
    
    if not pending_tasks:
        print(f"[WARNING] No tasks found to generate code.")
        return 0

    print(f"[INFO] Found {len(pending_tasks)} pending tasks for code generation.")
    print(f"[INFO] LLM Model: {DEFAULT_MODEL}\n")

    # Build list of tasks that need generation, skip existing files
    tasks_to_generate = []
    for task_info in pending_tasks:
        name = task_info.get("task_name")
        if not name:
            print(f" [SKIP] Skipping task with missing name: {task_info}")
            task_info["status"] = "failed to generate correct code"
            continue

        existing_task_path = os.path.join(OUTPUT_DIR, f"{name}.py")
        if os.path.exists(existing_task_path):
            print(f" [SKIP] {name} - existing script detected.")
            update_task_status_in_file(tasks_payload, name, "code_generated")
            continue

        tasks_to_generate.append(task_info)
        print(f" [QUEUE] {name}")
    
    print(f"\n[INFO] {len(tasks_to_generate)} tasks need code generation\n")

    # Group tasks into batches of up to 1 tasks
    batch_size = 1
    task_batches = [tasks_to_generate[i:i + batch_size] for i in range(0, len(tasks_to_generate), batch_size)]

    def process_batch(batch) -> None:
        payload = {
            "tasks": [
                {
                    "task_name": t.get("task_name"),
                    "description": t.get("description", ""),
                    "data_type": t.get("data_type", DATA_TYPE),
                }
                for t in batch
            ]
        }

        batch_names = [t.get("task_name") for t in batch]
        print(f"\n[PROCESSING] Batch tasks: {', '.join(batch_names)}")
        generated = call_llm_for_task_code(payload)

        if not generated or not generated.get("tasks"):
            for t in batch:
                tn = t.get("task_name")
                update_task_status_in_file(tasks_payload, tn, "failed to generate correct code")
                print(f" [FAIL] LLM did not return valid code for {tn}. Marked as failed.")
            return

        generated_tasks = generated.get("tasks", [])
        generated_map = {gt.get("task_name"): gt for gt in generated_tasks if gt.get("task_name")}

        for t in batch:
            tn = t.get("task_name")
            ret = generated_map.get(tn)
            
            # Fallback by index if name matching failed
            if not ret:
                try:
                    idx = batch.index(t)
                    if idx < len(generated_tasks):
                        ret = generated_tasks[idx]
                except Exception:
                    pass

            if ret and ret.get("code"):
                code_text = normalize_code_string(ret.get("code", "").strip())
                code_lines = len(code_text.split('\n'))
                print(f" [OK] LLM returned code for {tn} ({code_lines} lines)")
                
                filepath = os.path.join(OUTPUT_DIR, f"{tn}.py")
                try:
                    # Prepend task description as docstring for clarity and validation
                    description = t.get('description', '')
                    if description:
                        code_with_docstring = f'"""\nTask: {tn}\nDescription: {description}\n"""\n\n{code_text}'
                    else:
                        code_with_docstring = code_text
                    
                    with open(filepath, "w", encoding="utf-8") as wf:
                        wf.write(code_with_docstring)
                    print(f" [SAVED] {tn}.py")
                    update_task_status_in_file(tasks_payload, tn, "code_generated")
                except Exception as e:
                    print(f" [ERROR] Failed to save {tn}.py: {e}")
                    update_task_status_in_file(tasks_payload, tn, "failed to generate correct code")
            else:
                print(f" [FAIL] LLM response missing 'code' field for {tn}")
                update_task_status_in_file(tasks_payload, tn, "failed to generate correct code")

    # Use ThreadPoolExecutor for parallel batch code generation
    max_workers = min(len(task_batches), 4)  # run up to 4 batches in parallel
    if max_workers > 0:
        print(f"[INFO] Launching parallel code generation for {len(task_batches)} batches with {max_workers} threads...")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(process_batch, task_batches)

    print(f"\nAll requested batches processed. Check generated_tasks/{DATA_TYPE} for outputs.")

    # Log resource metrics at end
    log_resource_metrics(RESOURCE_CSV, "step2_code_generator", "end", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
