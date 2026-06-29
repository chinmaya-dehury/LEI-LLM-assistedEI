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

last code updated on 21-05-2025
(name changed from llm_orchestrator_adaptive_resource.py to task_generator.py)
"""

import os
import sys
import json
import time
import csv
from datetime import datetime, timezone, timedelta
from config import DATA_TYPE, LLM_BASE_URL, LLM_API_KEY, DEFAULT_MODEL
from prompts.get_tasks import SYSTEM_PROMPT
from resource_monitor import log_resource_metrics
from shared_utils import (
    sanitize_model_name,
    extract_first_json_object,
    get_environment_vars,
    setup_timing_paths,
    append_timing_rows_to_csv,
    load_context_for_data_type,
    validate_data_type_exists,
    load_resource_summary,
    write_task_generator_csv,
    IST,
)


def main() -> int:
    from openai import OpenAI
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=120)

    # Paths
    BASE_PATH = os.path.join("data", DATA_TYPE)
    DATA_PATH = os.path.join(BASE_PATH, "sample_data.csv")
    META_PATH = os.path.join(BASE_PATH, "metadata.json")
    CONTEXT_PATH = os.path.join(BASE_PATH, "context.txt")
    RESOURCE_SUMMARY_PATH = os.path.join("resource_stat", "resource_usage_summary.json")
    OUTPUT_DIR = os.environ.get("LEI_TASKS_DIR", os.path.join("generated_tasks", DATA_TYPE))
    TASK_LIST_PATH = os.path.join(OUTPUT_DIR, "tasks_list.json")

    # Setup timing paths and environment variables
    env_vars = get_environment_vars()
    RUN_ID = env_vars["RUN_ID"]
    RUN_COUNT = env_vars["RUN_COUNT"]

    # Validate that the DATA_TYPE folder exists with required files
    validate_data_type_exists(DATA_TYPE)

    timing_paths = setup_timing_paths(DATA_TYPE, "step1", DEFAULT_MODEL)
    TIMESTAMP_PATH = timing_paths["TIMESTAMP_PATH"]
    STEP1_CSV_PATH = timing_paths["STEP_CSV"]
    RESOURCE_CSV = timing_paths["RESOURCE_CSV"]

    # Script-wide timing start
    script_start_time = datetime.now(IST).isoformat()
    script_start_perf = time.perf_counter()

    # Log resource metrics at start
    log_resource_metrics(RESOURCE_CSV, "step1_task_generator", "start", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)

    # Load context for this data type
    context_data = load_context_for_data_type(DATA_TYPE)
    sample_data = context_data["sample_data"]
    metadata = context_data["metadata"]
    context = context_data["context"]

    # Ensure task list exists and is not empty; if not, create/reset with empty tasks list
    if not os.path.exists(TASK_LIST_PATH) or os.path.getsize(TASK_LIST_PATH) == 0:
        os.makedirs(os.path.dirname(TASK_LIST_PATH), exist_ok=True)
        with open(TASK_LIST_PATH, "w", encoding="utf-8") as f:
            json.dump({"tasks": []}, f, indent=2)

    with open(TASK_LIST_PATH, "r", encoding="utf-8") as f:
        existing_tasks = f.read().strip()
        if not existing_tasks:
            existing_tasks = '{"tasks": []}'

    with open(RESOURCE_SUMMARY_PATH, "r") as f:
        resource_summary = f.read()

    system_prompt = SYSTEM_PROMPT
    # User prompt with data, metadata, and context
    user_prompt = f"""
Return ONLY JSON. No prose.

IMPORTANT:
- The very first character of your response MUST be '{{'.
- Put any extra text AFTER the JSON object (but ideally output only JSON).

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
""".strip()

    #print how many tasks are in existing_tasks
    try:
        existing_tasks_json = json.loads(existing_tasks) if existing_tasks else {"tasks": []}
    except Exception:
        existing_tasks_json = {"tasks": []}
    print(f"{len(existing_tasks_json.get('tasks', []))} no. of existing tasks are sent to LLM.")

    # Call the LLM with timing
    llm_start_time = datetime.now(IST).isoformat()
    llm_start_perf = time.perf_counter()
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0,
        timeout=300
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

    model_name = getattr(response, "model", DEFAULT_MODEL)

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
        write_task_generator_csv(
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
            DEFAULT_MODEL,
            RUN_COUNT,
        )
        return 1

    # Parse JSON safely (handles extra NL text / code fences around JSON)
    try:
        tasks_data = extract_first_json_object(raw_output)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Could not extract JSON from LLM response: {e}")
        print("Checking fallback: extracting tasks from unstructured numbered list/markdown...")
        import re
        fallback_tasks = []
        
        def clean_name(name_str: str) -> str:
            # Clean up leading noise like "a Python program that calculates" -> "calculates"
            name_str = re.sub(r'^(?:a\s+)?(?:python\s+)?(?:program|script|code|workflow)\s+(?:that|to|for|designed\s+to|intended\s+to)?\s*', '', name_str, flags=re.IGNORECASE)
            # Clean up verbs at the beginning
            name_str = re.sub(r'^(?:calculates|performs|analyzes|does|is|runs|updates|shows|generates)\s+', '', name_str, flags=re.IGNORECASE)
            if name_str:
                name_str = name_str[0].upper() + name_str[1:]
            return name_str

        # 1. Match numbered patterns like "1) Task Name:" or "1. Task Name"
        matches = re.findall(r'(?:^|\n)\s*(\d+)[\.\)\:]\s*([^\n\:\(]+)(?:[\:\(]|\n)', raw_output)
        if matches:
            for idx, name_candidate in matches:
                name = name_candidate.strip()
                if len(name) > 3 and not name.lower().startswith("here are"):
                    fallback_tasks.append({
                        "task_name": clean_name(name),
                        "description": f"Write a Python program to perform: {name}"
                    })
        
        # 2. If we couldn't find numbered items, check for markdown headers
        if not fallback_tasks:
            headers = re.findall(r'(?:^|\n)\s*###?\s*([^\n]+)', raw_output)
            for h in headers:
                name = h.strip()
                if len(name) > 3:
                    fallback_tasks.append({
                        "task_name": clean_name(name),
                        "description": f"Write a Python program to perform: {name}"
                    })

        # 3. If still nothing, check for bullet points
        if not fallback_tasks:
            bullets = re.findall(r'(?:^|\n)\s*[\-\*]\s*([^\n\:\(]+)(?:[\:\(]|\n)', raw_output)
            for b in bullets:
                name = b.strip()
                if len(name) > 3 and not name.lower().startswith("here are"):
                    fallback_tasks.append({
                        "task_name": clean_name(name),
                        "description": f"Write a Python program to perform: {name}"
                    })

        # 4. If still nothing, check if there is an introductory sentence for code generation
        if not fallback_tasks:
            intro_match = re.search(r'(?:here is|this is|a python script|a python program|a script|a program)\s+(?:that|to|designed to|for)?\s*([^\n\.\:\,]+)', raw_output, re.IGNORECASE)
            if intro_match:
                name = intro_match.group(1).strip()
                cleaned = clean_name(name)
                if len(cleaned) > 5:
                    fallback_tasks.append({
                        "task_name": cleaned,
                        "description": f"Write a Python program to perform: {cleaned}"
                    })

        # 5. Fallback of last resort: if there is code but we couldn't parse any task name, look at comments in the code or use a default name
        if not fallback_tasks and "```python" in raw_output:
            comment_match = re.search(r'#\s*([^\n]+)', raw_output)
            if comment_match:
                name = comment_match.group(1).strip()
                if len(name) > 3:
                    fallback_tasks.append({
                        "task_name": clean_name(name),
                        "description": f"Write a Python program to perform: {name}"
                    })
            if not fallback_tasks:
                fallback_tasks.append({
                    "task_name": "Precision Agricultural Data Analysis",
                    "description": "Write a Python program to analyze the agricultural dataset."
                })
                    
        if fallback_tasks:
            print(f"[Fallback] Successfully extracted {len(fallback_tasks)} tasks from unstructured response!")
            tasks_data = {"tasks": fallback_tasks}
        else:
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
            write_task_generator_csv(
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
                DEFAULT_MODEL,
                RUN_COUNT,
            )
            return 1

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
        write_task_generator_csv(
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
            DEFAULT_MODEL,
            RUN_COUNT,
        )
        return 1

    # if no new tasks are generated, print the reason and exit successfully (non-failing)
    tasks_list = tasks_data.get("tasks", []) if isinstance(tasks_data.get("tasks", []), list) else []
    if len(tasks_list) == 0:
        reason = tasks_data.get("empty_reason", "No reason provided.")
        print("No new tasks were generated. Reason: " + reason)

        # Save empty new_tasks.json for subsequent generators
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "new_tasks.json"), "w", encoding="utf-8") as f:
            json.dump(tasks_data, f, indent=2)

        script_end_time = datetime.now(IST).isoformat()
        script_end_perf = time.perf_counter()
        script_duration = script_end_perf - script_start_perf
        llm_duration = llm_end_perf - llm_start_perf
        write_task_generator_csv(
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
            DEFAULT_MODEL,
            RUN_COUNT,
        )
        return 0

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
    if os.path.exists(TASK_LIST_PATH) and os.path.getsize(TASK_LIST_PATH) > 0:
        try:
            with open(TASK_LIST_PATH, "r", encoding="utf-8") as f:
                existing_tasks_data = json.load(f)
        except Exception:
            existing_tasks_data = {"tasks": []}
        if not isinstance(existing_tasks_data, dict) or "tasks" not in existing_tasks_data:
            existing_tasks_data = {"tasks": []}
        existing_tasks_data["tasks"].extend(tasks_data["tasks"])
        tasks_data = existing_tasks_data

    # Write updated tasks_list.json
    with open(TASK_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(tasks_data, f, indent=2)
    print("The list of all tasks with their description are successfully saved in "+TASK_LIST_PATH)

    # Keep new_tasks.json with the newly generated tasks so that code_generator.py can consume it.
    print(f"[OK] Preserved newly generated tasks in new_tasks.json for downstream code generation.")

    # Final script end timing and CSV logging
    script_end_time = datetime.now(IST).isoformat()
    script_end_perf = time.perf_counter()
    script_duration = script_end_perf - script_start_perf
    llm_duration = llm_end_perf - llm_start_perf

    # Log resource metrics at end
    log_resource_metrics(RESOURCE_CSV, "step1_task_generator", "end", model_name=DEFAULT_MODEL, run_count=RUN_COUNT)

    write_task_generator_csv(
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
        DEFAULT_MODEL,
        RUN_COUNT,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
