"""
task_code_generator.py
-------------------
This module contains functions to generate Python task code
based on LLM responses for edge devices in an LLM-assisted edge computing system.

Task_list.json may contain multiple tasks, however, we will call multiple LLM calls to generate code for each task separately.
Each generated task code will be saved as a separate .py file in the `generated_tasks/{DATA_TYPE}` directory.

"""

import os
import json
from openai import OpenAI
from string import Template
from prompts.get_single_task_code import SYSTEM_PROMPT

# Initialize the LLM client
client = OpenAI()

# Paths
DATA_TYPE = "temp_humidity"
BASE_PATH = "data/"+DATA_TYPE+"/"
DATA_PATH = BASE_PATH+"sample_data.csv"
META_PATH = BASE_PATH+"metadata.json"
CONTEXT_PATH = BASE_PATH+"context.txt"
OUTPUT_DIR = "generated_tasks/"+DATA_TYPE
TASK_LIST_PATH = OUTPUT_DIR+"/tasks_list1.json"
NO_OF_TASKS = 2  # Number of tasks to generate code for


def call_llm_for_task_code(task_list):
    system_prompt = Template(SYSTEM_PROMPT).substitute(DATA_TYPE=DATA_TYPE)

    user_prompt = f"""
    Sample Data:
    {sample_data}

    Metadata:
    {json.dumps(metadata, indent=2)}

    Context:
    {context}

    Tasks List:
    {task_list}
    """

    # # Call the LLM
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]    
    )
    # Extract the response content
    raw_output = response.choices[0].message.content

    # Parse JSON safely
    try:
        tasks_data = json.loads(raw_output) 
        
    except json.JSONDecodeError:
        print("⚠️ The LLM response was not valid JSON. Saving raw output for review.")    
        exit()
    return tasks_data # return python code for two tasks
    
    

def save_task_code(tasks_data):
    # # Save each generated task as a separate .py file
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for task in tasks_data["tasks"]:   
        filename = f"{task['task_name']}.py"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(task["code"])
        print(f"✅ Saved: {filename}")
        print(f"   → Description: {task['description']}\n")

    print("🎯 All tasks generated successfully and saved in {} folder.",OUTPUT_DIR)




# Read all inputs
with open(DATA_PATH, "r") as f:
    sample_data = f.read()

with open(META_PATH, "r") as f:
    metadata = json.load(f)

with open(CONTEXT_PATH, "r") as f:
    context = f.read()

# with open(TASK_LIST_PATH, "r") as f:
#     task_list = f.read()
json_task_list = []
with open(TASK_LIST_PATH, "r") as f:
    tasks = json.load(f)
    for task in tasks["tasks"]:
        json_task_list.append({
            "task_name": task["task_name"],
            "description": task["description"]
        })
# loop every 2 entries
for i in range(0, len(json_task_list), NO_OF_TASKS):    
    group = {"tasks": json_task_list[i:i+2]}
    print(json.dumps(group, ensure_ascii=False, indent=2))
    task_data = call_llm_for_task_code(json.dumps(group, ensure_ascii=False))
    if task_data:
        save_task_code(task_data)
    
















