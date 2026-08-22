from django.core.management.base import BaseCommand

from apps.audit.tasks import prune_audit_logs


class Command(BaseCommand):
    help = "Delete audit rows older than the configured retention window"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=None)

    def handle(self, *args, **options):
        deleted = prune_audit_logs(days=options["days"])
        self.stdout.write(self.style.SUCCESS(f"Pruned {deleted} audit log(s)."))
