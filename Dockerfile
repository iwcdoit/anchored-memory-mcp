# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.12.17 AS uv
FROM python:3.12-slim-bookworm

COPY --from=uv /uv /usr/local/bin/uv
ARG SERVICE_GROUP
ENV UV_PROJECT_ENVIRONMENT=/opt/cmem-venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH=/opt/cmem-venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CMEM_DATA_DIR=/data

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --only-group "$SERVICE_GROUP"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 cmem && useradd --create-home --uid 10001 --gid cmem cmem \
    && install -d -o cmem -g cmem /data/notes /data/config /data/cache

COPY coding_memory/ ./coding_memory/
COPY examples/notes/ ./examples/notes/
COPY mkdocs.yml ./
USER cmem
