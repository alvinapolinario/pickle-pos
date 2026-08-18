from django.db import models


class Branch(models.Model):
    """Physical location — supports future multi-branch expansion."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    timezone = models.CharField(max_length=50, default="Asia/Manila")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
