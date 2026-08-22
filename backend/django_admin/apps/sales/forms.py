from decimal import Decimal

from django import forms
from django.forms import formset_factory

from apps.customers.models import Customer
from apps.products.models import Product
from apps.sales.models import Payment


def _input(widget_class=forms.TextInput, **extra):
    return widget_class(attrs={"class": "field-input", **extra})


class ShiftOpenForm(forms.Form):
    opening_cash = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.00"),
        widget=_input(forms.NumberInput, step="0.01", min="0"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 2}),
    )


class CashMoveForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=_input(forms.NumberInput, step="0.01", min="0.01"),
    )
    reason = forms.CharField(required=False, widget=_input(placeholder="Reason"))


class ShiftCloseForm(forms.Form):
    actual_cash = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.00"),
        widget=_input(forms.NumberInput, step="0.01", min="0"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 2}),
    )


class SaleItemForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    quantity = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        widget=_input(forms.NumberInput, step="0.001", min="0.001"),
        label="Qty",
    )

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        products = Product.objects.filter(is_active=True).order_by("name")
        if branch:
            products = products.filter(branch=branch)
        self.fields["product"].queryset = products


class BaseSaleItemFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        count = 0
        for form in self.forms:
            data = getattr(form, "cleaned_data", None) or {}
            if data.get("DELETE") or not data.get("product"):
                continue
            if not data.get("quantity"):
                raise forms.ValidationError("Each line needs a quantity.")
            count += 1
        if self.total_error_count() == 0 and count == 0:
            raise forms.ValidationError("Add at least one item.")


def make_sale_item_formset(branch, extra=1, **kwargs):
    formset_class = formset_factory(SaleItemForm, formset=BaseSaleItemFormSet, extra=extra, can_delete=True)

    class Bound(SaleItemForm):
        def __init__(self, *args, **inner):
            super().__init__(*args, branch=branch, **inner)

    formset_class.form = Bound
    return formset_class(**kwargs)


class SalePaymentForm(forms.Form):
    method = forms.ChoiceField(
        choices=Payment.Method.choices,
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    amount = forms.DecimalField(
        required=False,
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=_input(forms.NumberInput, step="0.01", min="0.01"),
    )
    reference = forms.CharField(required=False, widget=_input(placeholder="Ref (optional)"))


class BasePaymentFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        count = 0
        for form in self.forms:
            data = getattr(form, "cleaned_data", None) or {}
            if data.get("DELETE") or not data.get("amount"):
                continue
            count += 1
        if self.total_error_count() == 0 and count == 0:
            raise forms.ValidationError("Add at least one payment.")


def make_payment_formset(**kwargs):
    return formset_factory(SalePaymentForm, formset=BasePaymentFormSet, extra=1, can_delete=True)(**kwargs)


class SaleHeaderForm(forms.Form):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        required=False,
        empty_label="Walk-in",
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    discount_amount = forms.DecimalField(
        required=False,
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.00"),
        initial=Decimal("0.00"),
        widget=_input(forms.NumberInput, step="0.01", min="0"),
        label="Discount",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 2}),
    )

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        customers = Customer.objects.filter(is_active=True).order_by("name")
        if branch:
            customers = customers.filter(branch=branch)
        self.fields["customer"].queryset = customers


class RefundLineForm(forms.Form):
    sale_item_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        widget=_input(forms.NumberInput, step="0.001", min="0"),
    )


def make_refund_formset(**kwargs):
    return formset_factory(RefundLineForm, extra=0)(**kwargs)


class RefundHeaderForm(forms.Form):
    method = forms.ChoiceField(
        choices=Payment.Method.choices,
        initial=Payment.Method.CASH,
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    reason = forms.CharField(required=False, widget=_input(placeholder="Reason"))
