FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache postgresql17 postgresql17-dev bash git

COPY pyproject.toml .

RUN pip3 install --upgrade uv
RUN uv sync

COPY .git/ .git/.
COPY docker/ docker/.
COPY logger.py .
COPY main.py .
COPY database.py .
COPY cogs/ cogs/.
COPY utils/ utils/.
COPY alembic.ini .
COPY alembic/ alembic/.

RUN rm cogs/devel.py

COPY docker-entrypoint.sh .

RUN chmod +x docker/prepare.sh
RUN bash docker/prepare.sh
RUN chmod +x docker-entrypoint.sh

RUN rm -r .git
RUN apk --no-cache del git bash

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
