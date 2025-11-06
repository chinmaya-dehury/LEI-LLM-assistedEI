"""
validator.py
-------------------
This module defines a function to validate generated Python task code
using an LLM in an LLM-assisted edge computing system.
The module sends generated task code, along with supporting data,
to an LLM for validation. The LLM checks syntax, logic, requirement compliance, and edge-case
handling before we persist the code to disk.

"""

import json
from string import Template

from openai import OpenAI
from config import OPENAI_API_KEY, DATA_TYPE
from prompts.get_validator import SYSTEM_PROMPT

# Initialize the LLM client once so repeated validations reuse the same session.
client = OpenAI(api_key=OPENAI_API_KEY)

# Paths align with task_code_generator_update.py so both modules share inputs.
BASE_PATH = f"data/{DATA_TYPE}/"
DATA_PATH = BASE_PATH + "sample_data.csv"
META_PATH = BASE_PATH + "metadata.json"
CONTEXT_PATH = BASE_PATH + "context.txt"


def _load_inputs():
	"""Load sample data, metadata, and context once per module import."""

	with open(DATA_PATH, "r", encoding="utf-8") as data_file:
		sample = data_file.read()

	with open(META_PATH, "r", encoding="utf-8") as meta_file:
		meta = json.load(meta_file)

	with open(CONTEXT_PATH, "r", encoding="utf-8") as context_file:
		ctx = context_file.read()

	return sample, meta, ctx


SAMPLE_DATA, METADATA, CONTEXT = _load_inputs()


def call_llm_for_validator(task_data):
	"""Validate generated task code via the LLM described in get_validator.py."""

	try:
		system_prompt = Template(SYSTEM_PROMPT).substitute(DATA_TYPE=DATA_TYPE)
	except KeyError:
		system_prompt = SYSTEM_PROMPT

	if isinstance(task_data, dict):
		task_payload = json.dumps(task_data, ensure_ascii=False, indent=2)
	else:
		task_payload = str(task_data)

	user_prompt = f"""
	Sample Data:
	{SAMPLE_DATA}

	Metadata:
	{json.dumps(METADATA, indent=2)}

	Context:
	{CONTEXT}

	Tasks Code:
	{task_payload}
	"""

	response = client.chat.completions.create(
		model="gpt-5",
		messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
	)

	raw_output = response.choices[0].message.content

	try:
		validation_result = json.loads(raw_output)
	except json.JSONDecodeError:
		print("Validator LLM response was not valid JSON. Raw output:")
		print(raw_output)
		return None

	return validation_result

