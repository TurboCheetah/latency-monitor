# latency-monitor

I got annoyed with CloudFlare having awful latency to me so I built this.

A network latency monitoring tool that runs periodic MTR and DNS dig tests against configurable targets, stores results in InfluxDB, and provides a web interface for viewing results.

## Features

- Scheduled MTR traces and DNS dig queries via Celery Beat (configurable interval)
- Time-series storage in InfluxDB for historical analysis
- Web dashboard with JSON API endpoints
- Docker deployment with Redis, InfluxDB, and Grafana support

## Quick Start

```bash
docker compose up
```

The web interface will be available at `http://localhost:8080`.

## Configuration

Environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `TARGETS` | Comma-separated list of IPs/hostnames to monitor | `1.1.1.1,8.8.8.8` |
| `SCHEDULE` | Cron expression for task schedule (5 fields) | `*/5 * * * *` |
| `REDIS_HOST` | Redis hostname | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `INFLUXDB_V2_URL` | InfluxDB URL | `http://influx:8086` |
| `INFLUXDB_V2_ORG` | InfluxDB organization | `latency-monitor` |
| `INFLUXDB_V2_TOKEN` | InfluxDB API token | `your-token` |
| `INFLUXDB_BUCKET` | InfluxDB bucket name | `latency-monitor` |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | HTML dashboard |
| `/json` | JSON results |
| `/trigger-mtr` | Manually trigger MTR task |
| `/trigger-dig` | Manually trigger dig task |

## Local Development

```bash
# Install dependencies
poetry install

# Run Flask dev server
poetry run python -m latency_monitor.latency_monitor

# Run Celery worker (separate terminal)
poetry run celery -A latency_monitor.latency_monitor:celery worker

# Run Celery beat scheduler (separate terminal)
poetry run celery -A latency_monitor.latency_monitor:celery beat

# Run tests
poetry run pytest
```

## Requirements

- Python 3.14+
- `mtr` and `dig` binaries installed on the system
- Redis
- InfluxDB 2.x

## License

GPLv3
