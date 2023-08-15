from flask import jsonify, render_template

from .latency_monitor import app


@app.flask.route("/")
def index():
    results = {
        target: (res.decode("utf-8") if res else "")
        for target, res in zip(app.targets, app.redis.mget(app.targets))
    }

    return render_template("index.html", targets=app.targets, results=results), 200


@app.flask.route("/json")
def json():
    results = {
        target: (res.decode("utf-8") if res else "")
        for target, res in zip(app.targets, app.redis.mget(app.targets))
    }

    response = {
        "targets": app.targets,
        "command": "mtr -rwznc 10 [-6] <target>",
        "results": results,
    }
    return jsonify(response)


@app.flask.route("/trigger-mtr")
def trigger_mtr():
    result = app.celery.send_task("latency_monitor.mtr.run_mtr")
    return jsonify({"task_id": result.id}), 202
