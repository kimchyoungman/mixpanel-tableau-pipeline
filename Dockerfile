FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies for Tableau Hyper API
# See: https://help.tableau.com/current/api/hyper_api/en-us/reference/sqlapi.html#system-requirements
RUN apt-get update && apt-get install -y \
    libxml2 \
    libkrb5-3 \
    libicu-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE main.py columns.txt ./
COPY config ./config
COPY src ./src
RUN python -m pip install --upgrade pip \
    && python -m pip install ".[tableau,gcs]"

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p output logs \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["python", "main.py"]
