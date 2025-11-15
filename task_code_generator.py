"""
task_code_generator.py
-------------------
This module contains functions to generate Python task code
based on LLM responses for edge devices in an LLM-assisted edge computing system.

Task_list.json may contain multiple tasks, however, we will call multiple LLM calls to generate code for each task separately.
Each generated task code will be saved as a separate .py file in the `generated_tasks/{DATA_TYPE}` directory.

Notes:
- Validator removed: this script only generates code.
- Processes up to 2 tasks per LLM call (batched).
- Skips tasks whose .py already exists.
- Updates new_tasks.json statuses (code_generated / failed to generate correct code).
"""

import os
import json
import sys
import time
from openai import OpenAI
from config import OPENAI_API_KEY, DATA_TYPE
from string import Template
from prompts.get_single_task_code import SYSTEM_PROMPT
from typing import List
import re

# Ensure Unicode-safe stdout/stderr on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Initialize the LLM client
client = OpenAI(api_key=OPENAI_API_KEY)

# Paths
BASE_PATH = f"data/{DATA_TYPE}/"
DATA_PATH = os.path.join(BASE_PATH, "sample_data.csv")
META_PATH = os.path.join(BASE_PATH, "metadata.json")
CONTEXT_PATH = os.path.join(BASE_PATH, "context.txt")
OUTPUT_DIR = os.path.join("generated_tasks", DATA_TYPE)
TASK_LIST_PATH = os.path.join(OUTPUT_DIR, "new_tasks.json")

FALLBACK_MODELS: List[str] = [
    "gpt-5",        # try first (if your account supports Responses/Chat for this model)
    "gpt-4o-mini",  # common lightweight fallback
    "gpt-4o",       # heavier fallback
]


def _truncate(text: str, max_chars: int) -> str:
    if not isinstance(text, str):
        return ""
    return text if len(text) <= max_chars else (text[:max_chars] + "\n... [truncated] ...")


def _extract_json_blob(raw: str) -> str | None:
    # Try to extract a single JSON object from free-form text
    if not raw:
        return None
    try:
        # simple heuristic: take between first '{' and last '}'
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw[start:end+1]
    except Exception:
        pass
    return None


def call_llm_for_task_code(task_payload: dict) -> dict:
    """
    Send up to two tasks (payload={"tasks":[...]} ) to the LLM and return parsed JSON.
    Returns dict with {"tasks":[{"task_name":..., "code":..., "description":...}, ...]} or None on failure.
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
Return ONLY JSON. No prose. Schema:
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

    # Model fallback
    response = None
    used_model = None
    errors = []
    start_all = time.perf_counter()
    for mdl in FALLBACK_MODELS:
        try:
            start = time.perf_counter()
            # Only pass temperature if not gpt-5 (since error shows gpt-5 disallows 0.0)
            kwargs = dict(
                model=mdl,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            if "gpt-5" not in mdl:  # safe heuristic
                kwargs["temperature"] = 0.0
            response = client.chat.completions.create(**kwargs)
            used_model = mdl
            break
        except Exception as e:
            errors.append(f"{mdl}: {repr(e)}")
            continue

    elapsed_all = time.perf_counter() - start_all
    if response is None:
        print("[Generator] All model attempts failed (%.2fs)." % elapsed_all)
        for line in errors:
            print(" -", line)
        return None

    raw_output = ""
    try:
        raw_output = response.choices[0].message.content
    except Exception:
        raw_output = str(response)

    print(f"[Generator] Model '{used_model}' success in {elapsed_all:.2f}s. Raw length={len(raw_output)}")

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
    if not tasks_data:
        code_blocks = re.findall(r"```(?:python)?\s*(.+?)```", raw_output, flags=re.DOTALL | re.IGNORECASE)
        names = [t.get("task_name") for t in task_payload.get("tasks", [])]
        synthesized = []
        for idx, code in enumerate(code_blocks[:len(names)]):
            synthesized.append({"task_name": names[idx], "code": code.strip()})
        if synthesized:
            tasks_data = {"tasks": synthesized}

    if not tasks_data or "tasks" not in tasks_data or not isinstance(tasks_data["tasks"], list):
        print("[Generator] Could not parse LLM output into tasks JSON.")
        return None

    # Clean / filter tasks (only keep ones with a name)
    cleaned = []
    requested_names = {t.get("task_name") for t in task_payload.get("tasks", [])}
    requested_order = [t.get("task_name") for t in task_payload.get("tasks", [])]
    for t in tasks_data["tasks"]:
        tn = (t.get("task_name") or "").strip()
        code = t.get("code") or ""
        if not tn or tn not in requested_names:
            continue
        cleaned.append({"task_name": tn, "code": code})

    # If names don’t match but counts do, map by index as a fallback
    if not cleaned and isinstance(tasks_data.get("tasks"), list):
        src = tasks_data["tasks"]
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

# Read inputs
# ensure output dir exists
if not os.path.exists(OUTPUT_DIR):
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
        # can't update by name (it's missing) — mark the entry directly
        task_info["status"] = "failed to generate correct code"
        continue

    existing_task_path = os.path.join(OUTPUT_DIR, f"{name}.py")
    if os.path.exists(existing_task_path):
        print(f" Skipping {name} - existing script detected at {existing_task_path}.")
        update_task_status_in_file(tasks_payload, name, "code_generated")
        continue

    tasks_to_generate.append(task_info)

# Process in batches of up to 2 tasks
for i in range(0, len(tasks_to_generate), 2):
    batch = tasks_to_generate[i:i+2]
    payload = {"tasks": []}
    for t in batch:
        # include data_type if present, else global
        payload["tasks"].append({
            "task_name": t.get("task_name"),
            "description": t.get("description", ""),
            "data_type": t.get("data_type", DATA_TYPE)
        })

    print(f"\nRequesting code for batch: {[t['task_name'] for t in payload['tasks']]}")
    generated = call_llm_for_task_code(payload)

    if not generated or not generated.get("tasks"):
        # mark all batch tasks as failed
        for t in batch:
            update_task_status_in_file(tasks_payload, t.get("task_name"), "failed to generate correct code")
            print(f" ❌ LLM did not return code for {t.get('task_name')}. Marked as failed.")
        # persist updated tasks file
        with open(TASK_LIST_PATH, "w", encoding="utf-8") as out_file:
            json.dump(tasks_payload, out_file, ensure_ascii=False, indent=2)
        continue

    # Save returned code files and update statuses
    # normalize returned task names for robust matching
    returned_map = {
        (rt.get("task_name") or "").strip().lower(): rt
        for rt in generated.get("tasks", [])
    }

    for t in batch:
        tn = t.get("task_name")
        ret = returned_map.get((tn or "").strip().lower())
        # fallback: if LLM returned exactly one task for the batch, assume it corresponds
        if ret is None and len(generated.get("tasks", [])) == 1:
            ret = generated["tasks"][0]

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
            print(f" ❌ LLM did not return code for {tn} in batch response.")
            update_task_status_in_file(tasks_payload, tn, "failed to generate correct code")

    # persist updated tasks file after each batch
    with open(TASK_LIST_PATH, "w", encoding="utf-8") as out_file:
        json.dump(tasks_payload, out_file, ensure_ascii=False, indent=2)

print(f"\nAll requested batches processed. Check generated_tasks/{DATA_TYPE} for outputs.")