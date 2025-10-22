"""
llm_orchestrator.py
-------------------
This script reads sample environmental data, metadata, and context,
then asks an LLM (e.g., GPT-5) to generate multiple small Python
programs that can run on an edge device to extract insights.
"""

import os
import json
from openai import OpenAI
from string import Template
from prompts.get_tasks_list import SYSTEM_PROMPT

# Initialize the LLM client
client = OpenAI()

# Paths
DATA_TYPE = "temp_humidity"
BASE_PATH = "data/"+DATA_TYPE+"/"
DATA_PATH = BASE_PATH+"sample_data.csv"
META_PATH = BASE_PATH+"metadata.json"
CONTEXT_PATH = BASE_PATH+"context.txt"
OUTPUT_DIR = "generated_tasks/"+DATA_TYPE

# Read all inputs
with open(DATA_PATH, "r") as f:
    sample_data = f.read()

with open(META_PATH, "r") as f:
    metadata = json.load(f)

with open(CONTEXT_PATH, "r") as f:
    context = f.read()

# System prompt to guide the LLM
# system_prompt = Template("""
# You are an expert AI orchestration agent.
# You receive (1) sample data, (2) metadata, and (3) contextual information
# from an edge device. Your goal is to generate multiple *small* Python
# programs that can each perform one insight or task related to the data.

# Your response should be in JSON format like this:

# {
#   "tasks": [
#     {
#       "task_name": "comfort_index_estimation",
#       "description": "Estimate human comfort index using temperature and humidity.",
#       "code": "<python code here>"
#     },
#     {
#       "task_name": "anomaly_detection",
#       "description": "Detect anomalies in temperature readings using rolling z-score.",
#       "code": "<python code here>"
#     }
#   ]
# }

# Each task should be:
# - Self-contained
# - Lightweight (runnable on Raspberry Pi)
# - Use standard Python libraries (pandas, numpy, matplotlib optional)
# - Should read actual data from 'data/$DATA_TYPE/raw_data.csv' as input when executed
# - Should print or save the output (no heavy dependencies)
# """).substitute(DATA_TYPE=DATA_TYPE)

system_prompt = Template(SYSTEM_PROMPT).substitute(DATA_TYPE=DATA_TYPE)
# User prompt with data, metadata, and context
user_prompt = f"""
Sample Data:
{sample_data}

Metadata:
{json.dumps(metadata, indent=2)}

Context:
{context}
"""

# Call the LLM
response = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]    
)

# Extract response content
raw_output = response.choices[0].message.content

# Parse JSON safely
try:
    tasks_data = json.loads(raw_output)
except json.JSONDecodeError:
    print("⚠️ The LLM response was not valid JSON. Saving raw output for review.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "raw_output.txt"), "w") as f:
        f.write(raw_output)
    exit()


# save task_data to a json file inside generated_tasks/<data_type> folder
with open(os.path.join(OUTPUT_DIR, "tasks_list.json"), "w", encoding="utf-8") as f:
    json.dump(tasks_data, f, indent=2)
print("🎯 The list of all tasks with their description are successfully saved in "+os.path.join(OUTPUT_DIR, "tasks_list.json"))

