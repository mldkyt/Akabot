#!/usr/bin/bash


if [[ "$1" == "web" ]]; then
  echo "==> Waiting for migrations"
  sleep 5
  echo "==> Starting Akabot (Web)"
  uv run gunicorn -w 4 -b 0.0.0.0 'webmain:app'
else
  echo "==> Running migrations"
  uv run alembic upgrade head
  echo "==> Starting Akabot"
  uv run main.py
fi
