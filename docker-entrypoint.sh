#!/usr/bin/bash

echo "==> Running migrations"
uv run alembic upgrade head

if [[ "$1" == "web" ]]; then
  echo "==> Starting Akabot (Web)"
  uv run web/main.py
fi

echo "==> Starting Akabot"
uv run main.py
