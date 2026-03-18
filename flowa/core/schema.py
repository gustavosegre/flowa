def validate_pipeline_data(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Pipeline YAML must be a mapping")

    if "name" not in data:
        raise ValueError("Pipeline is missing required field: 'name'")

    if "steps" not in data:
        raise ValueError("Pipeline is missing required field: 'steps'")

    if not isinstance(data["steps"], list) or not data["steps"]:
        raise ValueError("'steps' must be a non-empty list")

    seen_names = set()
    for step in data["steps"]:
        if not isinstance(step, dict):
            raise ValueError("Each step must be a mapping")

        step_name = step.get("name", "<unnamed>")

        if "name" not in step:
            raise ValueError("A step is missing required field: 'name'")

        if step_name in seen_names:
            raise ValueError(f"Duplicate step name: '{step_name}'")
        seen_names.add(step_name)

        if "run" not in step:
            raise ValueError(f"Step '{step_name}' is missing required field: 'run'")

        retries = step.get("retries", 0)
        if not isinstance(retries, int) or retries < 0:
            raise ValueError(f"Step '{step_name}': 'retries' must be a non-negative integer")

        timeout = step.get("timeout_seconds")
        if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
            raise ValueError(f"Step '{step_name}': 'timeout_seconds' must be a positive integer")
