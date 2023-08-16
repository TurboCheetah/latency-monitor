import subprocess
from concurrent.futures import ThreadPoolExecutor
from os import environ

from influxdb_client import Point

from .latency_monitor import app
from .utils import parse_dig


def dig(target: str) -> dict:
    cmd = ["dig", "google.com", f"@{target}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    parsed_output = parse_dig(result.stdout)

    print(f"Ran dig using {target}")

    return {"target": target, "stdout": result.stdout, "parsed_output": parsed_output}


@app.celery.task
def run_dig() -> None:
    """Run the dig command and update the global variable with the results."""
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(dig, app.targets))

    for res in results:
        target = res["target"]
        app.redis.set(f"dig_{target}", res["stdout"])

        p = (
            Point("dig")
            .tag("target", target)
            .field("query_time", res["parsed_output"])
            .field("raw", res["stdout"])
        )

        app.influx_write_api.write(
            bucket=environ["INFLUXDB_BUCKET"], org=environ["INFLUXDB_V2_ORG"], record=p
        )
