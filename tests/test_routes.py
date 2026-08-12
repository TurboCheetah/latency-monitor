import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("TARGETS", "8.8.8.8,1.1.1.1")
    monkeypatch.setenv("INFLUXDB_V2_URL", "http://localhost:8086")
    monkeypatch.setenv("INFLUXDB_V2_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_V2_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")

    mock_redis = MagicMock()
    mock_influx = MagicMock()
    mock_write_api = MagicMock()
    mock_celery = MagicMock()

    for module_name in list(sys.modules):
        if module_name.startswith("latency_monitor"):
            del sys.modules[module_name]

    with patch("redis.Redis", return_value=mock_redis), patch(
        "influxdb_client.InfluxDBClient.from_env_properties",
        return_value=mock_influx,
    ):
        mock_influx.write_api.return_value = mock_write_api
        from latency_monitor.latency_monitor import app

        monkeypatch.setattr(app, "redis", mock_redis)
        monkeypatch.setattr(app, "influx", mock_influx)
        monkeypatch.setattr(app, "influx_write_api", mock_write_api)
        monkeypatch.setattr(app, "celery", mock_celery)
        monkeypatch.setattr(app, "targets", ["8.8.8.8", "1.1.1.1"])

        with app.flask.test_client() as test_client:
            yield test_client, mock_redis, mock_celery

    for module_name in list(sys.modules):
        if module_name.startswith("latency_monitor"):
            del sys.modules[module_name]


class TestRoutes:
    def test_index_returns_html(self, client):
        test_client, mock_redis, _ = client
        mock_redis.mget.side_effect = [
            [b"mtr output", b"mtr output 2"],
            [b"dig output", b"dig output 2"],
        ]

        response = test_client.get("/")

        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.data

    def test_index_with_empty_redis(self, client):
        test_client, mock_redis, _ = client
        mock_redis.mget.side_effect = [[None, None], [None, None]]

        response = test_client.get("/")

        assert response.status_code == 200

    def test_json_endpoint(self, client):
        test_client, mock_redis, _ = client
        mock_redis.mget.side_effect = [
            [b"mtr output", b"mtr output 2"],
            [b"dig output", b"dig output 2"],
        ]

        response = test_client.get("/json")

        assert response.status_code == 200
        assert response.json["mtr"]["targets"] == ["8.8.8.8", "1.1.1.1"]
        assert response.json["mtr"]["results"] == {
            "8.8.8.8": "mtr output",
            "1.1.1.1": "mtr output 2",
        }
        assert response.json["dig"]["results"] == {
            "8.8.8.8": "dig output",
            "1.1.1.1": "dig output 2",
        }

    def test_json_endpoint_structure(self, client):
        test_client, mock_redis, _ = client
        mock_redis.mget.side_effect = [[b"mtr output", b"mtr output 2"], [None, None]]

        response = test_client.get("/json")

        assert response.status_code == 200
        assert set(response.json) == {"mtr", "dig"}
        assert response.json["mtr"]["command"] == "mtr -rwznc 10 [-6] <target>"
        assert response.json["dig"]["command"] == "dig google.com @<target>"
        assert response.json["dig"]["results"] == {
            "8.8.8.8": "",
            "1.1.1.1": "",
        }

    def test_trigger_mtr(self, client):
        test_client, _, mock_celery = client
        mock_celery.send_task.return_value.id = "test-task-id-123"

        response = test_client.get("/trigger-mtr")

        assert response.status_code == 202
        assert response.json == {"task_id": "test-task-id-123"}
        mock_celery.send_task.assert_called_once_with("latency_monitor.mtr.run_mtr")

    def test_trigger_dig(self, client):
        test_client, _, mock_celery = client
        mock_celery.send_task.return_value.id = "test-task-id-456"

        response = test_client.get("/trigger-dig")

        assert response.status_code == 202
        assert response.json == {"task_id": "test-task-id-456"}
        mock_celery.send_task.assert_called_once_with("latency_monitor.dig.run_dig")
