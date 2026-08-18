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
| Django Admin | http://localhost:8000/admin/ |
| Dashboard | http://localhost:8000/ |
| FastAPI Docs | http://localhost:8001/api/docs |
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
python manage.py createsuperuser
python manage.py runserver

# Separate terminal — FastAPI
cd backend
uvicorn fastapi_api.main:app --reload --port 8001
```

## Running Tests

```bash
cd backend
pip install -e ".[dev]"
pytest ../tests -v
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full system architecture |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | PostgreSQL schema design |
| [docs/PROGRESS.md](docs/PROGRESS.md) | **Progress tracker & phase checklist** |

## Phase 1 Deliverables (Current)

- [x] Monorepo structure
- [x] Docker Compose (PostgreSQL, Redis, Django, FastAPI, Celery, Nginx)
- [x] Shared `core` package (config, domain exceptions, auth service)
- [x] Django apps: accounts, branches, audit
- [x] Custom User model with roles and permissions
- [x] Device registration model
- [x] JWT auth API (login, refresh, logout, me)
- [x] RBAC seed command
- [x] Foundation tests

## Next Steps (Phase 2)

See the full checklist in [docs/PROGRESS.md](docs/PROGRESS.md).

- Products and categories
- Inventory movement ledger
- Suppliers and purchasing

## License

Proprietary — All rights reserved.
