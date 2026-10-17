#!/bin/sh
set -e

exec uvicorn app.main:create_app --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WEB_CONCURRENCY:-2}"
