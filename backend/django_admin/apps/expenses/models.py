from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class ExpenseCategory(models.Model):
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="expense_categories")
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "name"], name="uniq_expense_category_branch_name"),
        ]

    def __str__(self) -> str:
        return self.name


class Expense(models.Model):
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="expenses")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="expenses")
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    incurred_on = models.DateField()
    notes = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-incurred_on", "-id"]
        indexes = [
            models.Index(fields=["branch", "incurred_on"]),
        ]

    def __str__(self) -> str:
        return f"{self.category} {self.amount}"
