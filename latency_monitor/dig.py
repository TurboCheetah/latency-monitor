from concurrent.futures import ThreadPoolExecutor
from os import environ

from influxdb_client import Point

from .app_instance import get_app
from .utils import (
    parse_dig,
    print_dig_result,
    print_task_complete,
    print_task_error,
    print_task_start,
    run_command,
)

app = get_app()


def dig(target: str) -> dict:
    """Run a DNS query through one target and return raw and parsed results."""
    print_task_start("DIG", target)

    cmd = ["dig", "google.com", f"@{target}"]
    try:
        result = run_command(cmd)
    except RuntimeError as exc:
        error = f"ERROR: {exc}"
        print_task_error("DIG", target, str(exc))
        return {"target": target, "stdout": error, "parsed_output": None}

    parsed_output = parse_dig(result.stdout)

    print_dig_result(target, parsed_output)

    return {"target": target, "stdout": result.stdout, "parsed_output": parsed_output}


@app.celery.task
def run_dig() -> None:
    """Run DNS queries for all configured targets and store the results."""
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(dig, app.targets))

    print_task_complete("DIG", len(results))

    for res in results:
        target = res["target"]
        app.redis.set(f"dig_{target}", res["stdout"])

        if res["parsed_output"] is None:
            continue

        p = (
            Point("dig")
            .tag("target", target)
            .field("query_time", res["parsed_output"])
            .field("raw", res["stdout"])
        )

        app.influx_write_api.write(
            bucket=environ["INFLUXDB_BUCKET"], org=environ["INFLUXDB_V2_ORG"], record=p
        )
