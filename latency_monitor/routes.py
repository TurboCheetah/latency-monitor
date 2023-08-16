from flask import Response, jsonify, render_template

from .latency_monitor import app


@app.flask.route("/")
def index() -> tuple[str, int]:
    mtr_results = {
        target: (res.decode("utf-8") if res else "")
        for target, res in zip(
            app.targets, app.redis.mget([f"mtr_{target}" for target in app.targets])
        )
    }

    dig_results = {
        target: (res.decode("utf-8") if res else "")
        for target, res in zip(
            app.targets, app.redis.mget([f"dig_{target}" for target in app.targets])
        )
    }

    return (
        render_template(
            "index.html",
            targets=app.targets,
            mtr_results=mtr_results,
            dig_results=dig_results,
        ),
        200,
    )


@app.flask.route("/json")
def json() -> tuple[Response, int]:
    mtr_results = {
        target: (res.decode("utf-8") if res else "")
        for target, res in zip(
            app.targets, app.redis.mget([f"mtr_{target}" for target in app.targets])
        )
    }

    dig_results = {
        target: (res.decode("utf-8") if res else "")
        for target, res in zip(
            app.targets, app.redis.mget([f"dig_{target}" for target in app.targets])
        )
    }

    response = {
        "mtr": {
            "targets": app.targets,
            "command": "mtr -rwznc 10 [-6] <target>",
            "results": mtr_results,
        },
        "dig": {
            "targets": app.targets,
            "command": "dig google.com @<target>",
            "results": dig_results,
        },
    }
    return jsonify(response), 200


@app.flask.route("/trigger-mtr")
def trigger_mtr() -> tuple[Response, int]:
    result = app.celery.send_task("latency_monitor.mtr.run_mtr")
    return jsonify({"task_id": result.id}), 202


@app.flask.route("/trigger-dig")
def trigger_dig() -> tuple[Response, int]:
    result = app.celery.send_task("latency_monitor.dig.run_dig")
    return jsonify({"task_id": result.id}), 202
