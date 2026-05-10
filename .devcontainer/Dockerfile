FROM mcr.microsoft.com/devcontainers/python:3.11

RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    jq \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY requirements.txt /tmp/
RUN uv pip install --system --no-cache -r /tmp/requirements.txt