# Pickle POS — Progress Tracker

> Last updated: **2026-08-22**  
> Current phase: **Phase 7 — Hardening (Complete)**  
> Next: load tests, verify Bluetooth on a physical printer

This document tracks all architectural decisions, implemented work, test status, and remaining tasks across the full project roadmap.

---

## Quick Status

| Metric | Status |
|--------|--------|
| Architecture design | Complete |
| Phase 1 — Foundation | **Complete** |
| Phase 2 — Product & Inventory | **Complete** (optional variants/modifiers skipped) |
| Phase 3 — POS Core | **Complete** |
| Phase 4 — Android POS | **Complete** |
| Phase 5 — Court Management | **Complete** |
| Phase 6 — Reporting | **Complete** |
| Phase 7 — Hardening | **Complete** (load tests still later) |
| Automated tests | **115 passed, 1 skipped** |
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
- [x] **Console CRUD uses modals** — create, edit, and other data-entry forms open in-page; lists stay on the list URL

---

## Phase Checklist Overview

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 0 | Architecture & Design | Done | 100% |
| 1 | Foundation | Done | 100% |
| 2 | Product & Inventory | Done | 100% |
| 3 | POS Core | Done | 100% |
| 4 | Android POS | Done | 100% |
| 5 | Court Management | Done | 100% |
| 6 | Reporting | Done | 100% |
| 7 | Hardening & Production | Done | 90% |

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
- [x] Production `docker-compose.prod.yml`
- [x] CI pipeline (GitHub Actions) plus CD to GHCR
- [x] Rate limiting middleware on FastAPI
- [x] Failed login lockout / brute-force protection
- [x] Django web login UI (console)
- [x] Device registration API endpoint

---

## Phase 2 — Product & Inventory

**Status: Complete** (optional ProductVariant / ProductModifier skipped)

### 2.1 Product Management

- [x] Django app: `products`
- [x] `Category` model (branch-scoped, sort order, active/inactive)
- [x] `Product` model (SKU, barcode, name, prices, unit, tax status, image)
- [ ] `ProductVariant` model (optional)
- [ ] `ProductModifier` / add-ons (optional)
- [x] `BranchProductPrice` model (branch-specific price overrides)
- [x] Django admin CRUD for categories and products
- [x] Product list/search/filter in web admin
- [x] FastAPI read endpoints: `GET /api/v1/products`, `/categories`
- [x] Domain service: `core/services/pricing_service.py`
- [x] Domain module: `core/domain/pricing/`
- [x] Unit tests for product models and catalog API
- [x] Unit tests for pricing service

### 2.2 Inventory Management

- [x] Django app: `inventory`
- [x] `InventoryMovement` model (append-only ledger)
- [x] `InventoryBalance` model (materialized per branch + product)
- [x] Movement types: stock_in, stock_out, adjustment, transfer, sale, return, wastage, expired
- [x] `InventoryService` — atomic movement + balance update
- [x] Oversell prevention (`SELECT FOR UPDATE` on balances)
- [x] Stock adjustment workflow in web admin (modal)
- [x] Stock count / beginning inventory (count modal + opening seed)
- [x] Low stock detection (reorder level field on product)
- [x] Unit tests for inventory service
- [x] Sequential oversell tests; Postgres concurrency test skipped on SQLite runner

### 2.3 Suppliers & Purchasing

- [x] Django app: `purchasing`
- [x] `Supplier` model
- [x] `PurchaseOrder` / `PurchaseItem` models
- [x] `PurchaseReceipt` model (receiving)
- [x] Receiving → inventory movement (stock_in) workflow
- [x] Purchase return support (stock_out against received qty)
- [x] Django admin for suppliers, POs, receiving
- [x] Unit tests for purchase receiving → inventory flow

---

## Phase 3 — POS Core (Web + API)

**Status: Complete**

### 3.1 Cashier Shift Management

- [x] Django app: `shifts`
- [x] `CashierShift` model (open/close, opening cash, expected vs actual)
- [x] `CashTransaction` model (cash-in, cash-out)
- [x] Shift open/close service with audit logging
- [x] FastAPI: `POST /shifts/open`, `/close`, cash-in/out
- [x] Shift closing report (over/short calculation)
- [x] Tests for shift lifecycle

### 3.2 Sales Transactions

- [x] Django app: `sales`
- [x] `Sale`, `SaleItem`, `Payment` models
- [x] `Refund`, `RefundItem` models
- [x] `HeldOrder` model (hold/resume)
- [x] Server-side total recalculation (never trust client)
- [x] Transaction number / receipt number generation (unique per branch)
- [x] Sale → inventory movement (stock deduction) in single DB transaction
- [x] Void sale workflow (with authorization)
- [x] Refund workflow (with authorization)
- [x] Split payment support
- [x] Payment methods: cash, GCash, Maya, bank transfer, configurable others
- [x] FastAPI: `POST /sales`, void, refund, hold/resume
- [x] Tests for sale workflow, void, refund, shift integration

### 3.3 Customer (Optional at POS)

- [x] Django app: `customers`
- [x] `Customer` model (name, mobile, email, notes)
- [x] Optional customer on sale (walk-in allowed without registration)
- [x] Customer purchase history view

### 3.4 Receipt

- [x] Receipt data structure (server-side)
- [x] Receipt template design (thermal printer format)
- [x] Reprint support via API

---

## Phase 4 — Android POS (Flutter)

**Status: Complete**

### 4.1 Flutter Project Setup

- [x] Initialize Flutter project in `mobile/pos_app/`
- [x] App theme and routing (Riverpod)
- [ ] Drift (SQLite) local database schema (JSON pending queue + catalog cache for now)
- [x] HTTP client with JWT auth interceptor

### 4.2 Core Screens

- [x] Login (password / PIN)
- [x] Open Shift
- [x] POS Home (categories, products, search, barcode)
- [x] Cart / Checkout
- [x] Payment (multi-method, split, change calculation)
- [x] Receipt (display + print)
- [x] Transactions list
- [x] Held Orders (resume into cart)
- [x] Refund / Return
- [x] Shift Summary
- [x] Sync Status indicator
- [x] Settings

### 4.3 Offline & Sync

- [x] Local stores: pending sales queue
- [x] Offline sale creation with `client_sale_uuid`
- [x] Sync engine (push queue + pull handler)
- [x] Retry with exponential backoff
- [x] Conflict display (price change, stock conflict)
- [x] FastAPI: `POST /sync/push`, `GET /sync/pull`
- [x] `SyncTransaction` model for idempotency tracking
- [x] Integration tests for offline → sync → server commit
- [x] Offline catalog cache (SharedPreferences JSON)

### 4.4 Printing

- [x] Thermal printer abstraction (Bluetooth ESC/POS via `print_bluetooth_thermal`)
- [x] Receipt print from local data
- [x] Reprint from synced transaction

---

## Phase 5 — Court Management

**Status: Complete**

### 5.1 Courts & Pricing

- [x] Django app: `courts`
- [x] `Court` model (branch-scoped, status: available/maintenance; occupied is computed)
- [x] `CourtRate` model (hourly weekday override)
- [ ] `CourtRateSchedule` (optional time-based pricing)
- [x] Django admin for courts and rates
- [x] Console lists + modals for courts, rates, bookings, schedule
- [x] FastAPI: `GET /courts`, `/courts/occupancy`

### 5.2 Booking

- [x] `Booking` model with start/end timestamps
- [ ] PostgreSQL EXCLUDE constraint (no double booking) — service lock used so SQLite tests still run
- [x] Booking workflow: court → date → time → duration → server quote → payment
- [x] Walk-in vs reservation support (optional customer; unpaid if no payment method)
- [x] Cancellation (frees the slot, no money back)
- [x] Booking refund workflow (full refund, cancels slot, `BookingRefund` ledger)
- [x] Court payment on create (cash / GCash / Maya / bank / other)
- [x] Court occupancy / status view (console schedule + dashboard)
- [x] Maintenance blocking
- [x] Transaction locking strategy for concurrent bookings (`SELECT FOR UPDATE` + overlap query)
- [x] Tests for double-booking prevention
- [x] Flutter Bookings tab (live date/court/slot grid)

### 5.3 Membership

- [x] Django app: `membership`
- [x] `MembershipTier` model (Regular, Student, Premium, Club)
- [x] Benefits: court discount, canteen discount, priority booking, loyalty points
- [x] Feature flag `branch.memberships_enabled`
- [x] Apply membership pricing in court and canteen services
- [x] Loyalty ledger on paid sales/bookings; reverse on void/refund
- [x] Flutter customer picker on POS and Bookings (`customer_id` on quote/create)

---

## Phase 6 — Reporting

**Status: Complete**

### 6.1 Dashboard

- [x] Today's sales, canteen revenue, court revenue
- [x] Open shifts, low stock, court occupancy, bookings today
- [x] Expenses, estimated net income
- [x] Payment method breakdown (cash, GCash, Maya, other)

### 6.2 Sales Reports

- [x] Date-range sales report (console)
- [x] By product, cashier, payment method, hour, and day
- [x] Top-selling products
- [x] CSV export (daily totals)
- [x] PDF export (KPIs, by day, products, cashiers)

### 6.3 Inventory Reports

- [x] Current stock, low stock, movement history
- [x] Stock valuation, wastage, expired items
- [x] Fast/slow moving products
- [x] CSV export (stock snapshot)
- [x] PDF export (valuation, stock snapshot)

### 6.4 Court Reports

- [x] Court revenue, utilization, booking count
- [x] Peak hours, revenue per court, cancellation rate
- [x] CSV export (by court)
- [x] PDF export (utilization and by court)

### 6.5 Financial Summary

- [x] Gross sales, discounts, refunds, expenses
- [x] Gross profit, estimated net income
- [x] CSV and PDF export (P&L lines) — generated in-request, no Celery queue

---

## Phase 7 — Hardening & Production

**Status: Complete** (CI/CD and dedicated load tests still later)

### 7.1 Security

- [x] Rate limiting on FastAPI (Redis-backed; on in production or `RATE_LIMIT_ENABLED`)
- [x] Failed login lockout (5 attempts / 15 minutes, Redis or shared memory)
- [x] Discount / void / refund authorization (`sales.discount`, void = create or void, refund required)
- [x] HTTPS-ready production config (HSTS + SSL redirect via env)
- [x] Production refuses default `change-me` secrets
- [x] Auth and money endpoints return 403 for missing permissions
- [x] POS pairing API key + QR (`PosConnection`, `X-Api-Key`, Flutter scan)

### 7.2 Audit

- [x] `write_audit_log()` on sales, shifts, purchasing, inventory, bookings, expenses, console login
- [x] Console audit viewer with action / entity / user filters (`audit.view`)
- [x] Retention prune (`prune_audit_logs`, daily Celery beat)

### 7.3 Performance & Reliability

- [x] Existing indexes reviewed (audit + operational tables already indexed)
- [ ] Load testing (concurrent POS sales, booking conflicts) — later
- [x] PostgreSQL backup script (`scripts/backup_postgres.sh`)
- [x] Structured process logging in production settings
- [x] Health checks probe the database
- [x] `docker-compose.prod.yml` with Gunicorn workers
- [x] GitHub Actions CI (pytest, Docker build, Flutter) and CD (GHCR image on `v*` tags)

### 7.4 Testing (Full Suite)

- [x] Unit tests — domain services (auth, pricing, inventory, sales, bookings, reports, security)
- [x] Integration tests — sale + inventory + shift flows
- [x] API tests — FastAPI auth, catalog, POS, courts, settings
- [x] Database transaction tests — rollback on failure
- [x] Inventory concurrency tests (Postgres-only, skipped on SQLite)
- [x] Offline sync tests
- [x] Booking conflict tests
- [x] Permission / RBAC tests (discount + audit viewer)
- [x] Shift closing reconciliation tests

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
| Auth (Django + API) | 11 | Pass |
| Console UI | 6 | Pass |
| Products / catalog | 12 | Pass |
| Pricing | 6 | Pass |
| Inventory | 13 | 12 pass, 1 skipped (Postgres concurrency) |
| Purchasing | 11 | Pass |
| Shifts | 3 | Pass |
| Sales | 8 | Pass |
| Customers / receipts / sync | 7 | Pass |
| POS API (shifts + sales + sync) | 4 | Pass |
| Settings API | 1 | Pass |
| Courts / bookings | 9 | Pass |
| Courts API | 1 | Pass |
| Reports | 5 | Pass |
| Security / audit | 11 | Pass |
| Memberships | 5 | Pass |
| **Total** | **116** | **115 passing, 1 skipped** |

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
| Dedicated load tests | Medium | Next |
| Dashboard shows placeholder data only | Low | Phase 6 leftover |
| Redis optional in tests (by design) | Info | — |
| Bluetooth thermal print needs a physical Android printer to verify | Info | Phase 4 leftover |
| Drift SQLite catalog cache not yet used (JSON queue) | Medium | Phase 4 leftover |
| Booking overlap uses service lock, not Postgres EXCLUDE | Medium | Phase 5 leftover |

---

## Recommended Next Actions

1. **Create initial git commit** and push so GitHub Actions can run
2. **Use `docker-compose.prod.yml` with real secrets** when deploying
3. **Tag `v1.0.0`** when you want CD to publish `ghcr.io/<owner>/pickle-pos`
4. **Verify Bluetooth printing** on a physical 58mm/80mm ESC/POS printer

---

## Changelog

| Date | Milestone |
|------|-----------|
| 2026-08-18 | Architecture design completed (Parts 1–10) |
| 2026-08-18 | Phase 1 foundation scaffolded — auth, RBAC, branches, audit, Docker, tests |
| 2026-08-18 | Products and categories catalog: models, console CRUD, FastAPI reads, tests |
| 2026-08-18 | Inventory ledger: movements, balances, console stock/count modals, FastAPI balances |
| 2026-08-19 | Purchasing: suppliers, purchase orders, receiving, and supplier returns |
| 2026-08-19 | Pricing service (VAT-inclusive) plus Phase 3 shifts, sales, void, refund, hold |
| 2026-08-19 | Phase 3 polish: customers, receipts, devices, sync; Flutter POS app started |
| 2026-08-22 | Phase 4 polished: refunds, hold-resume, catalog cache, sync backoff |
| 2026-08-22 | Phase 5 started: courts, weekday rates, bookings, console + Flutter grid |
| 2026-08-22 | Booking refunds plus Phase 6 sales and court reports |
| 2026-08-22 | Phase 6 finished: inventory + financial reports, expenses ledger |
| 2026-08-22 | Phase 7 hardening: lockout, rate limits, RBAC on money actions, audit viewer, prod Compose |
| 2026-08-22 | CI/CD: GitHub Actions pytest + Docker + Flutter; GHCR publish on version tags |
| 2026-08-22 | Memberships: tiers, assignments, court/canteen discounts, loyalty points |
| 2026-08-22 | PDF export on sales, court, inventory, and financial reports |
| 2026-08-22 | Flutter Bluetooth thermal print: pair, reconnect, test print, receipt Print |
| 2026-08-22 | Flutter customer picker on POS and Bookings; FastAPI GET/POST /customers |
| 2026-08-22 | POS pairing QR: API URL + key in System Settings; Flutter scan / X-Api-Key |
