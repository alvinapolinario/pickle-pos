# Pickle POS — System Architecture

> Production architecture for a pickleball court + canteen POS and management platform.

---

## Part 1 — Architecture Review

### Stack Evaluation: Django + FastAPI + Flutter + PostgreSQL + Redis + Celery + SQLite

**Verdict: Correct architecture for this project**, with one critical rule: **shared domain layer + single PostgreSQL schema**, not duplicated business logic.

| Component | Role | Fit |
|-----------|------|-----|
| Django | Web admin, ORM, migrations, RBAC UI, reports | Excellent |
| FastAPI | Mobile POS API, sync, async I/O | Excellent |
| Flutter | Android POS, offline SQLite | Excellent |
| PostgreSQL | Source of truth, ACID, constraints | Required |
| Redis | Cache, sessions, rate limits, Celery broker | Excellent |
| Celery | Reports, sync reconciliation, notifications | Excellent |
| SQLite | Offline POS cache only | Correct scope |

### Advantages

1. **Django for admin** — mature auth, admin, forms, templates, migrations, RBAC; fast delivery for back-office.
2. **FastAPI for mobile** — OpenAPI docs, Pydantic validation, high throughput, JWT-friendly.
3. **Shared PostgreSQL** — one source of truth; no sync between separate DBs except mobile offline buffer.
4. **Modular monolith** — small team can ship; modules extractable later (sync service, reporting service).
5. **Offline-first Flutter** — SQLite + idempotent sync is industry-standard for POS.

### Disadvantages & Risks

| Risk | Mitigation |
|------|------------|
| Duplicated business rules in Django vs FastAPI | Shared `core/domain` + `core/services`; both apps call same services |
| FastAPI + Django ORM coupling | FastAPI bootstraps Django once; repositories wrap ORM |
| Offline sync conflicts | Server-authoritative pricing/stock; idempotency keys; conflict queue |
| Overselling under concurrency | Ledger + row locks + `SELECT FOR UPDATE` on stock snapshots |
| Team maintains two web frameworks | Strict module boundaries; FastAPI thin controllers only |
| Clock skew on devices | Server timestamps win; NTP advisory on devices |

### Improvements Over Naive Design

```
                    ┌─────────────────────────────────────┐
                    │         Shared Core Package          │
                    │  domain · services · repositories   │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
          Django Admin         FastAPI API         Celery Workers
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   ▼
                              PostgreSQL
                                   ▲
                              Redis (cache/broker)
                                   ▲
                              Flutter POS → SQLite (offline)
```

- **Nginx** terminates TLS, routes `/admin` → Django, `/api` → FastAPI.
- **Device registry** + JWT scopes for POS terminals.
- **Event outbox** table for reliable async side effects (optional Phase 7).
- **Branch-scoped** data from day one.

### Why Django for Web Admin

- Built-in user/group/permission model (extended for roles).
- Django Admin accelerates CRUD for products, inventory, courts.
- Template stack allows incremental React migration (HTMX or API-first pages later).
- Migration system owns schema; FastAPI reads same schema.

### Why FastAPI for Mobile API

- POS needs fast JSON APIs, sync batches, and OpenAPI for Flutter code gen.
- Stateless JWT fits mobile; refresh tokens in Redis.
- Async endpoints for sync pull/push without blocking workers.
- Keeps mobile traffic isolated from admin session load.

### Shared Business Logic Strategy

```
Request → Controller (Django view / FastAPI route)
       → Service (core/services/*.py)
       → Domain rules (core/domain/*.py)  ← pure Python, Decimal, no ORM
       → Repository (core/repositories/*.py)
       → Django ORM models
```

**Do NOT** share Django ORM models directly in domain logic. **Do** use Django ORM as the single persistence layer via repositories.

Pricing, tax, discount, inventory, payments, bookings, shifts — all live in `core/services`.

---

## Part 2 — System Architecture

```
                         Internet (HTTPS)
                               │
                          ┌────▼────┐
                          │  Nginx  │
                          │  TLS    │
                          └──┬──┬───┘
                    /admin   │  │   /api/v1
                             │  │
              ┌──────────────▼  └──────────────┐
              │                               │
        ┌─────▼─────┐                 ┌───────▼───────┐
        │  Django   │                 │   FastAPI     │
        │  Gunicorn │                 │   Uvicorn     │
        │  :7100    │                 │   :7101       │
        └─────┬─────┘                 └───────┬───────┘
              │         ┌──────────┐          │
              └────────►│   Core   │◄─────────┘
                        │ Services │
                        └────┬─────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌───────────┐      ┌───────────┐      ┌─────────────┐
   │ PostgreSQL│      │   Redis   │      │   Celery    │
   │  Primary  │      │ cache·jwt │      │ worker·beat │
   │    DB     │      │ rate·broker      └─────────────┘
   └─────▲─────┘      └───────────┘
         │
         │  sync push/pull (when online)
         │
   ┌─────▼─────┐
   │  Flutter  │
   │ Android   │
   │    POS    │
   └─────┬─────┘
         ▼
   ┌───────────┐
   │  SQLite   │  ← offline buffer only
   └───────────┘
```

---

## Part 3 — Monorepo Structure

```
pickle-pos/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── README.md
├── docs/
│   └── ARCHITECTURE.md
├── nginx/
│   └── conf.d/default.conf
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── core/                      # Shared domain + services
│   │   ├── config/
│   │   ├── domain/
│   │   │   ├── sales/
│   │   │   ├── inventory/
│   │   │   ├── pricing/
│   │   │   ├── payments/
│   │   │   ├── booking/
│   │   │   └── membership/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── django_setup.py
│   ├── django_admin/
│   │   ├── manage.py
│   │   ├── config/
│   │   └── apps/
│   │       ├── accounts/          # Users, roles, devices
│   │       ├── branches/
│   │       ├── products/
│   │       ├── inventory/
│   │       ├── sales/
│   │       ├── courts/
│   │       ├── customers/
│   │       ├── purchasing/
│   │       ├── expenses/
│   │       ├── reports/
│   │       └── audit/
│   ├── fastapi_api/
│   │   ├── main.py
│   │   └── app/
│   │       ├── api/v1/
│   │       ├── schemas/
│   │       ├── dependencies/
│   │       └── middleware/
│   └── workers/
│       └── celery_app.py
├── mobile/
│   └── pos_app/                   # Flutter project
│       ├── lib/
│       │   ├── core/
│       │   ├── features/
│       │   ├── sync/
│       │   └── data/
│       └── test/
└── tests/
    ├── unit/
    ├── integration/
    └── concurrency/
```

**Monorepo** recommended: shared `core`, unified CI, atomic schema migrations, single version tag.

---

## Part 4 — Database Model (Summary)

See `django_admin/apps/*/models.py` migrations. Key entities:

### Identity & Access
- **users** — custom user; links to branch assignments
- **roles**, **permissions**, **role_permissions**, **user_roles**
- **devices** — registered POS terminals
- **refresh_tokens** — hashed, Redis-backed optional index

### Organization
- **branches** — multi-location ready
- **branch_settings** — tax, receipt header, payment config

### Catalog
- **categories**, **products**, **product_variants**, **product_modifiers**
- **branch_product_prices** — branch-specific overrides

### Inventory (Ledger-Based)
- **inventory_movements** — append-only ledger
- **inventory_balances** — materialized `(branch_id, product_id) → qty` updated in same TX as movement
- Current stock = `SUM(movements)` or read from `inventory_balances` (maintained atomically)

### Sales & POS
- **cashier_shifts**, **cash_transactions**
- **sales**, **sale_items**, **payments**
- **refunds**, **refund_items**
- **held_orders**

### Courts
- **courts**, **court_rates**, **court_rate_schedules**
- **bookings**, **booking_payments**
- Unique constraint: `(court_id, start_at, end_at)` with exclusion constraint for overlaps (PostgreSQL `tstzrange`)

### Customers & Membership
- **customers**, **memberships**, **membership_tiers**, **loyalty_transactions**

### Purchasing
- **suppliers**, **purchase_orders**, **purchase_items**, **purchase_receipts**

### Operations
- **expenses**, **expense_categories**
- **audit_logs** — immutable append-only
- **sync_transactions** — idempotency tracking for mobile

### Key Constraints
```sql
-- Sale idempotency
UNIQUE (device_id, client_sale_uuid)

-- Receipt numbers per branch
UNIQUE (branch_id, receipt_number)

-- No double booking
EXCLUDE USING gist (court_id WITH =, tstzrange(start_at, end_at) WITH &&)
  WHERE (status NOT IN ('cancelled'))
```

All monetary fields: `NUMERIC(14,2)` — never float.

---

## Part 5 — FastAPI Endpoints (v1)

Base: `/api/v1`

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | username/password or PIN |
| POST | `/auth/refresh` | refresh token |
| POST | `/auth/logout` | revoke refresh |
| GET | `/auth/me` | current user + permissions |

### Catalog (read-only for POS)
| GET | `/products`, `/categories`, `/products/{id}` |

### Shifts
| POST | `/shifts/open`, `/shifts/close`, `/shifts/{id}/cash-in`, `/shifts/{id}/cash-out` |
| GET | `/shifts/current` |

### Sales
| POST | `/sales` | create (server recalculates totals) |
| GET | `/sales/{id}` |
| POST | `/sales/{id}/void` |
| POST | `/sales/{id}/refund` |
| POST | `/sales/hold`, `/sales/hold/{id}/resume` |

### Courts
| GET | `/courts` | active courts for the cashier branch |
| GET | `/courts/occupancy` | available / occupied / maintenance counts |
| GET | `/bookings?date=` | confirmed bookings for a day |
| POST | `/bookings/quote` | server-authoritative slot price |
| POST | `/bookings` | create booking (overlap locked) |
| POST | `/bookings/{id}/cancel` | cancel and free the slot (no money back) |
| POST | `/bookings/{id}/refund` | refund paid booking and cancel the slot |

### Sync
| POST | `/sync/push` | batch offline records |
| GET | `/sync/pull?since=` | catalog + config delta |

### Request Example — Create Sale
```json
{
  "client_sale_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "shift_id": 12,
  "device_id": "POS-001",
  "items": [
    {"product_id": 5, "quantity": "2", "modifiers": []}
  ],
  "discount_code": null,
  "customer_id": null,
  "payments": [
    {"method": "cash", "amount": "150.00"}
  ],
  "client_created_at": "2026-08-18T10:30:00+08:00"
}
```

### Response
```json
{
  "id": 1001,
  "transaction_number": "BR1-20260818-00042",
  "receipt_number": "R-00042",
  "status": "completed",
  "gross_amount": "150.00",
  "discount_amount": "0.00",
  "tax_amount": "0.00",
  "net_amount": "150.00",
  "payments": [...],
  "sync_status": "synced"
}
```

---

## Part 6 — Django Applications

| App | Responsibility |
|-----|----------------|
| accounts | Users, roles, permissions, devices, PIN |
| branches | Branches, settings |
| products | Categories, products, variants, modifiers |
| inventory | Movements, balances, adjustments, stock count |
| sales | Sales admin, refunds, held orders |
| shifts | Shift management, cash transactions |
| courts | Courts, rates, bookings, schedule |
| customers | Customers, loyalty |
| membership | Tiers, assignments, loyalty ledger (branch `memberships_enabled` flag) |
| purchasing | Suppliers, POs, receiving |
| expenses | Expense tracking |
| reports | Dashboards, exports |
| audit | Audit log viewer |
| sync | Sync conflict admin |

---

## Part 7 — Flutter Architecture

```
lib/
├── main.dart
├── app/                    # MaterialApp, routing, theme
├── core/
│   ├── auth/
│   ├── database/           # Drift/sqflite schema
│   ├── network/
│   ├── printing/
│   └── utils/
├── features/
│   ├── login/
│   ├── shift/
│   ├── pos/                # Home, cart, checkout
│   ├── payment/
│   ├── receipt/
│   ├── transactions/
│   ├── refund/
│   ├── bookings/
│   └── settings/
└── sync/
    ├── sync_engine.dart
    ├── push_queue.dart
    └── pull_handler.dart
```

**Screens:** Login → Open Shift → POS Home → Checkout → Payment → Receipt; plus Transactions, Held Orders, Refund, Shift Summary, Sync Status, Settings.

State management: **Riverpod** or **Bloc** — recommend Riverpod for DI + testability.

Local DB: **Drift** (typed SQLite) with migration versioning mirroring server catalog schema subset.

---

## Part 8 — Offline Sync Algorithm

### Principles
1. Server is authoritative for prices, tax, stock availability at commit time.
2. Every offline sale has `client_sale_uuid` (UUID v4).
3. Sync is **idempotent**: same UUID → same server sale, no duplicate.

### Push Flow
```
1. Device collects records WHERE sync_status = PENDING
2. POST /sync/push { sales: [...], shift_events: [...] }
3. For each sale (ordered by client_created_at):
   a. BEGIN TRANSACTION
   b. Check sync_transactions(client_uuid) — if exists, return existing mapping
   c. Validate device + shift + cashier still valid
   d. Re-fetch product prices from DB (not client prices)
   e. Recalculate totals server-side
   f. Lock inventory rows FOR UPDATE
   g. If insufficient stock → mark CONFLICT, store reason, skip or partial per policy
   h. Insert sale, items, payments, inventory movements
   i. Insert sync_transactions(device_id, client_uuid, server_sale_id)
   j. COMMIT
4. Return per-record status: SYNCED | CONFLICT | REJECTED
5. Device updates local SQLite from response
```

### Pull Flow
```
GET /sync/pull?since=<cursor>&branch_id=1
→ { products, categories, prices, tax_rules, payment_methods, users_pin_hashes, cursor }
→ Device upserts local catalog; never deletes sales locally
```

### Conflict Resolution
| Conflict | Resolution |
|----------|------------|
| Price changed | Server price wins; audit flag on sale |
| Product deleted | Reject line or substitute per config |
| Insufficient stock | CONFLICT queue; manager resolves in admin |
| Duplicate UUID | Return existing sale (idempotent) |
| Clock skew | `client_created_at` stored; `server_created_at` authoritative |

### Retry
- Exponential backoff: 1s, 2s, 4s, … max 5 min
- Max retries: unlimited while PENDING; dead-letter after 30 days → admin alert

---

## Part 9 — Transaction Integrity

### Isolation Level
Use PostgreSQL **`READ COMMITTED`** (default) with explicit row locks for inventory and bookings.

### Sale Workflow (Single DB Transaction)
```
BEGIN;
  -- 1. Validate shift is OPEN (lock shift row)
  SELECT * FROM cashier_shifts WHERE id = ? FOR UPDATE;

  -- 2. Idempotency check
  SELECT * FROM sync_transactions WHERE client_uuid = ?;

  -- 3. Lock inventory balance rows
  SELECT * FROM inventory_balances
  WHERE branch_id = ? AND product_id IN (...)
  FOR UPDATE;

  -- 4. Validate quantities
  -- 5. Server-side pricing (core/services/pricing.py)
  -- 6. INSERT sale, sale_items, payments
  -- 7. INSERT inventory_movements (negative qty)
  -- 8. UPDATE inventory_balances atomically
  -- 9. INSERT sync_transactions
COMMIT;
```

### Booking Workflow
- Use `SELECT FOR UPDATE` on court slot or PostgreSQL exclusion constraint.
- Serializable isolation optional for high-contention courts; start with READ COMMITTED + exclusion.

### Overselling Prevention
- Never update `products.stock` directly.
- Deduct via movement ledger only.
- Optional: `allow_negative_stock` branch setting (default false).
- Concurrency test: two POS terminals, one unit → exactly one succeeds.

---

## Part 10 — Development Roadmap

| Phase | Scope | Milestone |
|-------|-------|-----------|
| **1 — Foundation** | Docker, PG, Redis, auth, roles, branches, audit | Login works on web + API |
| **2 — Catalog & Inventory** | Products, categories, ledger, suppliers | Stock movements reconcile |
| **3 — POS Core** | Shifts, sales, payments, receipts, refunds | End-to-end sale in admin |
| **4 — Android POS** | Flutter UI, SQLite, sync engine | Offline sale syncs correctly |
| **5 — Courts** | Courts, rates, bookings, payments | No double booking |
| **6 — Reporting** | Dashboards, exports | Daily sales report accurate |
| **7 — Hardening** | Lockout, rate limits, RBAC on money actions, audit viewer, backups, prod Compose | Production checklist green |

---

## Architectural Rules (Non-Negotiable)

1. PostgreSQL is the source of truth.
2. SQLite is offline buffer only.
3. Never trust client totals.
4. Decimal/Numeric for all money.
5. Inventory = movement ledger.
6. Financial ops = atomic transactions.
7. No duplicated business rules.
8. Sync = idempotent.
9. Everything auditable.
10. Soft-delete reference data.
11. `branch_id` on all operational tables.
12. Keep it maintainable for a small team.
