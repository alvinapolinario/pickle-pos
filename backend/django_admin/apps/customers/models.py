from django.core.exceptions import ValidationError
from django.db import models


class Customer(models.Model):
    """Walk-in customers are allowed; this record is optional on a sale."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="customers",
    )
    name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "mobile"],
                condition=~models.Q(mobile=""),
                name="uniq_customer_branch_mobile",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["name"]),
        ]

    def clean(self) -> None:
        if self.mobile:
            self.mobile = self.mobile.strip()
        if not self.name.strip():
            raise ValidationError({"name": "Name is required."})

    def __str__(self) -> str:
        return self.name
