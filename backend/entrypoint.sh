#!/bin/sh
set -e

# Migrations run here for single-container simplicity. With several replicas this should
# become a separate one-off job (see ENGINEERING.md).
alembic upgrade head
python -m app.scripts.seed

exec uvicorn app.main:create_app --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WEB_CONCURRENCY:-2}"
