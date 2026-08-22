# PostgreSQL Schema Design

All monetary columns use `NUMERIC(14,2)`. All operational tables include `branch_id` where applicable.

---

## Identity & Access

### branches
| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| code | VARCHAR(20) UNIQUE | e.g. HQ |
| name | VARCHAR(150) | |
| address | TEXT | |
| timezone | VARCHAR(50) | default Asia/Manila |
| is_active | BOOLEAN | |

### users (extends Django auth)
| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| branch_id | FK branches | nullable for owner |
| pin_hash | VARCHAR(128) | cashier quick login |
| phone | VARCHAR(30) | |

### roles / permissions / role_permissions
Standard RBAC. Permission codes: `sales.create`, `inventory.*`, etc.

### devices
| Column | Type | Notes |
|--------|------|-------|
| device_code | VARCHAR(50) UNIQUE | POS terminal ID |
| branch_id | FK | |
| is_active | BOOLEAN | |

### refresh_tokens
Hashed refresh tokens for mobile JWT rotation.

---

## Catalog

### categories
`id`, `branch_id`, `name`, `sort_order`, `is_active`

### products
| Column | Type | Notes |
|--------|------|-------|
| sku | VARCHAR(50) | UNIQUE per branch |
| barcode | VARCHAR(50) | indexed |
| name | VARCHAR(200) | |
| category_id | FK | |
| selling_price | NUMERIC(14,2) | |
| cost_price | NUMERIC(14,2) | |
| unit | VARCHAR(20) | piece, bottle, etc. |
| tax_status | VARCHAR(20) | taxable, exempt |
| track_inventory | BOOLEAN | |
| is_active | BOOLEAN | soft deactivate |

### product_variants / product_modifiers
Optional size/flavor variants and add-ons.

### branch_product_prices
Branch-specific price overrides: `(branch_id, product_id)` UNIQUE.

---

## Inventory (Ledger)

### inventory_movements (append-only)
| Column | Type | Notes |
|--------|------|-------|
| product_id | FK | |
| branch_id | FK | |
| movement_type | VARCHAR(30) | stock_in, sale, adjustment, wastage, etc. |
| quantity | NUMERIC(12,3) | signed; negative = out |
| unit_cost | NUMERIC(14,2) | |
| reference_type | VARCHAR(50) | sale, purchase_receipt, adjustment |
| reference_id | BIGINT | |
| performed_by_id | FK users | |

**Current stock** = `SUM(quantity) GROUP BY branch_id, product_id`  
Maintained in `inventory_balances` updated atomically with each movement.

### inventory_balances
`(branch_id, product_id)` UNIQUE — `quantity`, `updated_at`  
Updated in same transaction as movement insert.

---

## Sales & POS

### cashier_shifts
| Column | Type | Notes |
|--------|------|-------|
| cashier_id | FK users | |
| branch_id | FK | |
| status | VARCHAR(20) | open, closed |
| opening_cash | NUMERIC(14,2) | |
| expected_cash | NUMERIC(14,2) | computed at close |
| actual_cash | NUMERIC(14,2) | |
| over_short | NUMERIC(14,2) | |

### cash_transactions
Cash-in, cash-out during shift.

### sales
| Column | Type | Notes |
|--------|------|-------|
| transaction_number | VARCHAR(50) | UNIQUE |
| receipt_number | VARCHAR(50) | UNIQUE per branch |
| client_sale_uuid | UUID | UNIQUE with device_id |
| device_id | FK | |
| shift_id | FK | |
| gross_amount | NUMERIC(14,2) | server-calculated |
| discount_amount | NUMERIC(14,2) | |
| tax_amount | NUMERIC(14,2) | |
| net_amount | NUMERIC(14,2) | |
| status | VARCHAR(20) | completed, void, held |
| payment_status | VARCHAR(20) | paid, partial, unpaid |

### sale_items / payments / refunds / refund_items
Standard normalized POS structure.

---

## Courts

### courts
`branch_id`, `code`, `name`, `status` (available, maintenance), `hourly_rate`, `sort_order`, `is_active`. Occupied is computed from live bookings, not stored.

### court_rates
Weekday hourly override (`weekday` 0=Monday … 6=Sunday). Default rate stays on `courts.hourly_rate`.

### bookings
| Column | Type | Notes |
|--------|------|-------|
| court_id | FK | |
| customer_id | FK nullable | Walk-in allowed |
| booked_by_id | FK | Cashier |
| booking_number | VARCHAR(50) | Unique per branch (`BK-YYYYMMDD-0001`) |
| start_at | TIMESTAMPTZ | |
| end_at | TIMESTAMPTZ | Must be after `start_at` |
| status | VARCHAR(20) | confirmed, cancelled, completed |
| amount | NUMERIC(14,2) | Server-quoted |
| payment_method | VARCHAR(20) | cash, gcash, maya, bank_transfer, other |
| payment_status | VARCHAR(20) | unpaid, paid, refunded |

### booking_refunds
Full refund of a paid booking. Cancels the slot. Amount is server-authoritative (`booking.amount`). Document numbers unique per branch (`BKR-`).

**Overlap:** `SELECT FOR UPDATE` on the court plus a service-level range check (`start_at < end AND end_at > start`) for confirmed/completed bookings. PostgreSQL `EXCLUDE USING gist` is deferred until the test runner is Postgres-only.

---

## Customers & Membership

### customers
`name`, `mobile`, `email`, `loyalty_points`, `notes`

### membership_tiers
`branch_id`, `code`, `name`, `court_discount_pct`, `canteen_discount_pct`, `priority_booking`, `points_per_peso`

### memberships
`customer_id`, `tier_id`, `started_on`, `expires_on`, `status` (active / expired / cancelled)

### loyalty_transactions
Append-only points ledger: `points` (signed), `kind` (earn / reverse), `source_type`, `source_id`

### branches
`memberships_enabled` — feature flag. When false, tiers stay but discounts and points do not apply.

---

## Purchasing

### suppliers / purchase_orders / purchase_items / purchase_receipts / purchase_returns
PO workflow: draft → ordered → receive (`stock_in`) → optional return (`stock_out`). Quantity received is net of returns. Document numbers are unique per branch (`PO-`, `GRN-`, `PRN-`).

---

## Operations

### expenses / expense_categories
`branch_id`, `category_id`, `amount`, `incurred_on`, `notes`, `created_by_id`. Categories are branch-scoped. Used by financial reports.

### audit_logs
Immutable: `action`, `entity_type`, `entity_id`, `previous_values`, `new_values`, `device_id`, `ip_address`

### sync_transactions
| Column | Type | Notes |
|--------|------|-------|
| device_id | FK | |
| client_uuid | UUID | |
| server_entity_type | VARCHAR(50) | sale |
| server_entity_id | BIGINT | |

UNIQUE `(device_id, client_uuid)` — idempotency guarantee.

---

## Indexes (Critical)

```sql
CREATE INDEX idx_sales_branch_created ON sales(branch_id, created_at DESC);
CREATE INDEX idx_movements_product_branch ON inventory_movements(product_id, branch_id);
CREATE INDEX idx_bookings_court_start ON bookings(court_id, start_at);
CREATE UNIQUE INDEX idx_sales_client_uuid ON sales(device_id, client_sale_uuid);
```
