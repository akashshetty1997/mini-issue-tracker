# ---- base: runtime dependencies only ----
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml ./
RUN pip install .

# ---- dev: adds test/lint tooling; used by `make test` and CI ----
FROM base AS dev
RUN pip install ".[dev]"
COPY . .
CMD ["pytest"]

# ---- prod: the image the API runs from ----
FROM base AS prod
RUN useradd --create-home --uid 1000 appuser
COPY . .
RUN chmod +x entrypoint.sh
USER appuser
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
