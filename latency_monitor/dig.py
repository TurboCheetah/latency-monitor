import subprocess
from os import environ

from influxdb_client import Point

from .latency_monitor import app
from .utils import parse_dig


@app.celery.task
def run_dig():
    """Run the dig command and update the global variable with the results."""
    for target in app.targets:
        cmd = ["dig", "google.com", f"@{target}"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        app.redis.set(f"dig_{target}", result.stdout)

        parsed_output = parse_dig(result.stdout)

        p = (
            Point("dig")
            .tag("target", target)
            .field("query_time", parsed_output)
            .field("raw", result.stdout)
        )

        app.influx_write_api.write(
            bucket=environ["INFLUXDB_BUCKET"], org=environ["INFLUXDB_V2_ORG"], record=p
        )

        print(f"Ran dig using {target}")
