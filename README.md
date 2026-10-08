# FastAPI Docker Boilerplate

> 🚧 **v2 in progress** on the `v2` branch: a full rewrite with an async domain-driven
> architecture, strict typing, 100% test coverage and a production-grade Docker setup.
> The original version is available at the [`v1.0.0`](https://github.com/diegoddie/fastapi-docker-boilerplate/tree/v1.0.0) tag.

## Quickstart

```bash
cp .env_template .env
docker compose up --build
```

- API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health/

## Tests

```bash
docker compose run --rm backend just test
```

## License

[MIT](LICENSE)
