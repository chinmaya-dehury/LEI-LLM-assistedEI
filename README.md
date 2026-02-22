# mini_LEI

mini_LEI runs a four-step LLM-assisted automation pipeline (`pipeline.py`). Each run wipes prior artifacts, then:
- Generates a task list for the selected data type.
- Produces task-specific code with the configured model.
- Validates the generated outputs.
- Executes the scheduled tasks on the edge scheduler.

To execute the pipeline (and log timestamps per model/run) run:
```bash
python pipeline.py
```
