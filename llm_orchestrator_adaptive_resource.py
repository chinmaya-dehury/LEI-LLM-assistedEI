"""
llm_orchestrator.py
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

last code updated on 14-12-2025
"""

import os
import json
import time
import csv
from datetime import datetime, timezone
from openai import OpenAI
from string import Template
from config import DATA_TYPE, OLLAMA_SERVER_URL
from prompts.get_tasks_list_adaptive_resource import SYSTEM_PROMPT

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
                "script_start_time_utc": script_start_time,
                "script_end_time_utc": script_end_time,
                "script_duration_sec": script_duration,
                "llm_start_time_utc": llm_start_time,
                "llm_end_time_utc": llm_end_time,
                "llm_duration_sec": llm_duration,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "prompt_tokens_per_sec": prompt_tokens_per_sec,
                "completion_tokens_per_sec": completion_tokens_per_sec,
                "model": model_name,
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

# Per-run CSV path (requested: step1_<timestamp>.csv)
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
STEP1_CSV_PATH = os.path.join(TIMESTAMP_PATH, f"step1_{RUN_ID}.csv")

# Script-wide timing start
script_start_time = datetime.now(timezone.utc).isoformat()
script_start_perf = time.perf_counter()

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
llm_start_time = datetime.now(timezone.utc).isoformat()
llm_start_perf = time.perf_counter()
response = client.chat.completions.create(
    model="qwen3:8b",  # you can change to other model available in your OLLAMA server
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
)
llm_end_perf = time.perf_counter()
llm_end_time = datetime.now(timezone.utc).isoformat()

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

model_name = getattr(response, "model", "qwen3:8b")

# Extract response content (may be None/empty if the model failed)
raw_output = response.choices[0].message.content or ""

# If nothing came back, treat as error early
if not str(raw_output).strip():
    print("The LLM returned empty content. Saving raw output for review.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_bytes = str(raw_output).encode("utf-8", "replace")
    with open(os.path.join(OUTPUT_DIR, "raw_output.txt"), "wb") as f:
        f.write(raw_bytes)

    script_end_time = datetime.now(timezone.utc).isoformat()
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
    exit()

# Parse JSON safely
try:
    tasks_data = json.loads(raw_output)
except json.JSONDecodeError:
    print("The LLM response was not valid JSON. Saving raw output for review.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_bytes = str(raw_output).encode("utf-8", "replace")
    with open(os.path.join(OUTPUT_DIR, "raw_output.txt"), "wb") as f:
        f.write(raw_bytes)

    # Script end timing and CSV logging before exit
    script_end_time = datetime.now(timezone.utc).isoformat()
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
    exit()

# if no new tasks are generated, print the reason
if len(tasks_data.get("tasks", [])) == 0:
    reason = tasks_data.get("empty_reason", "No reason provided.")
    print("No new tasks were generated. Reason: " + reason)

    # Script end timing and CSV logging before exit
    script_end_time = datetime.now(timezone.utc).isoformat()
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
    exit()

# print how many new tasks are generated
print(f"{len(tasks_data['tasks'])} new tasks are generated by LLM.")
# ensure each new task explicitly carries its DATA_TYPE for downstream modules
for t in tasks_data.get("tasks", []):
    t.setdefault("data_type", DATA_TYPE)

# Save new tasks for code generator (parity with adaptive orchestrator)
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
script_end_time = datetime.now(timezone.utc).isoformat()
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

