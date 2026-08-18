"""Seed default roles and permissions."""

from django.core.management.base import BaseCommand

from apps.accounts.models import Permission, Role

DEFAULT_PERMISSIONS = [
    ("sales.*", "All sales operations", "sales"),
    ("sales.create", "Create sales", "sales"),
    ("sales.void", "Void sales", "sales"),
    ("sales.refund", "Process refunds", "sales"),
    ("inventory.*", "All inventory operations", "inventory"),
    ("inventory.adjust", "Adjust inventory", "inventory"),
    ("courts.*", "All court operations", "courts"),
    ("reports.view", "View reports", "reports"),
    ("users.manage", "Manage users", "users"),
    ("settings.manage", "Manage system settings", "settings"),
    ("audit.view", "View audit logs", "audit"),
]

DEFAULT_ROLES = {
    "owner": {
        "name": "Owner",
        "permissions": ["*"],
    },
    "administrator": {
        "name": "Administrator",
        "permissions": [
            "sales.*",
            "inventory.*",
            "courts.*",
            "reports.view",
            "users.manage",
            "settings.manage",
            "audit.view",
        ],
    },
    "manager": {
        "name": "Manager",
        "permissions": [
            "sales.*",
            "inventory.*",
            "courts.*",
            "reports.view",
            "audit.view",
        ],
    },
    "cashier": {
        "name": "Cashier",
        "permissions": ["sales.create", "sales.refund"],
    },
    "inventory_staff": {
        "name": "Inventory Staff",
        "permissions": ["inventory.*"],
    },
    "court_staff": {
        "name": "Court Staff",
        "permissions": ["courts.*", "sales.create"],
    },
    "auditor": {
        "name": "Auditor",
        "permissions": ["reports.view", "audit.view"],
    },
}


class Command(BaseCommand):
    help = "Seed default RBAC roles and permissions"

    def handle(self, *args, **options):
        permission_map: dict[str, Permission] = {}

        for code, name, module in DEFAULT_PERMISSIONS:
            permission, _ = Permission.objects.update_or_create(
                code=code,
                defaults={"name": name, "module": module},
            )
            permission_map[code] = permission

        owner_star, _ = Permission.objects.update_or_create(
            code="*",
            defaults={"name": "All permissions", "module": "system"},
        )
        permission_map["*"] = owner_star

        for role_code, config in DEFAULT_ROLES.items():
            role, _ = Role.objects.update_or_create(
                code=role_code,
                defaults={"name": config["name"]},
            )
            role.permissions.set([permission_map[code] for code in config["permissions"]])
            self.stdout.write(self.style.SUCCESS(f"Seeded role: {role.name}"))

        self.stdout.write(self.style.SUCCESS("RBAC seed complete"))
