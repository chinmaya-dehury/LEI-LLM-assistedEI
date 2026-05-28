# Complex Task Synthesis (LLM-Driven)

This module enables **automatic generation of composite (multi-domain) tasks** using an LLM, based on all available domains, sample data, metadata, and existing tasks. **Each complex task is generated as an executable Python script** that:
- Executes subtasks and collects their outputs
- Applies intelligent decision logic combining results from multiple domains
- Considers resource constraints before execution
- Returns actionable insights

## How it works

1. **LLM analyzes all available domains, sample data, metadata, and existing tasks**: analysis.py
2. **LLM generates composite task specifications** (with subtasks, dependencies, and data flow): generation.py
3. **Composite task generator** checks which subtasks are available and which need generation: generation.py
4. **Executor generator** creates an executable Python script for each composite task: run_complex_tasks.py

## How to run

### Step 1: Generate Complex Tasks and Executors

Open a terminal in the project root and run:

```bash
python -m complex_task_synthesis.orchestration
```

This will:
- Call the LLM to generate composite task specs (based on all available data)
- Generate **executable Python scripts** for each composite task
- Save results to:
  - `generated_tasks/complex/complex_tasks_list.json` (all composite tasks)
  - `generated_tasks/complex/*_executor.py` (executable scripts for each task)

### Step 2: Execute a Complex Task

**Option A - Using the helper script:**
```bash
python run_complex_task.py --list              # List all available tasks
python run_complex_task.py air_quality_and_wind_pattern_analysis  # Run a task
```

**Option B - Direct execution:**
```bash
python generated_tasks/complex/air_quality_and_wind_pattern_analysis_executor.py
```

### Step 3: View Results

The executor script will:
1. Check available system resources (memory, CPU)
2. Execute each subtask in order
3. Combine outputs with business logic
4. Print actionable insights

Example output for air quality + wind analysis:
```
[WORKFLOW] Air Quality and Wind Pattern Analysis
[RESOURCES] Resources available
[EXECUTE] Starting subtask execution...

[1] Executing: Main Pollutant Identification (main_pollutant_identification) from air_quality
[2] Executing: Wind Speed Analysis (wind_speed_analysis) from wind

[ANALYZE] Applying decision logic...
[RESULT] FINAL ANALYSIS
  pm25_level                     → 150
  wind_speed                     → 2.5
  conclusion                     → POLLUTION TRAP: High PM2.5 with low wind
  severity                       → HIGH
  recommendation                 → Alert issued: Pollution likely to increase...
```

## Key Features

✅ **Automatic subtask execution** - Runs subtasks and passes data between them  
✅ **Business logic** - Makes intelligent decisions combining multiple data sources  
✅ **Resource-aware** - Checks memory, CPU before execution  
✅ **JSON output** - Results in structured format for downstream processing  
✅ **Extensible decision logic** - Easily add new analysis rules per domain combination  

## Core Components

- `generation.py` — Composite generation (includes LLM-driven generator)
- `analysis.py` — Task analysis and dependency resolution
- `generation.py` — Composite task and executor generation
- `orchestration.py` — Main orchestrator
- `utils.py` — Utility functions

## Output

- Composite task specs: `generated_tasks/complex/complex_tasks_list.json`
- **Executable scripts:** `generated_tasks/complex/*_executor.py`

---

**To generate and run everything:**

```bash
# Generate
python -m complex_task_synthesis.orchestration

# Run a specific task
python run_complex_task.py air_quality_and_wind_pattern_analysis

# Or list and choose
python run_complex_task.py --list
```
