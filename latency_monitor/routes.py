from typing import cast

from flask import Response, jsonify, render_template

from .app_instance import get_app

app = get_app()


def _cached_results(prefix: str) -> dict[str, str]:
    """Read cached command output for every configured target."""
    values = cast(
        list[bytes | None],
        app.redis.mget([f"{prefix}_{target}" for target in app.targets]),
    )
    return {
        target: (value.decode("utf-8") if value else "")
        for target, value in zip(app.targets, values)
    }


@app.flask.route("/")
def index() -> tuple[str, int]:
    """Render the monitor dashboard with cached MTR and DIG output."""
    return (
        render_template(
            "index.html",
            targets=app.targets,
            mtr_results=_cached_results("mtr"),
            dig_results=_cached_results("dig"),
        ),
        200,
    )


@app.flask.route("/json")
def json() -> tuple[Response, int]:
    """Return cached monitoring results as JSON."""
    response = {
        "mtr": {
            "targets": app.targets,
            "command": "mtr -rwznc 10 [-6] <target>",
            "results": _cached_results("mtr"),
        },
        "dig": {
            "targets": app.targets,
            "command": "dig google.com @<target>",
            "results": _cached_results("dig"),
        },
    }
    return jsonify(response), 200


@app.flask.route("/trigger-mtr")
def trigger_mtr() -> tuple[Response, int]:
    """Queue an immediate MTR collection task."""
    result = app.celery.send_task("latency_monitor.mtr.run_mtr")
    return jsonify({"task_id": result.id}), 202


@app.flask.route("/trigger-dig")
def trigger_dig() -> tuple[Response, int]:
    """Queue an immediate DIG collection task."""
    result = app.celery.send_task("latency_monitor.dig.run_dig")
    return jsonify({"task_id": result.id}), 202
