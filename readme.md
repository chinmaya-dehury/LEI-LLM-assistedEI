# LEI (LLM-Assisted Edge Intelligence)

## Introduction

LLM-assisted Edge Intelligence (LEI) bridges the gap between powerful cloud-based large language models and resource-constrained edge devices by enabling automated generation, validation, and deployment of lightweight programs on edge device.

## Control Flow of LLM-Assisted Edge Intelligence
![Basic Control Flow](lei.png)

## Description
1. Input Layer
    * **Sample Data** (e.g., last 5-min sensor readings, weather logs) → Can be in CSV, JSON, or YAML format.
    * **Metadata** (e.g., data type, generation frequency, range of values).
    * **Context** (e.g., domain knowledge, use case").

2. LLM Processing Layer (Cloud Computing Environment)
    * Uses advanced LLMs (e.g., GPT-5, DeepSeek-V3.1, Claude 4.1, Grok 4).
    * The LLM:
        * Analyzes the provided sample data, metadata, and context.
        * Thinks about what can be done with this data — identifies small, discrete tasks (t1, t2, …).
        * Writes small programs for each task, considering the programming language (e.g., Python) and edge device capability.
        * Sends all task programs and their descriptions to the edge device.

3. Edge Execution Layer
    * Edge Device receives the program(s) from the cloud.
    * Executes each program locally using actual live data (temperature, humidity, etc.).
    * Performs computations near the source, reducing latency and bandwidth usage.

4. Output Layer
    * Edge devices return processed outputs or inferences back to the cloud (if needed).
    * Enables distributed, low-latency intelligence while the LLM orchestrates logic and code generation dynamically.


# File structure

```
LEI-LLM-assistedEI/
│
├── config.py                          # Generic LLM configuration (provider, API keys, model)
├── .env.example                       # Example .env file with Ollama and cloud provider configs
├── pipeline.py                        # Main orchestrator: runs Steps 1-4 sequentially
├── resource_monitor.py                # Utility: logs CPU, memory, network metrics (used by all steps)
│
├── task_generator.py                  # Step 1: Generate task list from data + LLM
├── code_generator.py                  # Step 2: Generate Python code for each task
├── validator.py                       # Step 3: Validate and fix generated code
│
├── scheduler/
│   └── edge_scheduler_sequential.py   # Step 4: Execute validated tasks
│
├── prompts/                           # LLM prompt templates
│   ├── get_tasks.py
│   ├── get_code.py
│   └── get_validated.py
│
├── data/                              # Input layer: sample data, metadata, context
│   ├── air_quality/
│   ├── soil/
│   ├── temp_humidity/
│   └── wind/
│
├── generated_tasks/                   # Output from Steps 1-2: task lists and generated scripts
│   ├── <DATA_TYPE>/
│   │   ├── tasks_list.json
│   │   ├── task1_*.py
│   │   ├── task2_*.py
│   │   └── ...
│
├── output/                            # Output from Step 4: task execution results
│   └── <DATA_TYPE>/
│       ├── task_output_*.json
│       └── ...
│
├── timestamp_path/                    # Execution timing logs for each step
│   └── <DATA_TYPE>/
│       ├── pipeline_timestamp_*.csv
│       ├── resource_usage_step1_*.csv
│       ├── resource_usage_step2_*.csv
│       ├── resource_usage_step3_*.csv
│       └── resource_usage_step4_*.csv
│
└── Utility & Analysis (Independent)
    ├── resource_stat/
    │   ├── resource_stat.py           # Background monitor: logs system resource usage
    │   └── stop_monitor.py            # Utility: stops the background monitor
    │
    ├── publish_intelligence/
    │   └── edge_dashboard.py          # Visualization (not integrated in pipeline)
    │
    └── result_code/                   # Testbed analysis & reporting
        ├── result_*.py                # Individual step analysis scripts
        ├── combine_cases_plots.py      # Cross-step visualization & comparison
        └── res_complete_pipeline.py    # End-to-end pipeline result summary
```

## Pipeline Steps (Steps 1-4)

### Step 1: Task Generator
`task_generator.py` analyzes input data (sample data, metadata, context) and uses an LLM to identify discrete tasks.

* Reads `sample_data.csv`, `metadata.json`, `context.txt` from `data/<DATA_TYPE>/`
* Uses LLM to analyze patterns and generate task descriptions
* Outputs: `generated_tasks/<DATA_TYPE>/tasks_list.json`
* Logs resource metrics to `timestamp_path/<DATA_TYPE>/`

### Step 2: Code Generator
`code_generator.py` generates executable Python code for each identified task.

* Reads task list from Step 1
* Uses LLM to write production-ready Python code
* Outputs: `generated_tasks/<DATA_TYPE>/task*.py` scripts
* Logs resource metrics and code generation stats

### Step 3: Validator
`validator.py` executes and validates generated code.

* Runs each task script with test data
* Validates execution, error handling, output format
* Auto-corrects failures via LLM-assisted code repair
* Outputs: validation summaries and metrics
* Logs resource metrics and validation stats

### Step 4: Edge Scheduler
`scheduler/edge_scheduler_sequential.py` executes validated tasks sequentially.

* Discovers and runs all scripts in `generated_tasks/<DATA_TYPE>/`
* Collects execution results and timings
* Outputs: `output/<DATA_TYPE>/task_output_*.json`
* Logs resource metrics and execution stats


## Shared Utilities Module

### `shared_utils.py` — Cross-Pipeline Utility Functions

To eliminate code duplication and improve maintainability, common functionality is consolidated in `shared_utils.py`. All pipeline steps import and use these utilities instead of defining their own versions.

#### Core Functions:

**1. Model Name Sanitization**
```python
sanitize_model_name(model: str) -> str
```
- Sanitizes model names for safe use in filenames
- Removes/replaces special characters: spaces, colons, forward slashes, backslashes
- Used by all steps (Step 1-4) to generate consistent CSV/log filenames
- Example: `"gpt-4o:turbo"` → `"gpt-4o_turbo"`

**2. JSON Extraction**
```python
extract_first_json_object(text: str) -> dict
extract_json_blob(text: str) -> str
```
- `extract_first_json_object()`: Extracts and parses JSON object from text (handles code fences, extra NL text)
- `extract_json_blob()`: Extracts JSON string without parsing (used for extracting JSON before decision-making)
- Robust against LLM output variations (warnings, markdown fences, surrounding text)
- Used in Steps 1-2 to parse LLM responses

**3. Environment & Timing**
```python
get_environment_vars() -> Dict[str, str]
get_current_time_ist() -> str
get_current_time_perf() -> float
```
- `get_environment_vars()`: Retrieves RUN_ID and RUN_COUNT from environment or generates defaults
- `get_current_time_ist()`: Returns ISO-format timestamp in IST (India Standard Time, UTC+5:30)
- `get_current_time_perf()`: Returns performance counter for precise timing measurement

**4. Path & CSV Setup**
```python
setup_timing_paths(data_type: str, step_name: str, model_name: str) -> Dict[str, str]
ensure_csv_with_headers(csv_path: str, fieldnames: List[str]) -> bool
```
- `setup_timing_paths()`: Generates timestamped directory and CSV file paths for each pipeline step
  - Returns dict with keys: `TIMESTAMP_PATH`, `STEP_CSV`, `RESOURCE_CSV`, `RUN_ID`, `SANITIZED_MODEL`
  - Ensures paths are relative and system-agnostic (no hardcoded Windows/Linux paths)
  - Used by all 4 pipeline steps to maintain consistent naming conventions
- `ensure_csv_with_headers()`: Creates CSV file with headers if missing
  - Idempotent: safe to call multiple times
  - Used for initializing step-specific CSV logs

**5. CSV Operations**
```python
append_timing_rows_to_csv(csv_path: str, rows: list, fieldnames: list) -> None
load_resource_summary(resource_summary_path: str) -> Dict[str, Any]
```
- `append_timing_rows_to_csv()`: Appends rows to CSV with automatic header creation
  - Handles file creation, field validation, resource metric injection
  - Used by all steps for consistent CSV logging across pipeline
- `load_resource_summary()`: Loads CPU/memory metrics from `resource_stat/resource_usage_summary.json`
  - Returns dict with keys: `resource_generated_at`, `avg_cpu_1m`, `avg_mem_1m`, `avg_cpu_5m`, `avg_mem_5m`
  - Gracefully handles missing/malformed files

**6. Data Loading**
```python
load_context_for_data_type(data_type: str) -> Dict[str, Any]
```
- Loads `sample_data.csv`, `metadata.json`, `context.txt` for a given data type
- Returns dict with keys: `sample_data` (str), `metadata` (dict), `context` (str)
- Handles missing files gracefully (returns empty values)
- Used in Steps 1-2 to feed LLM with contextual data

**7. Text Processing**
```python
truncate(text: str, max_chars: int) -> str
normalize_code_string(code: str) -> str
```
- `truncate()`: Safely truncates text to max length with ellipsis indicator
- `normalize_code_string()`: Removes code fences and unescapes common sequences
- Used in code generation and validation steps

#### Design Principles:

- **Path Agnostic**: All paths are relative (e.g., `"data/{data_type}"`, `"timestamp_path/{data_type}"`) — works on any OS without modification
- **No Hardcoding**: No system-specific or Windows/Linux-specific paths embedded in functions
- **Idempotent Operations**: Safe to call multiple times (CSV creation, timing appends won't corrupt data)
- **Graceful Degradation**: Missing files/fields return sensible defaults instead of crashing

#### Usage Across Pipeline:

| Function | Step 1 | Step 2 | Step 3 | Step 4 |
|----------|--------|--------|--------|--------|
| `sanitize_model_name()` | ✓ | ✓ | ✓ | ✓ |
| `extract_first_json_object()` | ✓ | ✓ | ✓ | – |
| `get_environment_vars()` | ✓ | ✓ | ✓ | ✓ |
| `setup_timing_paths()` | ✓ | ✓ | ✓ | ✓ |
| `append_timing_rows_to_csv()` | ✓ | ✓ | ✓ | ✓ |
| `load_context_for_data_type()` | ✓ | ✓ | ✓ | – |
| `load_resource_summary()` | ✓ | ✓ | ✓ | – |
| `truncate()` | – | ✓ | – | – |

### CSV Naming Convention

Each pipeline step generates its own CSV log with consistent naming:
- **Step 1 (Task Generator)**: `step1_{SANITIZED_MODEL}_{RUN_ID}.csv`
- **Step 2 (Code Generator)**: `step2_{SANITIZED_MODEL}_{RUN_ID}.csv`
- **Step 3 (Validator)**: `step3_{SANITIZED_MODEL}_{RUN_ID}.csv`
- **Step 4 (Scheduler)**: `step4_{SANITIZED_MODEL}_{RUN_ID}.csv`
- **Resource Metrics**: `step{N}_resource_{SANITIZED_MODEL}_{RUN_ID}.csv` (generated by `log_resource_metrics()`)

All CSVs are stored in `timestamp_path/{DATA_TYPE}/` directory with timestamped rotation.

## Independent Components (Not in Main Pipeline)

* **resource_monitor.py** — Captures system metrics (CPU, memory, network I/O, temperature) and logs to CSV for performance evaluation across all pipeline steps.
* **resource_stat/** — Background monitor (`resource_stat.py`, `stop_monitor.py`) that runs concurrently to track overall system load; generates `resource_usage_summary.json` for adaptive task generation.
* **result_code/** — Post-execution analysis tools (`result_step*.py`, `result_avg_cpu.py`, `combine_cases_plots.py`) for evaluating pipeline performance and comparing results across runs.
* **publish_intelligence/edge_dashboard.py** — Streamlit dashboard for real-time visualization (under development, not yet integrated in pipeline).

# How to execute?

## Clone the Repository
```
git clone https://github.com/your-username/LEI-LLM-assistedEI.git
cd LEI-LLM-assistedEI
```

## Setup
1. Set up your Python virtual environment:
   ```
   python -m venv venv
   ```
   * Windows: `venv\Scripts\activate`
   * Linux/macOS: `source venv/bin/activate`

2. Install dependencies:
   ```
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Configure your environment (choose ONE option below):

   **OPTION A: Use a Cloud LLM Provider (ChatGPT, Gemini, Groq, Claude, etc.)**
   
   Create a `.env` file in the project root with:
   ```
   LLM_PROVIDER=generic
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_API_KEY=your-groq-api-key-here
   LLM_MODEL=llama-3.3-70b-versatile
   ```
   
   For other providers, set `LLM_BASE_URL` and `LLM_API_KEY` accordingly:
   - **OpenAI (ChatGPT)**: `https://api.openai.com/v1`
   - **Google Gemini**: `https://generativelanguage.googleapis.com/v1beta/openai`
   - **Anthropic Claude**: `https://api.anthropic.com/v1`
   - See `.env.example` for more options
   
   **OPTION B: Use Ollama (Local LLM - Self-Hosted)**
   
   1. Install Ollama: https://ollama.ai
   2. Start Ollama: `ollama serve`
   3. Pull a model: `ollama pull llama2` (or any available model)
   4. Create a `.env` file in the project root with:
   ```
   LLM_PROVIDER=ollama
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_API_KEY=ollama
   LLM_MODEL=llama2
   ```
   
   See `.env.example` for detailed configuration examples for all providers.
   
   4. Update `config.py` to set `DATA_TYPE` if needed (e.g., `DATA_TYPE="air_quality"`)
      - Options: `temp_humidity`, `air_quality`, `soil`, `wind`

## Run the complete pipeline

**Recommended: Start resource monitor first** (optional but useful for performance tracking):
```
python resource_stat/resource_stat.py &
```
This runs in the background and logs system metrics to `resource_stat/resource_usage_summary.json`.

**Then run the pipeline:**
```
python pipeline.py
```
This executes Steps 1–4 sequentially for 5 runs with the configured model, logging all results and performance metrics.

**Later, stop the background monitor:**
```
python resource_stat/stop_monitor.py
```

## Run individual steps
* **Step 1 – Generate task list:**
  ```
  python task_generator.py
  ```

* **Step 2 – Generate code for tasks:**
  ```
  python code_generator.py
  ```

* **Step 3 – Validate generated code:**
  ```
  python validator.py
  ```

* **Step 4 – Execute tasks on edge:**
  ```
  python scheduler/edge_scheduler_sequential.py
  ```
## Future Work

- Publish Intelligence (Dashboard Enhancement)
- Scheduler Algorithm Improvements

## License (To Add)
This project is open-source and available under the MIT License. See LICENSE file for details.
