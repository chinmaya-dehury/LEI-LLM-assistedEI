"""
task_generator.py
-------------------
This script reads sample environmental data, metadata, and context,
then asks an LLM (e.g., GPT-5) to generate multiple small Python
programs that can run on an edge device to extract insights.

Why adaptive?
------------
This version check if there is a list of tasks already generated. 
If so, it asks the LLM to only generate new list of task, if any. 

Why resource?
------------
This is resource-aware version. It provides the LLM with current
resource usage summary of the edge device so that the LLM can decide
whether to generate new tasks or not based on the resource constraints.

last code updated on 18-12-2025
(name changed from llm_orchestrator_adaptive_resource.py to task_generator.py)
"""

import os
import sys
import json
import time
import csv
from datetime import datetime, timezone, timedelta
from openai import OpenAI
from string import Template
from config import DATA_TYPE, OLLAMA_SERVER_URL, MODEL_NAME
from prompts.get_tasks_list_adaptive_resource import SYSTEM_PROMPT
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


def _extract_first_json_object(text: str) -> dict:
    """Extract first JSON object from LLM output that may contain extra NL text."""
    if not isinstance(text, str):
        raise ValueError("LLM output is not a string")

    s = text.strip()

    # Strip ``` fences if present
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if "```" in s:
            s = s.rsplit("```", 1)[0].strip()

    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object start '{' found in LLM output")

    decoder = json.JSONDecoder()
    obj, _end = decoder.raw_decode(s[start:])
    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON value is not an object")
    return obj


def write_timing_csv(
    csv_path: str,
    script_start_time: str,
    script_end_time: str,
    script_duration: float,
    llm_start_time: str,
    llm_end_time: str,
    llm_duration: float,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model_name: str,
) -> None:
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    prompt_tokens_per_sec = prompt_tokens / llm_duration if llm_duration > 0 else 0
    completion_tokens_per_sec = completion_tokens / llm_duration if llm_duration > 0 else 0

    fieldnames = [
        "step",
        "model",
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

    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0

    with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        # Dedicated LLM call timing row
        writer.writerow(
            {
                "step": "llm_call",
                "model": model_name,
                "script_start_time_ist": script_start_time,
                "script_end_time_ist": script_end_time,
                "script_duration_sec": script_duration,
                "llm_start_time_ist": llm_start_time,
                "llm_end_time_ist": llm_end_time,
                "llm_duration_sec": llm_duration,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "prompt_tokens_per_sec": prompt_tokens_per_sec,
                "completion_tokens_per_sec": completion_tokens_per_sec,
            }
        )


# Initialize the LLM client to use the OLLAMA server.
# OLLAMA_SERVER_URL is expected to include the /v1 endpoint, e.g. "http://localhost:11434/v1".
client = OpenAI(base_url=OLLAMA_SERVER_URL, api_key="ollama")

# Paths
BASE_PATH = "data/"+DATA_TYPE+"/"
DATA_PATH = BASE_PATH+"sample_data.csv"
META_PATH = BASE_PATH+"metadata.json"
CONTEXT_PATH = BASE_PATH+"context.txt"
RESOURCE_SUMMARY_PATH = "resource_stat/resource_usage_summary.json"
OUTPUT_DIR = "generated_tasks/"+DATA_TYPE
TASK_LIST_PATH = OUTPUT_DIR+"/tasks_list.json"
TIMESTAMP_PATH = os.path.join("timestamp_path", DATA_TYPE)

# Per-run CSV path with model name and run ID (requested: step1_<model>_<timestamp>.csv)
IST = timezone(timedelta(hours=5, minutes=30))
# Use RUN_ID from environment (passed from pipeline) or generate new one
RUN_ID = os.environ.get("RUN_ID") or datetime.now(IST).strftime("%Y%m%d_%H%M%S")
SANITIZED_MODEL = _sanitize_model_name(MODEL_NAME)
STEP1_CSV_PATH = os.path.join(TIMESTAMP_PATH, f"step1_{SANITIZED_MODEL}_{RUN_ID}.csv")

# Script-wide timing start
script_start_time = datetime.now(IST).isoformat()
script_start_perf = time.perf_counter()

# Log resource metrics at start
RESOURCE_CSV = os.path.join(TIMESTAMP_PATH, f"step1_resource_{SANITIZED_MODEL}_{RUN_ID}.csv")
log_resource_metrics(RESOURCE_CSV, "step1_task_generator", "start", model_name=MODEL_NAME)

# Read all inputs
with open(DATA_PATH, "r") as f:
    sample_data = f.read()

with open(META_PATH, "r") as f:
    metadata = json.load(f)

with open(CONTEXT_PATH, "r") as f:
    context = f.read()

# Ensure task list exists; if not create with empty tasks list
if not os.path.exists(TASK_LIST_PATH):
    os.makedirs(os.path.dirname(TASK_LIST_PATH), exist_ok=True)
    with open(TASK_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump({"tasks": []}, f, indent=2)

with open(TASK_LIST_PATH, "r", encoding="utf-8") as f:
    existing_tasks = f.read()

with open(RESOURCE_SUMMARY_PATH, "r") as f:
    resource_summary = f.read()

system_prompt = Template(SYSTEM_PROMPT).substitute(DATA_TYPE=DATA_TYPE)
# User prompt with data, metadata, and context
user_prompt = f"""
Sample Data:
{sample_data}

Metadata:
{json.dumps(metadata, indent=2)}

Context:
{context}

Existing tasks and their descriptions:
{existing_tasks}

Summary of current resource usage and its availability on the edge device:
{resource_summary} 
"""

#print how many tasks are in existing_tasks
existing_tasks_json = json.loads(existing_tasks)
print(f"{len(existing_tasks_json['tasks'])} no. of existing tasks are sent to LLM.")

# Call the LLM with timing
llm_start_time = datetime.now(IST).isoformat()
llm_start_perf = time.perf_counter()
response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
)
llm_end_perf = time.perf_counter()
llm_end_time = datetime.now(IST).isoformat()

# Extract token usage metrics from response
usage = getattr(response, "usage", None) or {}
if isinstance(usage, dict):
    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    total_tokens = usage.get("total_tokens") or (prompt_tokens + completion_tokens)
else:
    prompt_tokens = getattr(usage, "prompt_tokens", 0)
    completion_tokens = getattr(usage, "completion_tokens", 0)
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens)

model_name = getattr(response, "model", MODEL_NAME)

# Extract response content (may be None/empty if the model failed)
raw_output = response.choices[0].message.content or ""

# If nothing came back, treat as error early
if not str(raw_output).strip():
    print("The LLM returned empty content. Saving raw output for review.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_bytes = str(raw_output).encode("utf-8", "replace")
    with open(os.path.join(OUTPUT_DIR, "raw_output.txt"), "wb") as f:
        f.write(raw_bytes)

    script_end_time = datetime.now(IST).isoformat()
    script_end_perf = time.perf_counter()
    script_duration = script_end_perf - script_start_perf
    llm_duration = llm_end_perf - llm_start_perf
    write_timing_csv(
        STEP1_CSV_PATH,
        script_start_time,
        script_end_time,
        script_duration,
        llm_start_time,
        llm_end_time,
        llm_duration,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        model_name,
    )
    sys.exit(1)

# Parse JSON safely (handles extra NL text / code fences around JSON)
try:
    tasks_data = _extract_first_json_object(raw_output)
except (json.JSONDecodeError, ValueError) as e:
    print(f"Could not extract JSON from LLM response: {e}")
    print("Saving raw output for review.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_bytes = str(raw_output).encode("utf-8", "replace")
    with open(os.path.join(OUTPUT_DIR, "raw_output.txt"), "wb") as f:
        f.write(raw_bytes)

    # Script end timing and CSV logging before exit
    script_end_time = datetime.now(IST).isoformat()
    script_end_perf = time.perf_counter()
    script_duration = script_end_perf - script_start_perf
    llm_duration = llm_end_perf - llm_start_perf
    write_timing_csv(
        STEP1_CSV_PATH,
        script_start_time,
        script_end_time,
        script_duration,
        llm_start_time,
        llm_end_time,
        llm_duration,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        model_name,
    )
    sys.exit(1)

# _extract_first_json_object already guarantees dict, but double-check
if not isinstance(tasks_data, dict):
    print("The LLM returned JSON that is not an object. Saving raw output for review.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "raw_output.txt"), "wb") as f:
        f.write(str(raw_output).encode("utf-8", "replace"))

    script_end_time = datetime.now(IST).isoformat()
    script_end_perf = time.perf_counter()
    script_duration = script_end_perf - script_start_perf
    llm_duration = llm_end_perf - llm_start_perf
    write_timing_csv(
        STEP1_CSV_PATH,
        script_start_time,
        script_end_time,
        script_duration,
        llm_start_time,
        llm_end_time,
        llm_duration,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        model_name,
    )
    sys.exit(1)

# if no new tasks are generated, print the reason and fail this model run
tasks_list = tasks_data.get("tasks", []) if isinstance(tasks_data.get("tasks", []), list) else []
if len(tasks_list) == 0:
    reason = tasks_data.get("empty_reason", "No reason provided.")
    print("No new tasks were generated. Reason: " + reason)

    script_end_time = datetime.now(IST).isoformat()
    script_end_perf = time.perf_counter()
    script_duration = script_end_perf - script_start_perf
    llm_duration = llm_end_perf - llm_start_perf
    write_timing_csv(
        STEP1_CSV_PATH,
        script_start_time,
        script_end_time,
        script_duration,
        llm_start_time,
        llm_end_time,
        llm_duration,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        model_name,
    )
    sys.exit(1)

# print how many new tasks are generated
print(f"{len(tasks_data['tasks'])} new tasks are generated by LLM.")
# ensure each new task explicitly carries its DATA_TYPE for downstream modules
for t in tasks_data.get("tasks", []):
    t.setdefault("data_type", DATA_TYPE)

# Save new tasks for code generator (parity with adaptive task_generator)
os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(os.path.join(OUTPUT_DIR, "new_tasks.json"), "w", encoding="utf-8") as f:
    json.dump(tasks_data, f, indent=2)

# Merge with existing tasks_list.json
if os.path.exists(TASK_LIST_PATH):
    with open(TASK_LIST_PATH, "r", encoding="utf-8") as f:
        existing_tasks_data = json.load(f)
    existing_tasks_data["tasks"].extend(tasks_data["tasks"])
    tasks_data = existing_tasks_data

# Write updated tasks_list.json
with open(TASK_LIST_PATH, "w", encoding="utf-8") as f:
    json.dump(tasks_data, f, indent=2)
print("The list of all tasks with their description are successfully saved in "+TASK_LIST_PATH)

# Final script end timing and CSV logging
script_end_time = datetime.now(IST).isoformat()
script_end_perf = time.perf_counter()
script_duration = script_end_perf - script_start_perf
llm_duration = llm_end_perf - llm_start_perf

# Log resource metrics at end
log_resource_metrics(RESOURCE_CSV, "step1_task_generator", "end", model_name=MODEL_NAME)

write_timing_csv(
    STEP1_CSV_PATH,
    script_start_time,
    script_end_time,
    script_duration,
    llm_start_time,
    llm_end_time,
    llm_duration,
    prompt_tokens,
    completion_tokens,
    total_tokens,
    model_name,
)

