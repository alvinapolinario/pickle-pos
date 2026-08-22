from decimal import Decimal

from django import forms
from django.forms import formset_factory

from apps.branches.models import Branch
from apps.products.models import Product
from apps.purchasing.models import PurchaseOrder, Supplier


def _input(widget_class=forms.TextInput, **extra):
    attrs = {"class": "field-input", **extra}
    return widget_class(attrs=attrs)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ("branch", "name", "contact_name", "phone", "email", "address", "notes", "is_active")
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "name": _input(placeholder="Supplier name"),
            "contact_name": _input(placeholder="Contact person"),
            "phone": _input(placeholder="Phone"),
            "email": _input(forms.EmailInput, placeholder="email@supplier.com"),
            "address": forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 2}),
            "notes": forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 2}),
            "is_active": forms.CheckboxInput(attrs={"class": "field-check"}),
        }

    def __init__(self, *args, branch: Branch | None = None, lock_branch: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        if branch and not self.instance.pk:
            self.fields["branch"].initial = branch
        if lock_branch and branch:
            self.fields["branch"].widget = forms.HiddenInput()
            self.fields["branch"].initial = branch.pk


class PurchaseOrderForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.none(),
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    expected_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "field-input", "type": "date"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 2}),
    )

    def __init__(self, *args, branch: Branch | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        suppliers = Supplier.objects.filter(is_active=True)
        if branch:
            suppliers = suppliers.filter(branch=branch)
        self.fields["supplier"].queryset = suppliers.order_by("name")


class PurchaseItemForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    quantity_ordered = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        widget=_input(forms.NumberInput, step="0.001", min="0.001"),
        label="Qty",
    )
    unit_cost = forms.DecimalField(
        required=False,
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0"),
        widget=_input(forms.NumberInput, step="0.01", min="0"),
        label="Unit cost",
    )

    def __init__(self, *args, branch: Branch | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        products = Product.objects.filter(track_inventory=True, is_active=True).order_by("name")
        if branch:
            products = products.filter(branch=branch)
        self.fields["product"].queryset = products

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        qty = cleaned.get("quantity_ordered")
        cost = cleaned.get("unit_cost")
        filled = bool(product or qty or cost is not None)
        if filled and (not product or not qty):
            raise forms.ValidationError("Each line needs a product and quantity.")
        if product and cost is None:
            cleaned["unit_cost"] = product.cost_price
        return cleaned


class BasePurchaseItemFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        products = []
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            product = form.cleaned_data.get("product")
            if not product:
                continue
            if product in products:
                raise forms.ValidationError("Each product can appear only once.")
            products.append(product)
        if self.total_error_count() == 0 and not products:
            raise forms.ValidationError("Add at least one purchase item.")


def make_item_formset(branch: Branch | None, **kwargs):
    formset_class = formset_factory(
        PurchaseItemForm,
        formset=BasePurchaseItemFormSet,
        extra=1,
        can_delete=True,
    )

    class BoundItemForm(PurchaseItemForm):
        def __init__(self, *args, **inner):
            super().__init__(*args, branch=branch, **inner)

    formset_class.form = BoundItemForm
    return formset_class(**kwargs)


class ReceiveOrderForm(forms.Form):
    purchase_order = forms.ModelChoiceField(
        queryset=PurchaseOrder.objects.none(),
        widget=forms.Select(attrs={"class": "field-input", "data-reload-form": "po"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 2}),
    )

    def __init__(self, *args, queryset=None, lock_po: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["purchase_order"].queryset = queryset if queryset is not None else self.fields["purchase_order"].queryset
        if lock_po:
            self.fields["purchase_order"].widget = forms.HiddenInput()


class ReceiveLineForm(forms.Form):
    purchase_item_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        widget=_input(forms.NumberInput, step="0.001", min="0"),
        label="Qty",
    )
    unit_cost = forms.DecimalField(
        required=False,
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0"),
        widget=_input(forms.NumberInput, step="0.01", min="0"),
        label="Unit cost",
    )


def make_receive_formset(**kwargs):
    return formset_factory(ReceiveLineForm, extra=0, can_delete=False)(**kwargs)
