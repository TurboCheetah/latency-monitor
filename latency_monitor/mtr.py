import subprocess
from concurrent.futures import ThreadPoolExecutor
from os import environ

from influxdb_client import Point

from .latency_monitor import app
from .utils import parse_mtr


def mtr(target: str) -> dict:
    cmd = ["mtr", "-rwznc", "10", target]
    if ":" in target:
        cmd = ["mtr", "-rwznc", "10", "-6", target]

    result = subprocess.run(cmd, capture_output=True, text=True)
    parsed_output = parse_mtr(result.stdout, target)

    print(f"Ran MTR for {target}")

    return {"target": target, "stdout": result.stdout, "parsed_output": parsed_output}


@app.celery.task
def run_mtr() -> None:
    """Run the MTR command and update the global variable with the results."""
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(mtr, app.targets))

    for res in results:
        target = res["target"]
        app.redis.set(f"mtr_{target}", res["stdout"])

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
