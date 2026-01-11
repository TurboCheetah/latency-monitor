import pytest
from unittest.mock import MagicMock, patch
import sys


@pytest.fixture
def mock_app(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("TARGETS", "8.8.8.8")
    monkeypatch.setenv("INFLUXDB_V2_URL", "http://localhost:8086")
    monkeypatch.setenv("INFLUXDB_V2_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_V2_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")

    for mod in list(sys.modules.keys()):
        if mod.startswith("latency_monitor"):
            del sys.modules[mod]

    mock_redis_instance = MagicMock()
    mock_influx_instance = MagicMock()
    mock_write_api = MagicMock()
    mock_influx_instance.write_api.return_value = mock_write_api

    with patch("redis.Redis", return_value=mock_redis_instance):
        with patch("influxdb_client.InfluxDBClient.from_env_properties", return_value=mock_influx_instance):
            from latency_monitor.latency_monitor import app

            app.redis = mock_redis_instance
            app.influx = mock_influx_instance
            app.influx_write_api = mock_write_api
            app.targets = ["8.8.8.8"]

            yield app


class TestMtrFunction:
    def test_mtr_function_ipv4(self, mock_app):
        mtr_output = """HOST: server                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 8.8.8.8                   0.0%    10   10.5  11.2   9.8  15.3   1.5"""

        mock_result = MagicMock()
        mock_result.stdout = mtr_output

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            from latency_monitor.mtr import mtr

            result = mtr("8.8.8.8")

            mock_run.assert_called_once_with(
                ["mtr", "-rwznc", "10", "8.8.8.8"],
                capture_output=True,
                text=True
            )
            assert result["target"] == "8.8.8.8"
            assert result["stdout"] == mtr_output
            assert result["parsed_output"]["avg"] == 11.2

    def test_mtr_function_ipv6(self, mock_app):
        mtr_output = """HOST: server                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 2001:4860:4860::8888      0.0%    10   15.2  16.0  14.5  18.0   1.2"""

        mock_result = MagicMock()
        mock_result.stdout = mtr_output

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            from latency_monitor.mtr import mtr

            result = mtr("2001:4860:4860::8888")

            mock_run.assert_called_once_with(
                ["mtr", "-rwznc", "10", "-6", "2001:4860:4860::8888"],
                capture_output=True,
                text=True
            )
            assert result["target"] == "2001:4860:4860::8888"


class TestRunMtrTask:
    def test_run_mtr_task(self, mock_app):
        mtr_output = """HOST: server                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 8.8.8.8                   0.0%    10   10.5  11.2   9.8  15.3   1.5"""

        mock_result = MagicMock()
        mock_result.stdout = mtr_output

        with patch("subprocess.run", return_value=mock_result):
            from latency_monitor.mtr import run_mtr

            run_mtr()

            mock_app.redis.set.assert_called_once()
            call_args = mock_app.redis.set.call_args
            assert call_args[0][0] == "mtr_8.8.8.8"

            mock_app.influx_write_api.write.assert_called_once()


class TestDigFunction:
    def test_dig_function(self, mock_app):
        dig_output = """;; Query time: 42 msec
;; SERVER: 8.8.8.8#53(8.8.8.8) (UDP)"""

        mock_result = MagicMock()
        mock_result.stdout = dig_output

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            from latency_monitor.dig import dig

            result = dig("8.8.8.8")

            mock_run.assert_called_once_with(
                ["dig", "google.com", "@8.8.8.8"],
                capture_output=True,
                text=True
            )
            assert result["target"] == "8.8.8.8"
            assert result["stdout"] == dig_output
            assert result["parsed_output"] == 42


class TestRunDigTask:
    def test_run_dig_task(self, mock_app):
        dig_output = """;; Query time: 42 msec
;; SERVER: 8.8.8.8#53(8.8.8.8) (UDP)"""

        mock_result = MagicMock()
        mock_result.stdout = dig_output

        with patch("subprocess.run", return_value=mock_result):
            from latency_monitor.dig import run_dig

            run_dig()

            mock_app.redis.set.assert_called_once()
            call_args = mock_app.redis.set.call_args
            assert call_args[0][0] == "dig_8.8.8.8"

            mock_app.influx_write_api.write.assert_called_once()
