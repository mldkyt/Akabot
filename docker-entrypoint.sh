#!/usr/bin/bash

echo "==> Running migrations"
uv run alembic upgrade head

echo "==> Starting Nekona"
uv run main.py
