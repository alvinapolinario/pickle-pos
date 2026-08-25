# Pickle POS

Production-ready POS and management system for a **pickleball court and canteen**.

## Stack

| Layer | Technology |
|-------|------------|
| Web Admin | Django + Templates |
| Mobile API | FastAPI |
| Android POS | Flutter (Phase 4) |
| Database | PostgreSQL |
| Cache / Broker | Redis |
| Background Jobs | Celery |
| Offline Store | SQLite (mobile only) |
| Proxy | Nginx |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design.

```
Web Admin → Django ─┐
                    ├→ Core Services → PostgreSQL
Flutter POS → FastAPI ┘
              ↓
            SQLite (offline)
```

## Quick Start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Services:

| Service | URL |
|---------|-----|
| Django Admin | http://localhost:7100/ |
| Built-in Django Admin | http://localhost:7100/django-admin/ |
| FastAPI Docs | http://localhost:7101/api/docs |
| Nginx (combined) | http://localhost/ |

## Local Development (without Docker)

```bash
# From repo root
cp .env.example .env

# Install backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"

# Start PostgreSQL and Redis locally, then:
cd django_admin
python manage.py migrate
python manage.py seed_rbac
python manage.py seed_courts
python manage.py seed_expenses
python manage.py seed_memberships
python manage.py createsuperuser
python manage.py runserver 7100

# Separate terminal — FastAPI
cd backend
uvicorn fastapi_api.main:app --reload --port 7101
```

## Running Tests

```bash
cd backend
pip install -e ".[dev]"
pytest ../tests -v
```

## CI/CD

Pipelines live in `.github/workflows/`. They run on GitHub after you push; commit and push only trigger them.

```
push / pull request          tag v1.0.0 or "Run workflow"
        │                              │
        ▼                              ▼
   CI pipeline                    CD pipeline
 backend tests                  runs CI first
 Docker build                   publish image to GHCR
 Flutter analyze/test           optional SSH deploy
        │
        ▼
   "CI passed" gate
```

**CI** (`.github/workflows/ci.yml`) — every push and pull request.

**CD** (`.github/workflows/cd.yml`) — version tags (`v1.0.0`) or **Actions → CD → Run workflow**. It re-runs CI, then publishes `ghcr.io/<owner>/pickle-pos`. If you set deploy secrets, it SSHs to the server, pulls that image, and restarts Compose.

Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

On the server without SSH deploy:

```bash
export PICKLE_POS_IMAGE=ghcr.io/<owner>/pickle-pos:1.0.0
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Optional deploy secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`, `DEPLOY_PATH`, and a `GHCR_TOKEN` (classic PAT with `read:packages`) so the server can pull the private image. Create a GitHub Environment named `production` if you want an approval step before deploy.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full system architecture |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | PostgreSQL schema design |
| [docs/PROGRESS.md](docs/PROGRESS.md) | **Progress tracker & phase checklist** |

## Phase 4 — Android POS (Flutter)

The cashier app lives in `mobile/pos_app/`.

```bash
cd mobile/pos_app
flutter pub get
flutter run
```

Use `http://10.0.2.2:7101` from the Android emulator (host FastAPI).

## Production

Use real secrets in `.env` (never the `change-me` placeholders). Then:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

That overlay runs Gunicorn (Django + FastAPI workers), enables login lockout and API rate limits, and refuses default secrets. Daily database backups:

```bash
./scripts/backup_postgres.sh
```

Behind TLS, set `SECURE_SSL_REDIRECT=true` and `SECURE_HSTS_SECONDS=31536000`.

## Phase 1–3 Deliverables

- [x] Monorepo structure
- [x] Docker Compose (PostgreSQL, Redis, Django, FastAPI, Celery, Nginx)
- [x] Shared `core` package (config, domain exceptions, auth service)
- [x] Django apps: accounts, branches, audit
- [x] Custom User model with roles and permissions
- [x] Device registration model
- [x] JWT auth API (login, refresh, logout, me)
- [x] RBAC seed command
- [x] Foundation tests
- [x] Products, categories, and branch price overrides
- [x] Inventory movement ledger
- [x] Suppliers and purchasing
- [x] Server-side pricing (VAT-inclusive)
- [x] Cashier shifts and POS sales (stock deduction, void, refund, hold)
- [x] Optional customers, receipts, device API, and offline sync
- [x] Flutter POS app (`mobile/pos_app`)


## License

Proprietary — All rights reserved.
