#!/usr/bin/bash

echo "==> Running migrations"
uv run alembic upgrade head

echo "==> Starting Akabot"
uv run main.py
