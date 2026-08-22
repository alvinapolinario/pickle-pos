from apps.branches.models import Branch
from apps.console.navigation import NAV_FOOTER, NAV_SECTIONS


def console_nav(request):
    user = request.user if request.user.is_authenticated else None
    display_name = "Staff"
    role_name = "User"
    initials = "ST"

    if user:
        display_name = user.get_full_name() or user.username
        role = user.roles.order_by("name").first()
        if user.is_superuser and not role:
            role_name = "Owner"
        elif role:
            role_name = role.name
        elif user.is_staff:
            role_name = "Administrator"
        parts = display_name.split()
        initials = "".join(part[0] for part in parts[:2]).upper() if parts else user.username[:2].upper()

    return {
        "nav_sections": NAV_SECTIONS,
        "nav_footer": NAV_FOOTER,
        "console_branches": Branch.objects.filter(is_active=True),
        "console_user_name": display_name,
        "console_user_role": role_name,
        "console_user_initials": initials,
        "console_current_branch": (
            user.branch if user and getattr(user, "branch_id", None) else Branch.objects.filter(is_active=True).first()
        ),
    }
