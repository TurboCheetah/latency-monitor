import subprocess

from celery import Celery
from celery.schedules import crontab
from flask import Flask, jsonify
from redis import Redis

app = Flask(__name__)
app.config["CELERY_CONFIG"] = {
    "broker_url": "redis://mtr-redis:6379/0",
    "result_backend": "redis://mtr-redis:6379/0",
    "broker_connection_retry_on_startup": True,
    "beat_schedule": {
        "run-mtr-every-5-minutse": {
            "task": "mtr_probe.mtr_probe.run_mtr",
            "schedule": crontab(minute="*/5"),
        },
    },
}

celery = Celery(app.name)
celery.conf.update(app.config["CELERY_CONFIG"])

redis = Redis(host="mtr-redis", port=6379, db=0)

targets = ["1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"]


@celery.task
def run_mtr():
    """Run the MTR command and update the global variable with the results."""
    for target in targets:
        cmd = ["mtr", "-rwznc", "10", target]
        # check if the target is an IPv4 or IPv6 address
        if ":" in target:
            cmd = ["mtr", "-rwznc", "10", "-6", target]

        result = subprocess.run(cmd, capture_output=True, text=True)
        redis.set(target, result.stdout)

        print(f"Ran MTR for {target}")


@app.route("/json")
def json():
    results = {
        target: (res.decode("utf-8") if res else "")
        for target, res in zip(targets, redis.mget(targets))
    }

    response = {
        "targets": targets,
        "command": "mtr -rwznc 10 [-6] <target>",
        "results": results,
    }
    return jsonify(response)


@app.route("/")
def index():
    results = {
        target: (res.decode("utf-8") if res else "")
        for target, res in zip(targets, redis.mget(targets))
    }

    # Construct the HTML response with responsive design
    html_response = """
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 20px auto;
            padding: 20px;
            border: 1px solid #e1e1e1;
            border-radius: 5px;
            background-color: #fafafa;
        }
        h1, h2, h3 {
            color: #333;
        }
        pre {
            background-color: #f7f7f7;
            padding: 10px;
            border-radius: 3px;
            overflow-x: scroll;
            white-space: pre-wrap; /* Allow content to wrap */
            word-wrap: break-word; /* Break long words if necessary */
        }
        ul {
            list-style-type: none;
            padding-left: 0;
        }
        li {
            padding: 5px 0;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            body {
                font-size: 0.9em; /* Reduce font size for smaller devices */
                padding: 15px;
            }
            h1, h2, h3 {
                margin-top: 15px;
            }
        }

    </style>
    <h1>MTR Probe</h1>

    <h2>Targets:</h2>
    <ul>
    """

    for target in targets:
        html_response += f"<li>{target}</li>"

    html_response += """
    </ul>

    <h2>Command:</h2>
    <pre>mtr -rwznc 10 [-6] &lt;target&gt;</pre>

    <h2>Results:</h2>
    """

    for target, result in results.items():
        html_response += f"""
        <h3>Target: {target}</h3>
        <pre>{result}</pre>
        """

    return html_response, 200


@app.route("/trigger-mtr")
def trigger_mtr():
    result = celery.send_task("mtr_probe.mtr_probe.run_mtr")
    return jsonify({"task_id": result.id}), 202


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
