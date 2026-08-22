"""Sidebar navigation for the web admin console."""

NAV_SECTIONS = [
    {
        "label": None,
        "items": [
            {"name": "dashboard", "label": "Dashboard", "icon": "layout-dashboard"},
        ],
    },
    {
        "label": "POS",
        "items": [
            {"name": "sales", "label": "Sales", "icon": "shopping-cart", "url_name": "sales:sale_list"},
            {"name": "transactions", "label": "Transactions", "icon": "receipt", "url_name": "sales:transaction_list"},
            {"name": "refunds", "label": "Refunds", "icon": "undo-2", "url_name": "sales:refund_list"},
            {"name": "shifts", "label": "Shift Management", "icon": "clock-3", "url_name": "shifts:shift_list"},
        ],
    },
    {
        "label": "Inventory",
        "items": [
            {"name": "products", "label": "Products", "icon": "package", "url_name": "products:product_list"},
            {"name": "categories", "label": "Categories", "icon": "tags", "url_name": "products:category_list"},
            {"name": "stock", "label": "Stock", "icon": "warehouse", "url_name": "inventory:stock_list"},
            {"name": "stock_movements", "label": "Stock Movements", "icon": "arrow-left-right", "url_name": "inventory:movement_list"},
            {"name": "suppliers", "label": "Suppliers", "icon": "truck", "url_name": "purchasing:supplier_list"},
            {"name": "purchase_orders", "label": "Purchase Orders", "icon": "clipboard-list", "url_name": "purchasing:purchase_order_list"},
            {"name": "receiving", "label": "Receiving", "icon": "package-check", "url_name": "purchasing:receiving_list"},
        ],
    },
    {
        "label": "Courts",
        "items": [
            {"name": "courts", "label": "Courts", "icon": "layout-grid", "url_name": "courts:court_list"},
            {"name": "bookings", "label": "Bookings", "icon": "calendar-check", "url_name": "courts:booking_list"},
            {"name": "court_schedule", "label": "Court Schedule", "icon": "calendar-days", "url_name": "courts:court_schedule"},
            {"name": "court_rates", "label": "Rates & Pricing", "icon": "badge-peso", "url_name": "courts:rate_list"},
        ],
    },
    {
        "label": "Customers",
        "items": [
            {"name": "customers", "label": "Customers", "icon": "users", "url_name": "customers:customer_list"},
            {"name": "memberships", "label": "Memberships", "icon": "id-card", "url_name": "membership:membership_list"},
        ],
    },
    {
        "label": "Employees",
        "items": [
            {"name": "users", "label": "Users", "icon": "user-cog"},
            {"name": "roles", "label": "Roles & Permissions", "icon": "shield"},
            {"name": "cashiers", "label": "Cashiers", "icon": "user"},
        ],
    },
    {
        "label": "Reports",
        "items": [
            {"name": "report_sales", "label": "Sales Reports", "icon": "chart-column", "url_name": "console:report_sales"},
            {"name": "report_inventory", "label": "Inventory Reports", "icon": "chart-bar", "url_name": "console:report_inventory"},
            {"name": "report_courts", "label": "Court Reports", "icon": "pie-chart", "url_name": "console:report_courts"},
            {"name": "report_financial", "label": "Financial Reports", "icon": "wallet", "url_name": "console:report_financial"},
        ],
    },
]

NAV_FOOTER = [
    {"name": "expenses", "label": "Expenses", "icon": "circle-dollar-sign", "url_name": "expenses:expense_list"},
    {"name": "audit", "label": "Audit Log", "icon": "scroll-text", "url_name": "console:audit_list"},
    {"name": "settings", "label": "System Settings", "icon": "settings"},
]

PAGE_META = {
    "dashboard": {"title": "Dashboard", "subtitle": "Overview of your business"},
    "sales": {"title": "Sales", "subtitle": "Create and review POS sales"},
    "transactions": {"title": "Transactions", "subtitle": "All sales, voids, and payments"},
    "refunds": {"title": "Refunds", "subtitle": "Process and review returns"},
    "shifts": {"title": "Shift Management", "subtitle": "Open, close, and reconcile cashier shifts"},
    "products": {"title": "Products", "subtitle": "Catalog, SKUs, and pricing"},
    "categories": {"title": "Categories", "subtitle": "Organize canteen and retail items"},
    "stock": {"title": "Stock", "subtitle": "Current inventory balances by branch"},
    "stock_movements": {"title": "Stock Movements", "subtitle": "Append-only inventory ledger"},
    "suppliers": {"title": "Suppliers", "subtitle": "Vendor records and contacts"},
    "purchase_orders": {"title": "Purchase Orders", "subtitle": "Create and track purchase orders"},
    "receiving": {"title": "Receiving", "subtitle": "Receive stock against purchase orders"},
    "courts": {"title": "Courts", "subtitle": "Court status and configuration"},
    "bookings": {"title": "Bookings", "subtitle": "Reservations and walk-in court time"},
    "court_schedule": {"title": "Court Schedule", "subtitle": "Daily occupancy and availability"},
    "court_rates": {"title": "Rates & Pricing", "subtitle": "Hourly rates and membership pricing"},
    "customers": {"title": "Customers", "subtitle": "Customer profiles and history"},
    "memberships": {"title": "Memberships", "subtitle": "Tiers, benefits, and active members"},
    "users": {"title": "Users", "subtitle": "Staff accounts and branch assignment"},
    "roles": {"title": "Roles & Permissions", "subtitle": "Access control for the POS and admin"},
    "cashiers": {"title": "Cashiers", "subtitle": "Cashier profiles and PIN access"},
    "report_sales": {"title": "Sales Reports", "subtitle": "Daily, weekly, and product performance"},
    "report_inventory": {"title": "Inventory Reports", "subtitle": "Stock, wastage, and movement history"},
    "report_courts": {"title": "Court Reports", "subtitle": "Utilization and court revenue"},
    "report_financial": {"title": "Financial Reports", "subtitle": "Sales, expenses, and profit"},
    "expenses": {"title": "Expenses", "subtitle": "Operating expenses and categories"},
    "audit": {"title": "Audit Log", "subtitle": "Sensitive actions with filters and retention"},
    "settings": {"title": "System Settings", "subtitle": "POS pairing, receipt header, void passcode, and tax"},
}


def page_meta(page_name: str) -> dict[str, str]:
    return PAGE_META.get(page_name, {"title": page_name.title(), "subtitle": ""})
