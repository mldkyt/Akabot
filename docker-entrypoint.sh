#!/usr/bin/bash

echo "==> Running migrations"
uv run alembic upgrade head

if [[ "$1" == "web" ]]; then
  echo "==> Starting Akabot (Web)"
  uv run gunicorn -w 4 -b 0.0.0.0 'webmain:app'
else
  echo "==> Starting Akabot"
  uv run main.py
fi
