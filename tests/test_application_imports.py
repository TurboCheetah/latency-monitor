import os
import subprocess
import sys

TEST_ENVIRONMENT = {
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "TARGETS": "1.1.1.1",
    "INFLUXDB_V2_URL": "http://localhost:8086",
    "INFLUXDB_V2_ORG": "test-org",
    "INFLUXDB_V2_TOKEN": "test-token",
    "INFLUXDB_BUCKET": "test-bucket",
}


def test_application_import_and_celery_cli_entrypoint():
    environment = os.environ | TEST_ENVIRONMENT
    script = """
from latency_monitor.latency_monitor import app, celery, flask
from latency_monitor.mtr import app as mtr_app, run_mtr
from latency_monitor.dig import app as dig_app, run_dig

assert app is mtr_app is dig_app
assert app.celery is celery
assert app.flask is flask
assert run_mtr.name == "latency_monitor.mtr.run_mtr"
assert run_dig.name == "latency_monitor.dig.run_dig"
assert "latency_monitor.mtr.run_mtr" in celery.tasks
assert "latency_monitor.dig.run_dig" in celery.tasks
"""

    import_result = subprocess.run(
        [sys.executable, "-c", script],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert import_result.returncode == 0, import_result.stderr

    cli_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "latency_monitor.latency_monitor:celery",
            "report",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli_result.returncode == 0, cli_result.stderr


def test_importing_task_module_first_uses_initialized_application():
    environment = os.environ | TEST_ENVIRONMENT
    script = """
from latency_monitor.mtr import app as mtr_app
from latency_monitor.app_instance import get_app
from latency_monitor.latency_monitor import app
from latency_monitor.routes import app as routes_app

assert app is mtr_app is routes_app is get_app()
assert "latency_monitor.mtr.run_mtr" in app.celery.tasks
assert "latency_monitor.dig.run_dig" in app.celery.tasks
assert {"/", "/json", "/trigger-mtr", "/trigger-dig"} <= {
    rule.rule for rule in app.flask.url_map.iter_rules()
}
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
