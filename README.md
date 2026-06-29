# Xuanwu

A self-hosted **authentication and authorization server** built with FastAPI,
MySQL 8, Redis, and Celery.

It provides token-based auth (RS256 JWT in httpOnly cookies with refresh-token
rotation), role-based access control, API-key (HMAC) access for machine clients,
TOTP two-factor auth, encrypted PII at rest with searchable blind indexes,
rate limiting, and an immutable audit trail.

> Named after **Xuanwu (玄武)**, the Black Tortoise — guardian of the North.

## Quickstart

The entire toolchain runs in containers; no local Python is required — only
Docker and Docker Compose. From a fresh clone:

```bash
cp .env.example .env                          # local configuration
make build                                    # build the image
make migrate                                  # create the database schema
make seed                                     # default RBAC permissions + levels
make superadmin EMAIL=admin@example.com       # bootstrap an admin (prompts for a password)
make stack                                    # start db, redis, api, worker, beat, mailhog, minio
```

Then log in:

```bash
curl -i -X POST http://localhost:8000/api/v2/xuanwu/identity/sessions \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<the password you set>"}'
```

The response sets the `access_token`, `refresh_token`, and `csrf_token`
cookies. Browse the API at <http://localhost:8000/docs>, sent email at the
MailHog UI (<http://localhost:8025>), and object storage at the MinIO console
(<http://localhost:9001>).

## Development

```bash
make check     # ruff (lint) + ruff format --check + mypy --strict + pytest
make security  # bandit + pip-audit
make lock      # recompile requirements.lock after editing pyproject.toml
```

`make help` lists every target. The JWT keypair is auto-generated on first use
in development; run `make keys` to mint one explicitly (required in production).
See `COMMANDS.md` for the full command reference and `CONTRIBUTING.md` for the
contribution workflow.

## Project layout

```
.
├── app/
│   ├── main.py            # application factory + /health
│   ├── console.py         # operator CLI (generate-keys, seed, create-superadmin)
│   ├── core/ db/ models/ schemas/ api/ services/
│   ├── workers/ queries/ emails/ integrations/
├── alembic/versions/      # database migrations
├── tests/                 # pytest suite
├── Dockerfile             # multi-stage image (non-root); runs api / worker / beat
├── docker-compose.yml     # db, redis, api, worker, beat, mailhog, minio
├── docker-compose.prod.yml# production overrides (no mounts, worker pool)
├── pyproject.toml         # dependencies + ruff/mypy/pytest/bandit config
├── requirements.lock      # fully-pinned dependencies
└── .env.example           # documented environment template
```

## Operations

The operator console bootstraps and maintains an install:

```bash
docker compose run --rm api python -m app.console generate-keys
docker compose run --rm api python -m app.console seed
docker compose run --rm api python -m app.console create-superadmin --email admin@example.com
```

Background processing is split one-process-per-container: the `worker` runs
Celery tasks (email, SMS, audit writes) and `beat` fires scheduled jobs (a daily
expired-token sweep today; domain schedules such as storage invoicing later).

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
