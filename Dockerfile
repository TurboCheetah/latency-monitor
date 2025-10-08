FROM python:3.14-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk --no-cache add mtr bind-tools && \
  pip install --no-cache-dir poetry==1.5.1

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --only main

COPY . .

EXPOSE 8080

CMD ["gunicorn", "latency_monitor.latency_monitor:flask", "-w", "4", "-b", "0.0.0.0:8080"]
