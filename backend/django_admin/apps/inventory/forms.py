from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator

from apps.products.models import Product
from core.domain.inventory import EXPIRED, STOCK_IN, STOCK_OUT, WASTAGE

MANUAL_MOVEMENT_TYPES = (
    (STOCK_IN, "Stock In"),
    (STOCK_OUT, "Stock Out"),
    (WASTAGE, "Wastage"),
    (EXPIRED, "Expired"),
)


def _input(widget_class=forms.TextInput, **extra):
    attrs = {"class": "field-input", **extra}
    return widget_class(attrs=attrs)


class MovementForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    movement_type = forms.ChoiceField(
        choices=MANUAL_MOVEMENT_TYPES,
        widget=forms.Select(attrs={"class": "field-input"}),
        initial=STOCK_IN,
    )
    quantity = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        widget=_input(forms.NumberInput, step="0.001", min="0.001"),
    )
    unit_cost = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        initial=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        widget=_input(forms.NumberInput, step="0.01", min="0"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 3}),
    )

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        products = Product.objects.filter(track_inventory=True, is_active=True).order_by("name")
        if branch:
            products = products.filter(branch=branch)
        self.fields["product"].queryset = products


class StockCountForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    counted_quantity = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        widget=_input(forms.NumberInput, step="0.001", min="0"),
        label="Counted quantity",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 3}),
    )

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        products = Product.objects.filter(track_inventory=True, is_active=True).order_by("name")
        if branch:
            products = products.filter(branch=branch)
        self.fields["product"].queryset = products
