import pytest
from unittest.mock import MagicMock, patch
import json
import sys


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("TARGETS", "8.8.8.8,1.1.1.1")
    monkeypatch.setenv("INFLUXDB_V2_URL", "http://localhost:8086")
    monkeypatch.setenv("INFLUXDB_V2_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_V2_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")

    for mod in list(sys.modules.keys()):
        if mod.startswith("latency_monitor"):
            del sys.modules[mod]

    mock_redis_instance = MagicMock()
    mock_influx_instance = MagicMock()
    mock_celery = MagicMock()

    with patch("redis.Redis", return_value=mock_redis_instance):
        with patch("influxdb_client.InfluxDBClient.from_env_properties", return_value=mock_influx_instance):
            from latency_monitor.latency_monitor import app

            app.redis = mock_redis_instance
            app.celery = mock_celery

            with app.flask.test_client() as test_client:
                yield test_client, app, mock_redis_instance, mock_celery


class TestRoutes:
    def test_index_returns_html(self, client):
        test_client, app, mock_redis, _ = client
        mock_redis.mget.return_value = [b"mtr output", b"mtr output 2"]

        response = test_client.get("/")

        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data

    def test_index_with_empty_redis(self, client):
        test_client, app, mock_redis, _ = client
        mock_redis.mget.return_value = [None, None]

        response = test_client.get("/")

        assert response.status_code == 200

    def test_json_endpoint(self, client):
        test_client, app, mock_redis, _ = client
        mock_redis.mget.return_value = [b"mtr result 1", b"mtr result 2"]

        response = test_client.get("/json")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "mtr" in data
        assert "dig" in data
        assert "targets" in data["mtr"]
        assert "results" in data["mtr"]
        assert "command" in data["mtr"]

    def test_json_endpoint_structure(self, client):
        test_client, app, mock_redis, _ = client
        app.targets = ["8.8.8.8", "1.1.1.1"]
        mock_redis.mget.return_value = [b"output1", b"output2"]

        response = test_client.get("/json")

        data = json.loads(response.data)
        assert data["mtr"]["targets"] == ["8.8.8.8", "1.1.1.1"]
        assert data["dig"]["targets"] == ["8.8.8.8", "1.1.1.1"]
        assert data["mtr"]["command"] == "mtr -rwznc 10 [-6] <target>"
        assert data["dig"]["command"] == "dig google.com @<target>"

    def test_trigger_mtr(self, client):
        test_client, app, mock_redis, mock_celery = client
        mock_result = MagicMock()
        mock_result.id = "test-task-id-123"
        mock_celery.send_task.return_value = mock_result

        response = test_client.get("/trigger-mtr")

        assert response.status_code == 202
        data = json.loads(response.data)
        assert data["task_id"] == "test-task-id-123"
        mock_celery.send_task.assert_called_once_with("latency_monitor.mtr.run_mtr")

    def test_trigger_dig(self, client):
        test_client, app, mock_redis, mock_celery = client
        mock_result = MagicMock()
        mock_result.id = "test-task-id-456"
        mock_celery.send_task.return_value = mock_result

        response = test_client.get("/trigger-dig")

        assert response.status_code == 202
        data = json.loads(response.data)
        assert data["task_id"] == "test-task-id-456"
        mock_celery.send_task.assert_called_once_with("latency_monitor.dig.run_dig")
