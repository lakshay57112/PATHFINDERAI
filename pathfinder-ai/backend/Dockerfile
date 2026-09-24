FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY data ./data
RUN useradd --create-home --uid 10001 pathfinder && mkdir -p /app/uploads && chown -R pathfinder /app
USER pathfinder
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD curl -fs http://localhost:8000/api/v1/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--workers", "2"]
