# mini_LEI

mini_LEI runs a four-step LLM-assisted automation pipeline (`pipeline.py`). Each run wipes prior artifacts, then:
- Generates a task list for the selected data type.
- Produces task-specific code with the configured model.
- Validates the generated outputs.
- Executes the scheduled tasks on the edge scheduler.

To run the pipeline on a Raspberry Pi for a specific use case:
- Update `device.yml` with the Pi's hostname and the desired `use_case`.
- Push the changes to GitHub; the workflow handles the rest end-to-end.
