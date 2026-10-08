FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS base

LABEL project="fastapi-docker-boilerplate" service="backend" stage="base"

ARG DEBIAN_FRONTEND=noninteractive \
    GROUP_ID=1000 \
    USER_ID=1000 \
    USER=appuser

ENV APPUSER=$USER \
    INTERNAL_SERVICE_PORT=8000 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WORKDIR=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

ENV ALEMBIC_CONFIG="app/migrations/alembic.ini" \
    UV_PROJECT_ENVIRONMENT="/home/$APPUSER/.venv"

# Why: dependencies are synced at build time, so `uv run` must not re-sync (and
# recompile bytecode) on every command; rebuild the image after changing them.
ENV UV_NO_SYNC=1

ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"

WORKDIR $WORKDIR

RUN groupadd --gid "$GROUP_ID" "$APPUSER" \
    && useradd --uid "$USER_ID" --gid "$GROUP_ID" --create-home --skel /dev/null \
    "$APPUSER"

COPY --chown=$APPUSER ./pyproject.toml ./uv.lock ./

RUN apt-get update \
    && apt-get install --assume-yes --no-install-recommends \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && chown -R "$USER_ID":"$GROUP_ID" "$WORKDIR" \
    && su "$APPUSER" -c "uv sync --frozen --no-cache"

FROM base AS remote

LABEL project="fastapi-docker-boilerplate" service="backend" stage="remote"

RUN su "$APPUSER" -c "uv sync --frozen --no-cache --group remote"

COPY --chown=$APPUSER . .

USER $APPUSER

ENTRYPOINT ["./scripts/entrypoint.sh"]

CMD ["gunicorn", "app.main:app"]

FROM base AS test

LABEL project="fastapi-docker-boilerplate" service="backend" stage="test"

RUN su "$APPUSER" -c "uv sync --frozen --no-cache --group test"

COPY --chown=$APPUSER . .

USER $APPUSER

ENTRYPOINT ["./scripts/entrypoint.sh"]

CMD ["./scripts/test.sh"]

FROM base AS local

LABEL project="fastapi-docker-boilerplate" service="backend" stage="local"

RUN apt-get update \
    && apt-get install --assume-yes --no-install-recommends \
    curl \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN su "$APPUSER" -c "uv sync --frozen --no-cache --group local --group test"

COPY --chown=$APPUSER . .

USER $APPUSER

ENV UVICORN_HOST="0.0.0.0" \
    UVICORN_PORT="$INTERNAL_SERVICE_PORT"

HEALTHCHECK --start-period=5s --retries=5 \
    CMD curl --fail --head http://localhost:$INTERNAL_SERVICE_PORT/api/health/ \
    || exit 1

ENTRYPOINT ["./scripts/entrypoint.sh"]

CMD ["just", "runserver"]
