FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md requirements.txt ./
COPY src ./src
COPY apps ./apps

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install -e .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/_stcore/health" || exit 1

CMD ["python", "-m", "streamlit", "run", "apps/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
