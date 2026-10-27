# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first (better layer caching)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copy source
COPY app ./app
COPY scripts ./scripts
COPY data ./data

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app"

EXPOSE 8501

CMD ["streamlit", "run", "app/ui/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
