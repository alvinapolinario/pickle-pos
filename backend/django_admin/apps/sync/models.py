from django.db import models


class SyncTransaction(models.Model):
    """Idempotency map from a device client UUID to a server entity."""

    device = models.ForeignKey(
        "accounts.Device",
        on_delete=models.PROTECT,
        related_name="sync_transactions",
    )
    client_uuid = models.UUIDField()
    server_entity_type = models.CharField(max_length=50, default="sale")
    server_entity_id = models.BigIntegerField()
    status = models.CharField(max_length=20, default="synced")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["device", "client_uuid"], name="uniq_sync_device_client_uuid"),
        ]
        indexes = [
            models.Index(fields=["server_entity_type", "server_entity_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.device_id}:{self.client_uuid}"
