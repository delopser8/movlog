FROM mcr.microsoft.com/devcontainers/python:3.11

# Evitar diálogos interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    jq \
    curl \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Actualizar pip
RUN pip install --upgrade pip

# Copiar requirements e instalar (opcional, acelera el arranque)
# COPY requirements.txt /tmp/pip-tmp/
# RUN pip install --disable-pip-version-check -r /tmp/pip-tmp/requirements.txt \
#    && rm -rf /tmp/pip-tmp