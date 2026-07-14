FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /workspace

COPY pyproject.toml README.md ./
COPY app ./app
COPY worker ./worker
RUN pip install --no-cache-dir .

FROM base AS test
COPY tests ./tests
RUN pip install --no-cache-dir ".[dev]" && ruff check . && pytest

FROM base AS runtime
RUN useradd --create-home appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
