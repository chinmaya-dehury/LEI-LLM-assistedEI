# Complex Task Synthesis (LLM-Driven)

This module enables **automatic generation and execution of multi-domain tasks** (workflows) using an LLM.

---

## 1. Flow of Complex Tasks
1. **Analyze**: Parses data directories to extract schemas and discover existing subtasks.
2. **Design**: Generates composite task blueprints (`generated_tasks/complex/complex_tasks_list.json`).
3. **Resolve**: Sorts subtasks topologically (DAG) to establish execution order.
4. **Reuse & Repair**: Matches subtasks to existing scripts (using keyword/LLM fallback) and deletes/regenerates syntactically broken code.
5. **Compile**: Generates dynamic decision logic (`analyze_and_combine_results`) using the LLM and outputs a self-contained executor script.
6. **Execute**: Runs the subtasks sequentially, pipes outputs via stdin, evaluates decision rules, and saves structured results.

---

## 2. Important Validation Checks
* **Syntax Guard**: Runs AST syntax checks on all subtask and executor scripts.
* **Execution Guard**: Validates exit codes and traces standard streams for runtime issues.
* **Semantic Guard**: Verifies output JSON conforms to structural schema guidelines.
* **Resource Guard**: Checks system memory/CPU limits prior to script execution.

---

## 3. Key Features
* **Data Lineage**: Pipes results between sequential steps automatically.
* **Self-Healing**: Cleans up and fixes broken files on disk dynamically.
* **Smart Reuse**: Avoids duplicate LLM calls by reusing matching task scripts.
* **Dynamic Rules**: Creates conditional python logic on-the-fly based on the rules.

---

## 4. How to Run

### Generate Executors
```bash
python -m complex_task_synthesis.orchestration
# Pass --skip to bypass specification generation and just compile scripts
```

### Run a Workflow
* **Via Runner**:
  ```bash
  python run_complex_task.py --list
  python run_complex_task.py <task_name>
  ```
* **Directly**:
  ```bash
  python generated_tasks/complex/<task_name>_executor.py
  ```

### Outputs
* Spec file: `generated_tasks/complex/complex_tasks_list.json`
* Executor: `generated_tasks/complex/<task_name>_executor.py`
* Results payload: `output/complex/<task_name>_result.json`
