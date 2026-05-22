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
"""

import os
import json
import sys
import time
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from openai import OpenAI
from config import LLM_BASE_URL, LLM_API_KEY, DATA_TYPE, DEFAULT_MODEL
from string import Template
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
    IST,
)

# Ensure Unicode-safe stdout/stderr on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Initialize the LLM client
client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

# Paths
BASE_PATH = f"data/{DATA_TYPE}/"
DATA_PATH = os.path.join(BASE_PATH, "sample_data.csv")
META_PATH = os.path.join(BASE_PATH, "metadata.json")
CONTEXT_PATH = os.path.join(BASE_PATH, "context.txt")
OUTPUT_DIR = os.path.join("generated_tasks", DATA_TYPE)
TASK_LIST_PATH = os.path.join(OUTPUT_DIR, "new_tasks.json")
RESOURCE_SUMMARY_PATH = "resource_stat/resource_usage_summary.json"

# Per-run CSV path with model name and run ID
env_vars = get_environment_vars()
RUN_ID = env_vars["RUN_ID"]
RUN_COUNT = env_vars["RUN_COUNT"]
timing_paths = setup_timing_paths(DATA_TYPE, "step2", DEFAULT_MODEL)
TIMESTAMP_PATH = timing_paths["TIMESTAMP_PATH"]
STEP2_CSV = timing_paths["STEP_CSV"]
RESOURCE_CSV = timing_paths["RESOURCE_CSV"]


def _append_timing_rows(rows: list[dict]) -> None:
    os.makedirs(TIMESTAMP_PATH, exist_ok=True)
    file_exists = os.path.exists(STEP2_CSV) and os.path.getsize(STEP2_CSV) > 0
    # Add run_count and resource summary fields from resource_stat/resource_usage_summary.json
    fieldnames = [
        "step",
        "model",
        "run_count",
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
        "tasks",
        "resource_generated_at",
        "resource_last_checked",
        "avg_cpu_1m",
        "avg_mem_1m",
        "avg_cpu_5m",
        "avg_mem_5m",
    ]

    # Try to read resource summary values
    resource_vals = {}
    try:
        with open(RESOURCE_SUMMARY_PATH, "r", encoding="utf-8") as rf:
            rs = json.load(rf)
            resource_vals["resource_generated_at"] = rs.get("generated_at", "")
            resource_vals["resource_last_checked"] = rs.get("last_checked", "")
            sw = rs.get("summary_windows", {}) or {}
            w1 = sw.get("1m", {}) or {}
            w5 = sw.get("5m", {}) or {}
            resource_vals["avg_cpu_1m"] = w1.get("avg_cpu", "")
            resource_vals["avg_mem_1m"] = w1.get("avg_mem", "")
            resource_vals["avg_cpu_5m"] = w5.get("avg_cpu", "")
            resource_vals["avg_mem_5m"] = w5.get("avg_mem", "")
    except Exception:
        # leave resource_vals empty if file missing or malformed
        resource_vals = {k: "" for k in [
            "resource_generated_at", "resource_last_checked", "avg_cpu_1m",
            "avg_mem_1m", "avg_cpu_5m", "avg_mem_5m"]}

    with open(STEP2_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            # Add run_count and resource_vals to each row
            row["run_count"] = row.get("run_count", RUN_COUNT)
            row.update(resource_vals)
            writer.writerow(row)

# Step-level timing (for entire script)
SCRIPT_START_TIME = datetime.now(IST).isoformat()
SCRIPT_START_PERF = time.perf_counter()

# Log resource metrics at start
log_resource_metrics(RESOURCE_CSV, "step2_code_generator", "start", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)

def _truncate(text: str, max_chars: int) -> str:
    if not isinstance(text, str):
        return ""
    return text if len(text) <= max_chars else (text[:max_chars] + "\n... [truncated] ...")


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

    system_prompt = Template(SYSTEM_PROMPT).substitute(DATA_TYPE=task_dt)

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
{{"tasks":[{{"task_name":"<name1>","code":"<python code string>"}},{{"task_name":"<name2>","code":"<python code string>"}}]}}

Rules:
- Escape all internal quotes in the code string properly.
- Omit tasks with empty code.
- If only one task provided, return one element.

Sample Data:
{sample_data}

Metadata:
{meta_text}

Context:
{context}

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
        _append_timing_rows([
            {
                "step": "llm_call_failed",
                "script_start_time_ist": SCRIPT_START_TIME,
                "script_end_time_ist": script_end_time,
                "script_duration_sec": script_duration,
                # Do not populate llm_* timestamps when no response is received
                "llm_start_time_ist": "",
                "llm_end_time_ist": "",
                "llm_duration_sec": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "prompt_tokens_per_sec": 0,
                "completion_tokens_per_sec": 0,
                "model": DEFAULT_MODEL,
                "tasks": ",".join([t.get("task_name", "") for t in task_payload.get("tasks", [])]) if isinstance(task_payload, dict) else "",
            }
        ])
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
        return None

    # Parse using extract-first-json (tolerate extra text)
    tasks_json = None
    try:
        tasks_json = extract_first_json_object(raw_output)
    except Exception:
        raw_output = str(response)

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
    _append_timing_rows([
        {
            "step": "llm_call",
            "script_start_time_ist": SCRIPT_START_TIME,
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
            "model": used_model,
            "tasks": ",".join([t.get("task_name", "") for t in task_payload.get("tasks", [])]) if isinstance(task_payload, dict) else "",
        }
    ])

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
            synthesized.append({"task_name": names[idx], "code": code.strip()})
        if synthesized:
            tasks_json = {"tasks": synthesized}

    if not tasks_json or "tasks" not in tasks_json or not isinstance(tasks_json["tasks"], list):
        print("[Generator] Could not parse LLM output into tasks JSON.")
        _debug_dump_response(response, Path("output") / "debug", prefix="task_codegen_unparseable")
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
        if not tn or tn not in requested_names:
            continue
        cleaned.append({"task_name": tn, "code": code})

    # If names don’t match but counts do, map by index as a fallback
    if not cleaned and isinstance(tasks_json.get("tasks"), list):
        src = tasks_json["tasks"]
        n = min(len(src), len(requested_order))
        if n > 0:
            cleaned = [
                {"task_name": requested_order[i], "code": (src[i].get("code") or "").strip()}
                for i in range(n)
                if isinstance(src[i], dict)
            ]

    if not cleaned:
        print("[Generator] Parsed output but found no matching tasks.")
        return None

    return {"tasks": cleaned}


def update_task_status_in_file(all_tasks_payload, task_name, status_message):
    for task_entry in all_tasks_payload.get("tasks", []):
        if task_entry.get("task_name") == task_name:
            task_entry["status"] = status_message
            break
    with open(TASK_LIST_PATH, "w", encoding="utf-8") as out_file:
        json.dump(all_tasks_payload, out_file, ensure_ascii=False, indent=2)


def normalize_code_string(code: str) -> str:
    """Convert JSON-escaped/code-fenced text into plain Python source."""
    if not isinstance(code, str):
        return ""
    s = code.strip()
    # strip fenced blocks if present
    if s.startswith("```"):
        s = re.sub(r"^```(?:python)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
    # unescape common sequences if they appear literally
    if "\\r\\n" in s or "\\n" in s or "\\t" in s:
        s = s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
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

def main() -> None:
    # ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ensure task list exists before trying to read it
    if not os.path.exists(TASK_LIST_PATH):
        print(f"❌ Task list not found: {TASK_LIST_PATH}")
        print("Create the new_tasks.json (or ensure pipeline writes it) and re-run.")
        sys.exit(1)

    with open(TASK_LIST_PATH, "r", encoding="utf-8") as f:
        tasks_payload = json.load(f)

    pending_tasks = tasks_payload.get("tasks", [])

    # Build list of tasks that need generation, skip existing files
    tasks_to_generate = []
    for task_info in pending_tasks:
        name = task_info.get("task_name")
        if not name:
            print(f" Skipping task with missing name: {task_info}")
            task_info["status"] = "failed to generate correct code"
            continue

        existing_task_path = os.path.join(OUTPUT_DIR, f"{name}.py")
        if os.path.exists(existing_task_path):
            print(f" Skipping {name} - existing script detected at {existing_task_path}.")
            update_task_status_in_file(tasks_payload, name, "code_generated")
            continue

        tasks_to_generate.append(task_info)

    # Process one task per LLM call (prevents truncation on long code responses)
    for t in tasks_to_generate:
        payload = {
            "tasks": [
                {
                    "task_name": t.get("task_name"),
                    "description": t.get("description", ""),
                    "data_type": t.get("data_type", DATA_TYPE),
                }
            ]
        }

        tn = t.get("task_name")
        print(f"\nRequesting code for task: {tn}")
        generated = call_llm_for_task_code(payload)

        if not generated or not generated.get("tasks"):
            update_task_status_in_file(tasks_payload, tn, "failed to generate correct code")
            print(f" ❌ LLM did not return code for {tn}. Marked as failed.")
            with open(TASK_LIST_PATH, "w", encoding="utf-8") as out_file:
                json.dump(tasks_payload, out_file, ensure_ascii=False, indent=2)
            continue

        ret = (generated.get("tasks") or [{}])[0]
        if ret and ret.get("code"):
            filepath = os.path.join(OUTPUT_DIR, f"{tn}.py")
            try:
                code_text = normalize_code_string(ret.get("code", ""))
                with open(filepath, "w", encoding="utf-8") as wf:
                    wf.write(code_text)
                print(f" ✅ Saved: {tn}.py")
                print(f"    Description: {t.get('description','')}\n")
                update_task_status_in_file(tasks_payload, tn, "code_generated")
            except Exception as e:
                print(f" ❌ Failed to save {tn}.py: {e}")
                update_task_status_in_file(tasks_payload, tn, "failed to generate correct code")
        else:
            print(f" ❌ LLM did not return code for {tn}.")
            update_task_status_in_file(tasks_payload, tn, "failed to generate correct code")

        with open(TASK_LIST_PATH, "w", encoding="utf-8") as out_file:
            json.dump(tasks_payload, out_file, ensure_ascii=False, indent=2)

    print(f"\nAll requested batches processed. Check generated_tasks/{DATA_TYPE} for outputs.")

    # Log resource metrics at end
    log_resource_metrics(RESOURCE_CSV, "step2_code_generator", "end", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)


if __name__ == "__main__":
    main()
