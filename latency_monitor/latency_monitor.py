from importlib import import_module
from os import environ

from celery import Celery
from celery.schedules import crontab
from flask import Flask
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from redis import Redis


def parse_crontab(cron_expr: str) -> crontab:
    """Parse a five-field cron expression into a Celery crontab schedule."""
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression '{cron_expr}': expected 5 fields")
    return crontab(
        minute=parts[0],
        hour=parts[1],
        day_of_month=parts[2],
        month_of_year=parts[3],
        day_of_week=parts[4],
    )


class App:
    def __init__(self) -> None:
        self.flask = Flask(__name__)

        schedule = parse_crontab(environ.get("SCHEDULE", "*/5 * * * *"))
        redis_host = environ.get("REDIS_HOST", "localhost")
        redis_port = environ.get("REDIS_PORT", "6379")

        self.flask.config["CELERY_CONFIG"] = {
            "broker_url": f"redis://{redis_host}:{redis_port}/0",
            "result_backend": f"redis://{redis_host}:{redis_port}/0",
            "broker_connection_retry_on_startup": True,
            "beat_schedule": {
                "mtr-task": {
                    "task": "latency_monitor.mtr.run_mtr",
                    "schedule": schedule,
                },
                "dig-task": {
                    "task": "latency_monitor.dig.run_dig",
                    "schedule": schedule,
                },
            },
        }

        self.celery = Celery(self.flask.name)
        self.celery.conf.update(self.flask.config["CELERY_CONFIG"])

        self.redis = Redis(host=redis_host, port=int(redis_port))

        self.influx = InfluxDBClient.from_env_properties()
        self.influx_write_api = self.influx.write_api(write_options=SYNCHRONOUS)
        self.influx_query_api = self.influx.query_api()

        self.targets = environ.get("TARGETS", "1.1.1.1").split(",")


app = App()

# Register routes and Celery tasks after the singleton is available. These
# imports are intentionally kept here so every module receives the same App.
from .app_instance import set_app

set_app(app)
for module_name in ("dig", "mtr", "routes"):
    import_module(f"{__package__}.{module_name}")

flask = app.flask
celery = app.celery

if __name__ == "__main__":
    app.flask.run(host="0.0.0.0", port=8080)
