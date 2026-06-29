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
├── benchmark_v3.py                    # Coordinator for LEI steps and Ollama models comparison
├── benchmark_runner_triple.py         # Coordinator for 3-way framework comparison (LEI, AutoGen, LangGraph)
│
├── task_generator.py                  # Step 1: Generate task list from data + LLM
├── code_generator.py                  # Step 2: Generate Python code for each task
├── validator.py                       # Step 3: Validate and fix generated code
│   └── val_semantic.py                # Semantic validation: strict Pydantic v2 models for task output validation
│
├── scheduler/
│   └── edge_scheduler.py              # Step 4: Execute validated tasks with concurrent orchestration
│
├── prompts/                           # LLM prompt templates
│   ├── get_tasks.py
│   ├── get_code.py
│   └── get_validated.py
│
├── data/                              # Input layer: sample data, metadata, context
│   ├── agri-data/
│   ├── air-quality/
│   ├── lab-data/
│   └── meteo-data/
│
├── generated_tasks/                   # Output from Steps 1-2: task lists and generated scripts
│   └── <DATA_TYPE>/
│       ├── tasks_list.json
│       ├── task1_*.py
│       └── ...
│
├── output/                            # Output from Step 4: task execution results
│   └── <DATA_TYPE>/
│       ├── task_output_*.json
│       └── ...
│
├── results/                           # Output directory for benchmark results
│   ├── benchmark_results_v3.csv       # Detailed model comparison step-level metrics
│   ├── benchmark_summary_v3.csv       # Statistical summaries for model comparison
│   └── <DATA_TYPE>/
│       ├── benchmark_results_triple.csv # Detailed framework comparison metrics
│       ├── benchmark_summary_triple.csv  # Statistical summaries for framework comparison
│       └── samples/                   # High-frequency (0.1s) CPU/memory sample logs
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
`validator.py` executes and validates generated code with semantic validation.

* Runs each task script with test data
* **Semantic Validation** (via `val_semantic.py`): 
  - Strict Pydantic v2 validation with `strict=True, extra="forbid"`
  - Rejects type coercion and hallucinated fields
  - Validates task output structure: `{task_name, result_summary: [{key, value, metric?}]}`
  - Business rule checks: task name matching, minimum result counts
* Auto-corrects failures via LLM-assisted code repair (up to 2 retries)
* On validation error: extracts error details and passes to LLM for correction
* Outputs: validation summaries and metrics
* Logs resource metrics and validation stats via `write_validator_detailed_row()`

### Step 4: Edge Scheduler
`scheduler/edge_scheduler.py` executes validated tasks with concurrent orchestration.

* **Concurrent Execution**: ProcessPoolExecutor with 4 configurable workers for parallel task execution
* **Task Discovery**: Automatically discovers all scripts in `generated_tasks/<DATA_TYPE>/`
* **Retry Support**: Automatic retry mechanism (up to 2 retries) for failed tasks with priority-based queuing
* **Graceful Shutdown**: Signal handling (SIGINT/SIGTERM) for clean process termination
* **Task Isolation**: Subprocess-based execution prevents one failed task from crashing the scheduler
* **Timeout Protection**: 120-second timeout per task with proper error handling
* **Outputs**: `output/<DATA_TYPE>/task_output_*.json` with execution results and metrics
* **Logs**: CSV metrics via `write_scheduler_detailed_row()` in shared_utils.py



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
   DATA_TYPE=air_quality
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
   DATA_TYPE=air_quality
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

## Run Benchmarks

### 1. Framework Comparison (LEI vs AutoGen vs LangGraph)
To compare the performance of LEI against AutoGen and LangGraph across all discovered datasets (e.g., `agri-data`, `air-quality`, etc.) for 10 runs each:

1. Ensure that the sibling repositories (`autogen` and `langgraph`) are located in the same parent directory as `LEI-LLM-assistedEI`.
2. Comment out any `DATA_TYPE` definitions inside your `.env` file since the script overrides it dynamically.
3. Run the framework comparison script from the root of the `LEI-LLM-assistedEI` folder:
   ```bash
   python benchmark_runner_triple.py --runs 10
   ```
4. **Output Folder & Files**:
   - Detailed iteration results: [benchmark_results_triple.csv](results/%3Cdataset_name%3E/benchmark_results_triple.csv) (saved in `results/<dataset_name>/`)
   - Statistical summaries: [benchmark_summary_triple.csv](results/%3Cdataset_name%3E/benchmark_summary_triple.csv) (saved in `results/<dataset_name>/`)
   - Raw CPU & memory usage samples (0.1s interval): `results/<dataset_name>/samples/`

### 2. Ollama Code-Based Model Comparison on LEI Framework (v3)
To compare the performance of different Ollama code models (`qwen2.5-coder`, `deepseek-coder`, `codegemma`, `granite-code`, `yi-coder`, `codellama`) across all datasets (`agri-data`, `air-quality`, `lab-data`, `meteo-data`) for 10 runs each, profiling step-by-step (task generation, code generation, validation, and scheduling):

1. Ensure Ollama is running and has the following models pulled:
   - `qwen2.5-coder:7b-instruct-q8_0`
   - `deepseek-coder:6.7b-instruct-q8_0`
   - `codegemma:7b-instruct-v1.1-q8_0`
   - `granite-code:8b-instruct-q8_0`
   - `yi-coder:9b-chat-q8_0`
   - `codellama:7b-instruct-q8_0`
2. Run the models comparison script from the root of the `LEI-LLM-assistedEI` folder:
   ```bash
   python benchmark_v3.py
   ```
3. **Output Folder & Files**:
   - Detailed step-level execution metrics (task_generator, code_generator, validator, scheduler): [benchmark_results_v3.csv](results/benchmark_results_v3.csv) (saved in `results/`)
   - Statistical summaries grouping by dataset, model, and pipeline step: [benchmark_summary_v3.csv](results/benchmark_summary_v3.csv) (saved in `results/`)
   - Raw CPU & memory usage samples (0.1s interval) for each step: `results/<dataset_name>/samples/`


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
  python scheduler/edge_scheduler.py
  ```
## Future Work

- Publish Intelligence (Dashboard Enhancement)
- Scheduler Algorithm Improvements

## Citation

If you use this code, please cite it using the following BibTeX entry:

```bibtex
@article{dehury2026llm,
  title={LLM-assisted Agentic Edge Intelligence Framework},
  author={Dehury, Chinmaya Kumar and Kushwaha, Siddharth Singh and Zhang, Qiyang and Saleh, Alaa and Donta, Praveen Kumar},
  journal={arXiv preprint arXiv:2604.09607},
  year={2026}
}
```

## License

This project is open-source and available under the MIT License. See LICENSE file for details.
