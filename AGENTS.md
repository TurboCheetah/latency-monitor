# AGENTS.md

## Build & Run
- **Install deps**: `uv sync`
- **Run Flask dev**: `uv run python -m latency_monitor.latency_monitor`
- **Run Celery worker**: `uv run celery -A latency_monitor.latency_monitor:celery worker`
- **Run Celery beat**: `uv run celery -A latency_monitor.latency_monitor:celery beat`
- **Docker**: `docker compose up` (uses gunicorn on port 8080)

## Architecture
- Flask web app + Celery for scheduled tasks (mtr/dig every 5 min)
- Redis: task broker + result cache storage
- InfluxDB: time-series metrics storage (mtr latency, dig query times)
- Entry point: `latency_monitor/latency_monitor.py` (creates App singleton with flask, celery, redis, influx clients)
- Routes: `routes.py` — `/` (HTML), `/json`, `/trigger-mtr`, `/trigger-dig`
- Tasks: `mtr.py` (run_mtr), `dig.py` (run_dig) — Celery tasks that shell out to mtr/dig binaries
- Utilities: `utils.py` — regex parsers for mtr/dig output

## Code Style
- Python 3.14+, managed with uv
- Type hints on function signatures (use `-> ReturnType`)
- Imports: stdlib, then third-party, then local (relative imports within package)
- Use `environ` directly for config; no .env file parsing
- Errors: raise `ValueError` with descriptive messages for parse failures
