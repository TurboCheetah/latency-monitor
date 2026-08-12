from concurrent.futures import ThreadPoolExecutor
from os import environ

from influxdb_client import Point

from .app_instance import get_app
from .utils import (
    parse_mtr,
    print_mtr_result,
    print_task_complete,
    print_task_error,
    print_task_start,
    run_command,
)

app = get_app()


def mtr(target: str) -> dict:
    """Run MTR for one target and return raw and parsed results."""
    print_task_start("MTR", target)

    cmd = ["mtr", "-rwznc", "10", target]
    if ":" in target:
        cmd = ["mtr", "-rwznc", "10", "-6", target]

    try:
        result = run_command(cmd)
    except RuntimeError as exc:
        error = f"ERROR: {exc}"
        print_task_error("MTR", target, str(exc))
        return {"target": target, "stdout": error, "parsed_output": None}

    parsed_output = parse_mtr(result.stdout, target)

    print_mtr_result(target, parsed_output)

    return {"target": target, "stdout": result.stdout, "parsed_output": parsed_output}


@app.celery.task
def run_mtr() -> None:
    """Run MTR for all configured targets and store the results."""
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(mtr, app.targets))

    print_task_complete("MTR", len(results))

    for res in results:
        target = res["target"]
        app.redis.set(f"mtr_{target}", res["stdout"])

        if res["parsed_output"] is None:
            continue

        p = (
            Point("mtr")
            .tag("target", target)
            .field("loss", res["parsed_output"]["loss"])
            .field("snt", res["parsed_output"]["snt"])
            .field("last", res["parsed_output"]["last"])
            .field("avg", res["parsed_output"]["avg"])
            .field("best", res["parsed_output"]["best"])
            .field("worst", res["parsed_output"]["worst"])
            .field("stdev", res["parsed_output"]["stdev"])
            .field("raw", res["stdout"])
        )

        app.influx_write_api.write(
            bucket=environ["INFLUXDB_BUCKET"], org=environ["INFLUXDB_V2_ORG"], record=p
        )
