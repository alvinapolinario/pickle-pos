# Pickle POS — Progress Tracker

> Last updated: **2026-08-18**  
> Current phase: **Phase 1 — Foundation (Complete)**  
> Next phase: **Phase 2 — Product & Inventory**

This document tracks all architectural decisions, implemented work, test status, and remaining tasks across the full project roadmap.

---

## Quick Status

| Metric | Status |
|--------|--------|
| Architecture design | Complete |
| Phase 1 — Foundation | **Complete** |
| Phase 2 — Product & Inventory | Not started |
| Phase 3 — POS Core | Not started |
| Phase 4 — Android POS | Not started |
| Phase 5 — Court Management | Not started |
| Phase 6 — Reporting | Not started |
| Phase 7 — Hardening | Not started |
| Automated tests | **11 / 11 passing** |
| Git commits | None yet (initial scaffold) |

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | Quick start, stack overview |
| [docs/ARCHITECTURE.md](./ARCHITECTURE.md) | Full system architecture (Parts 1–10) |
| [docs/DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | PostgreSQL entity design |
| [docs/PROGRESS.md](./PROGRESS.md) | This file — progress & checklist |
| [mobile/README.md](../mobile/README.md) | Flutter app placeholder (Phase 4) |

---

## Architecture Decisions (Locked In)

These decisions were made during the initial design session and should not change without explicit review:

- [x] **Modular monolith** — single repo, extractable modules later
- [x] **Monorepo** — `backend/core`, `django_admin`, `fastapi_api`, `workers`, `mobile`, `tests`
- [x] **Django** owns schema migrations and web admin
- [x] **FastAPI** handles mobile POS API only (thin controllers)
- [x] **Shared business logic** in `backend/core/services` and `backend/core/domain`
- [x] **Django ORM** as single persistence layer (FastAPI bootstraps Django)
- [x] **PostgreSQL** = source of truth; **SQLite** = offline mobile buffer only
- [x] **Server-authoritative totals** — mobile never trusted for money calculations
- [x] **Inventory ledger** — append-only movements, not mutable stock columns
- [x] **branch_id** on operational tables from day one
- [x] **NUMERIC(14,2)** for all monetary values
- [x] **UUID idempotency** for offline sale sync
- [x] **Redis** for cache, sessions, Celery broker, optional JWT refresh cache
- [x] **Docker + Nginx** deployment topology

---

## Phase Checklist Overview

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 0 | Architecture & Design | Done | 100% |
| 1 | Foundation | Done | 100% |
| 2 | Product & Inventory | Not started | 0% |
| 3 | POS Core | Not started | 0% |
| 4 | Android POS | Not started | 0% |
| 5 | Court Management | Not started | 0% |
| 6 | Reporting | Not started | 0% |
| 7 | Hardening & Production | Not started | 0% |

---

## Phase 0 — Architecture & Design

**Status: Complete**

### Completed

- [x] Stack evaluation (Django + FastAPI + Flutter + PostgreSQL + Redis + Celery + SQLite)
- [x] System architecture diagram (Nginx → Django / FastAPI → Core → PostgreSQL)
- [x] Monorepo folder structure defined
- [x] Shared business logic strategy (domain → services → repositories → ORM)
- [x] Database entity model designed (all major tables documented)
- [x] FastAPI endpoint map (v1) designed
- [x] Django app/module map defined
- [x] Flutter app architecture and screen list defined
- [x] Offline sync algorithm designed (push/pull, idempotency, conflicts)
- [x] Transaction integrity strategy (READ COMMITTED + row locks)
- [x] 7-phase development roadmap defined
- [x] Security requirements documented
- [x] Audit trail requirements documented
- [x] Multi-branch schema strategy documented
- [x] Testing strategy documented (unit, integration, concurrency)

### Artifacts

- [x] `docs/ARCHITECTURE.md`
- [x] `docs/DATABASE_SCHEMA.md`

---

## Phase 1 — Foundation

**Status: Complete**

### 1.1 Project Structure & DevOps

- [x] Monorepo root layout
- [x] `docker-compose.yml` — postgres, redis, django, fastapi, celery-worker, celery-beat, nginx
- [x] `backend/Dockerfile`
- [x] `nginx/conf.d/default.conf` — routes `/admin` → Django, `/api` → FastAPI
- [x] `.env.example` — all required environment variables
- [x] `.gitignore`
- [x] `backend/pyproject.toml` — dependencies, pytest, ruff, mypy config
- [x] `pytest.ini` — test runner config
- [x] `README.md` — quick start guide

### 1.2 Shared Core Package (`backend/core/`)

- [x] `core/config/settings.py` — Pydantic settings from environment
- [x] `core/domain/exceptions.py` — DomainError, AuthenticationError, ConflictError, etc.
- [x] `core/domain/auth/` — AuthenticatedUser, permission helpers
- [x] `core/services/auth_service.py` — shared login, JWT, refresh token logic
- [x] `core/django_setup.py` — Django bootstrap for FastAPI/Celery

### 1.3 Django Admin (`backend/django_admin/`)

- [x] Django project config (`config/settings/base|development|production|test.py`)
- [x] URL routing — admin, dashboard, health check
- [x] Dashboard template (placeholder metrics)
- [x] Redis session/cache integration
- [x] Celery config wired to Django settings

#### App: `accounts`

- [x] Custom `User` model (extends AbstractUser)
- [x] `Role` model with M2M permissions
- [x] `Permission` model (code-based RBAC)
- [x] `Device` model (POS terminal registration)
- [x] `RefreshToken` model (hashed, revocable)
- [x] Cashier PIN support (`pin_hash` field)
- [x] Django admin registration for all models
- [x] `seed_rbac` management command (Owner, Admin, Manager, Cashier, etc.)
- [x] Initial migration `0001_initial`

#### App: `branches`

- [x] `Branch` model (code, name, address, timezone, is_active)
- [x] Django admin registration
- [x] Initial migration `0001_initial`

#### App: `audit`

- [x] `AuditLog` model (immutable append-only)
- [x] `AuditContextMiddleware` — captures request context
- [x] `write_audit_log()` helper function
- [x] Read-only Django admin for audit logs
- [x] Initial migration `0001_initial`

### 1.4 FastAPI Mobile API (`backend/fastapi_api/`)

- [x] FastAPI app with CORS middleware
- [x] Django ORM bootstrap on startup
- [x] API v1 router structure
- [x] `POST /api/v1/auth/login` — password or PIN, optional device validation
- [x] `POST /api/v1/auth/refresh` — token rotation
- [x] `POST /api/v1/auth/logout` — revoke refresh token
- [x] `GET /api/v1/auth/me` — current user + roles + permissions
- [x] `GET /health` — service health check
- [x] Pydantic request/response schemas
- [x] JWT bearer authentication dependency
- [x] OpenAPI docs at `/api/docs`

### 1.5 Celery Workers (`backend/workers/`)

- [x] Celery app configured from Django settings
- [x] `health.ping` sample task
- [x] celery-worker and celery-beat services in docker-compose

### 1.6 Testing

- [x] `tests/conftest.py` — fixtures (branch, user, roles, api client)
- [x] `tests/test_auth_django.py` — 5 tests (password auth, PIN auth, roles, health)
- [x] `tests/test_auth_api.py` — 6 tests (login, refresh, me, logout, health)
- [x] Test settings using SQLite file DB
- [x] **All 11 tests passing**

### 1.7 Mobile (Placeholder)

- [x] `mobile/README.md` — planned Flutter structure documented

### Phase 1 — Not Done / Deferred

- [ ] Initial git commit
- [ ] `docker compose up` verified end-to-end in this environment
- [ ] Production `docker-compose.prod.yml`
- [ ] CI pipeline (GitHub Actions or similar)
- [ ] Rate limiting middleware on FastAPI
- [ ] Failed login lockout / brute-force protection
- [ ] Full Django web login UI (currently admin-only + placeholder dashboard)
- [ ] Device registration API endpoint (model exists, API not yet exposed)

---

## Phase 2 — Product & Inventory

**Status: Not started**

### 2.1 Product Management

- [ ] Django app: `products`
- [ ] `Category` model (branch-scoped, sort order, active/inactive)
- [ ] `Product` model (SKU, barcode, name, prices, unit, tax status, image)
- [ ] `ProductVariant` model (optional)
- [ ] `ProductModifier` / add-ons (optional)
- [ ] `BranchProductPrice` model (branch-specific price overrides)
- [ ] Django admin CRUD for categories and products
- [ ] Product list/search/filter in web admin
- [ ] FastAPI read endpoints: `GET /api/v1/products`, `/categories`
- [ ] Domain service: `core/services/pricing_service.py`
- [ ] Domain module: `core/domain/pricing/`
- [ ] Unit tests for product models and pricing service

### 2.2 Inventory Management

- [ ] Django app: `inventory`
- [ ] `InventoryMovement` model (append-only ledger)
- [ ] `InventoryBalance` model (materialized per branch + product)
- [ ] Movement types: stock_in, stock_out, adjustment, transfer, sale, return, wastage, expired
- [ ] `InventoryService` — atomic movement + balance update
- [ ] Oversell prevention (`SELECT FOR UPDATE` on balances)
- [ ] Stock adjustment workflow in web admin
- [ ] Stock count / beginning / ending inventory support
- [ ] Low stock detection (reorder level field on product)
- [ ] Unit tests for inventory service
- [ ] **Concurrency test:** two simultaneous deductions, one unit in stock → only one succeeds

### 2.3 Suppliers & Purchasing

- [ ] Django app: `purchasing`
- [ ] `Supplier` model
- [ ] `PurchaseOrder` / `PurchaseItem` models
- [ ] `PurchaseReceipt` model (receiving)
- [ ] Receiving → inventory movement (stock_in) workflow
- [ ] Purchase return support
- [ ] Django admin for suppliers, POs, receiving
- [ ] Unit tests for purchase receiving → inventory flow

---

## Phase 3 — POS Core (Web + API)

**Status: Not started**

### 3.1 Cashier Shift Management

- [ ] Django app: `shifts`
- [ ] `CashierShift` model (open/close, opening cash, expected vs actual)
- [ ] `CashTransaction` model (cash-in, cash-out)
- [ ] Shift open/close service with audit logging
- [ ] FastAPI: `POST /shifts/open`, `/close`, cash-in/out
- [ ] Shift closing report (over/short calculation)
- [ ] Tests for shift lifecycle

### 3.2 Sales Transactions

- [ ] Django app: `sales`
- [ ] `Sale`, `SaleItem`, `Payment` models
- [ ] `Refund`, `RefundItem` models
- [ ] `HeldOrder` model (hold/resume)
- [ ] Server-side total recalculation (never trust client)
- [ ] Transaction number / receipt number generation (unique per branch)
- [ ] Sale → inventory movement (stock deduction) in single DB transaction
- [ ] Void sale workflow (with authorization)
- [ ] Refund workflow (with authorization)
- [ ] Split payment support
- [ ] Payment methods: cash, GCash, Maya, bank transfer, configurable others
- [ ] FastAPI: `POST /sales`, void, refund, hold/resume
- [ ] Tests for sale workflow, void, refund, shift integration

### 3.3 Customer (Optional at POS)

- [ ] Django app: `customers`
- [ ] `Customer` model (name, mobile, email, notes)
- [ ] Optional customer on sale (walk-in allowed without registration)
- [ ] Customer purchase history view

### 3.4 Receipt

- [ ] Receipt data structure (server-side)
- [ ] Receipt template design (thermal printer format)
- [ ] Reprint support via API

---

## Phase 4 — Android POS (Flutter)

**Status: Not started**

### 4.1 Flutter Project Setup

- [ ] Initialize Flutter project in `mobile/pos_app/`
- [ ] App theme and routing (Riverpod or Bloc)
- [ ] Drift (SQLite) local database schema
- [ ] HTTP client with JWT auth interceptor

### 4.2 Core Screens

- [ ] Login (password / PIN)
- [ ] Open Shift
- [ ] POS Home (categories, products, search, barcode)
- [ ] Cart / Checkout
- [ ] Payment (multi-method, split, change calculation)
- [ ] Receipt (display + print)
- [ ] Transactions list
- [ ] Held Orders
- [ ] Refund / Return
- [ ] Shift Summary
- [ ] Sync Status indicator
- [ ] Settings

### 4.3 Offline & Sync

- [ ] Local SQLite stores: products, categories, prices, pending sales
- [ ] Offline sale creation with `client_sale_uuid`
- [ ] Sync engine (push queue + pull handler)
- [ ] Retry with exponential backoff
- [ ] Conflict display (price change, stock conflict)
- [ ] FastAPI: `POST /sync/push`, `GET /sync/pull`
- [ ] `SyncTransaction` model for idempotency tracking
- [ ] Integration tests for offline → sync → server commit

### 4.4 Printing

- [ ] Thermal printer abstraction (Bluetooth)
- [ ] Receipt print from local data
- [ ] Reprint from synced transaction

---

## Phase 5 — Court Management

**Status: Not started**

### 5.1 Courts & Pricing

- [ ] Django app: `courts`
- [ ] `Court` model (branch-scoped, status: available/occupied/maintenance)
- [ ] `CourtRate` model (hourly, day-of-week, membership tier)
- [ ] `CourtRateSchedule` (optional time-based pricing)
- [ ] Django admin for courts and rates

### 5.2 Booking

- [ ] `Booking` model with start/end timestamps
- [ ] PostgreSQL EXCLUDE constraint (no double booking)
- [ ] Booking workflow: customer → court → date → time → duration → price → payment
- [ ] Walk-in vs reservation support
- [ ] Cancellation and refund workflow
- [ ] Court payment integration
- [ ] Court occupancy / status view
- [ ] Maintenance blocking
- [ ] Transaction locking strategy for concurrent bookings
- [ ] Tests for double-booking prevention

### 5.3 Membership (Feature-flagged)

- [ ] Django app: `membership`
- [ ] `MembershipTier` model (Regular, Student, Premium, Club)
- [ ] Benefits: court discount, canteen discount, priority booking, loyalty points
- [ ] Feature flag to enable/disable module
- [ ] Apply membership pricing in court and canteen services

---

## Phase 6 — Reporting

**Status: Not started**

### 6.1 Dashboard

- [ ] Today's sales, canteen revenue, court revenue
- [ ] Open shifts, low stock, court occupancy, bookings today
- [ ] Expenses, net sales
- [ ] Payment method breakdown (cash, GCash, Maya, other)

### 6.2 Sales Reports

- [ ] Daily / weekly / monthly sales
- [ ] By product, category, cashier, payment method, hour
- [ ] Top-selling products

### 6.3 Inventory Reports

- [ ] Current stock, low stock, movement history
- [ ] Stock valuation, wastage, expired items
- [ ] Fast/slow moving products

### 6.4 Court Reports

- [ ] Court revenue, utilization, booking count
- [ ] Peak hours, revenue per court, cancellation rate

### 6.5 Financial Summary

- [ ] Gross sales, discounts, refunds, expenses
- [ ] Gross profit, estimated net income
- [ ] Export to CSV/PDF (Celery async jobs)

---

## Phase 7 — Hardening & Production

**Status: Not started**

### 7.1 Security

- [ ] Rate limiting on FastAPI (Redis-backed)
- [ ] Failed login lockout
- [ ] Discount / void / refund authorization flows
- [ ] HTTPS-only production config
- [ ] Secrets management (not in .env committed to repo)
- [ ] Security audit of auth and financial endpoints

### 7.2 Audit

- [ ] Wire `write_audit_log()` into all sensitive operations
- [ ] Audit viewer with filters in web admin
- [ ] Audit log retention policy

### 7.3 Performance & Reliability

- [ ] Database query optimization and index review
- [ ] Load testing (concurrent POS sales, booking conflicts)
- [ ] PostgreSQL backup strategy (automated daily)
- [ ] Log aggregation (structured logging)
- [ ] Health checks and uptime monitoring
- [ ] `docker-compose.prod.yml` with Gunicorn, proper worker counts

### 7.4 Testing (Full Suite)

- [ ] Unit tests — all domain services
- [ ] Integration tests — sale + inventory + shift flows
- [ ] API tests — all FastAPI endpoints
- [ ] Database transaction tests — rollback on failure
- [ ] Inventory concurrency tests
- [ ] Offline sync tests
- [ ] Booking conflict tests
- [ ] Permission / RBAC tests
- [ ] Shift closing reconciliation tests

---

## Files Created (Phase 0 + 1)

```
pickle-pos/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pytest.ini
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   └── PROGRESS.md                    ← this file
├── nginx/conf.d/default.conf
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── core/
│   │   ├── config/settings.py
│   │   ├── domain/auth/__init__.py
│   │   ├── domain/exceptions.py
│   │   ├── django_setup.py
│   │   └── services/auth_service.py
│   ├── django_admin/
│   │   ├── manage.py
│   │   ├── config/                      (settings, urls, wsgi, asgi)
│   │   ├── templates/dashboard.html
│   │   └── apps/
│   │       ├── accounts/                (models, admin, seed_rbac, migrations)
│   │       ├── branches/                (models, admin, migrations)
│   │       └── audit/                   (models, admin, middleware, migrations)
│   ├── fastapi_api/
│   │   ├── main.py
│   │   └── app/api/v1/                  (auth routes, schemas, dependencies)
│   └── workers/celery_app.py
├── mobile/README.md
└── tests/
    ├── conftest.py
    ├── test_auth_django.py
    └── test_auth_api.py
```

---

## Test Status

| Suite | Tests | Status |
|-------|-------|--------|
| `test_auth_django.py` | 5 | Pass |
| `test_auth_api.py` | 6 | Pass |
| **Total** | **11** | **All passing** |

Run tests:
```bash
backend\.venv\Scripts\pytest -v
```

---

## Known Gaps & Technical Debt

| Item | Priority | Phase |
|------|----------|-------|
| No git commits yet | Medium | Now |
| Docker end-to-end not verified locally | Medium | Now |
| No CI/CD pipeline | Medium | Phase 7 |
| No rate limiting on API | High | Phase 7 |
| No failed login lockout | High | Phase 7 |
| Dashboard shows placeholder data only | Low | Phase 6 |
| Device registration API not exposed | Medium | Phase 3 |
| Redis optional in tests (by design) | Info | — |
| Web login UI not built (admin panel only) | Medium | Phase 3 |
| No production docker-compose overlay | Medium | Phase 7 |

---

## Recommended Next Actions

1. **Create initial git commit** — preserve Phase 1 scaffold
2. **Verify Docker stack** — `docker compose up --build`, run migrations, seed RBAC, create superuser
3. **Begin Phase 2** — `products` app with categories and product models
4. **Implement inventory ledger** — movements + balances with concurrency tests
5. **Add pricing service** in `core/services/` before any sale logic in Phase 3

---

## Changelog

| Date | Milestone |
|------|-----------|
| 2026-08-18 | Architecture design completed (Parts 1–10) |
| 2026-08-18 | Phase 1 foundation scaffolded — auth, RBAC, branches, audit, Docker, tests |
| 2026-08-18 | Progress tracker created (this document) |
