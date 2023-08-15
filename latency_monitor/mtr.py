import subprocess
from os import environ

from influxdb_client import Point

from .latency_monitor import app
from .utils import parse_mtr


@app.celery.task
def run_mtr():
    """Run the MTR command and update the global variable with the results."""
    for target in app.targets:
        cmd = ["mtr", "-rwznc", "10", target]
        # check if the target is an IPv4 or IPv6 address
        if ":" in target:
            cmd = ["mtr", "-rwznc", "10", "-6", target]

        result = subprocess.run(cmd, capture_output=True, text=True)
        app.redis.set(target, result.stdout)

        parsed_output = parse_mtr(result.stdout, target)

        p = (
            Point("mtr")
            .tag("target", target)
            .field("loss", parsed_output["loss"])
            .field("snt", parsed_output["snt"])
            .field("last", parsed_output["last"])
            .field("avg", parsed_output["avg"])
            .field("best", parsed_output["best"])
            .field("worst", parsed_output["worst"])
            .field("stdev", parsed_output["stdev"])
            .field("raw", result.stdout)
        )

        app.influx_write_api.write(
            bucket=environ["INFLUXDB_BUCKET"], org=environ["INFLUXDB_V2_ORG"], record=p
        )

        print(f"Ran MTR for {target}")
