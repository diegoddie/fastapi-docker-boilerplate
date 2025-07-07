FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ADD . /app

WORKDIR /app

RUN uv sync --locked

# Run the application.
CMD ["uv", "run", "uvicorn", "app.main:app", "--port", "8000", "--host", "0.0.0.0", "--reload"]