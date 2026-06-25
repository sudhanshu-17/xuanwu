# Xuanwu

A self-hosted **authentication and authorization server** built with FastAPI,
MySQL 8, Redis, and Celery.

It provides token-based auth (RS256 JWT in httpOnly cookies with refresh-token
rotation), role-based access control, API-key (HMAC) access for machine clients,
TOTP two-factor auth, encrypted PII at rest with searchable blind indexes,
rate limiting, and an immutable audit trail.

> Named after **Xuanwu (玄武)**, the Black Tortoise — guardian of the North.

## Development

The entire toolchain runs in containers; no local Python is required — only
Docker and Docker Compose.

```bash
make lock      # compile requirements.lock (run once / when dependencies change)
make build     # build the api image
make up        # start the API → http://localhost:8000/health
make check     # ruff + format + mypy + pytest
make security  # bandit + pip-audit
```

`make help` lists every target. Each wraps `docker compose run --rm --no-deps api <cmd>`.

## Project layout

```
.
├── app/
│   ├── main.py            # application factory + /health
│   ├── core/ db/ models/ schemas/ api/ services/
│   ├── workers/ queries/ emails/ integrations/
├── alembic/versions/      # database migrations
├── tests/                 # pytest suite
├── Dockerfile             # development image (non-root)
├── docker-compose.yml     # mysql + redis + api
├── pyproject.toml         # dependencies + ruff/mypy/pytest/bandit config
├── requirements.lock      # fully-pinned dependencies
└── .env.example           # documented environment template
```

## API

Application endpoints are versioned and namespaced under **`/api/v2/xuanwu/`**:

| Group     | Path prefix                | Auth                                          |
|-----------|----------------------------|-----------------------------------------------|
| identity  | `/api/v2/xuanwu/identity/` | public                                        |
| resource  | `/api/v2/xuanwu/resource/` | access cookie + CSRF, or API-key HMAC         |
| admin     | `/api/v2/xuanwu/admin/`    | access cookie + role check                    |
| public    | `/api/v2/xuanwu/public/`   | public                                        |

`/health` is served at the root as a liveness probe for load balancers.

## License

MIT
