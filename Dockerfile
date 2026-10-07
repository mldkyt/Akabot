FROM python:3.12-alpine

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apk apk add --no-cache gcc postgresql17 postgresql17-dev bash git

COPY pyproject.toml .
COPY uv.lock .

RUN --mount=type=cache,target=/root/.cache/pip pip3 install --upgrade uv
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen

COPY .git/ .git/.
COPY docker/ docker/.
COPY logger.py .
COPY main.py .
COPY webmain.py .
COPY database.py .
COPY cogs/ cogs/.
COPY utils/ utils/.
COPY web/ web/.
COPY alembic.ini .
COPY alembic/ alembic/.

RUN rm cogs/devel.py

COPY docker-entrypoint.sh .

RUN chmod +x docker/prepare.sh
RUN bash docker/prepare.sh
RUN chmod +x docker-entrypoint.sh

RUN rm -r .git
RUN apk --no-cache del git bash

STOPSIGNAL SIGKILL

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
