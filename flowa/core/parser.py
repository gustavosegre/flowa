import yaml
from flowa.core.pipeline import Pipeline, Step
from flowa.core.schema import validate_pipeline_data
from flowa.scheduler.schedule_parser import parse_schedule


def load_pipeline(path: str) -> Pipeline:
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    validate_pipeline_data(data)

    steps = []
    for step_data in data["steps"]:
        depends = step_data.get("depends_on", [])
        if isinstance(depends, str):
            depends = [depends]

        step = Step(
            name=step_data["name"],
            run=step_data["run"],
            depends_on=depends,
            retries=step_data.get("retries", 0),
            continue_on_error=step_data.get("continue_on_error", False),
            timeout_seconds=step_data.get("timeout_seconds"),
            working_dir=step_data.get("working_dir"),
        )
        steps.append(step)

    return Pipeline(
        name=data["name"],
        steps=steps,
        schedule=parse_schedule(data),
        max_parallel=data.get("max_parallel", 4),
    )
