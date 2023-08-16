from os import environ

from celery import Celery
from celery.schedules import crontab
from flask import Flask
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from redis import Redis


class App:
    def __init__(self) -> None:
        self.flask = Flask(__name__)

        self.flask.config["CELERY_CONFIG"] = {
            "broker_url": f"redis://{environ['REDIS_HOST']}:{environ['REDIS_PORT']}/0",
            "result_backend": f"redis://{environ['REDIS_HOST']}:{environ['REDIS_PORT']}/0",
            "broker_connection_retry_on_startup": True,
            "beat_schedule": {
                "mtr-task": {
                    "task": "latency_monitor.mtr.run_mtr",
                    "schedule": crontab(minute="*/5"),
                },
                "dig-task": {
                    "task": "latency_monitor.dig.run_dig",
                    "schedule": crontab(minute="*/5"),
                },
            },
        }

        self.celery = Celery(self.flask.name)
        self.celery.conf.update(self.flask.config["CELERY_CONFIG"])

        self.redis = Redis(host=environ["REDIS_HOST"], port=int(environ["REDIS_PORT"]))

        self.influx = InfluxDBClient.from_env_properties()
        self.influx_write_api = self.influx.write_api(write_options=SYNCHRONOUS)
        self.influx_query_api = self.influx.query_api()

        self.targets = environ["TARGETS"].split(",")


app = App()

# import these so they are actually registered
from . import routes as _  # noqa
from . import mtr as _  # noqa
from . import dig as _  # noqa

flask = app.flask
celery = app.celery

if __name__ == "__main__":
    app.flask.run(host="0.0.0.0", port=8080)
