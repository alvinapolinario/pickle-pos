from django import forms

from apps.branches.models import Branch
from apps.products.models import Category, Product


def _input(widget_class=forms.TextInput, **extra):
    attrs = {"class": "field-input", **extra}
    return widget_class(attrs=attrs)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("branch", "name", "sort_order", "is_active")
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "name": _input(placeholder="e.g. Drinks"),
            "sort_order": _input(forms.NumberInput, min="0"),
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


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "branch",
            "category",
            "sku",
            "barcode",
            "name",
            "description",
            "selling_price",
            "cost_price",
            "unit",
            "tax_status",
            "track_inventory",
            "reorder_level",
            "image",
            "is_active",
        )
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "category": forms.Select(attrs={"class": "field-input"}),
            "sku": _input(placeholder="BALL-OUT-YLW"),
            "barcode": _input(placeholder="Optional"),
            "name": _input(placeholder="Product name"),
            "description": forms.Textarea(attrs={"class": "field-input field-textarea", "rows": 3}),
            "selling_price": _input(forms.NumberInput, step="0.01", min="0"),
            "cost_price": _input(forms.NumberInput, step="0.01", min="0"),
            "unit": forms.Select(attrs={"class": "field-input"}),
            "tax_status": forms.Select(attrs={"class": "field-input"}),
            "track_inventory": forms.CheckboxInput(attrs={"class": "field-check"}),
            "reorder_level": _input(forms.NumberInput, step="0.001", min="0"),
            "is_active": forms.CheckboxInput(attrs={"class": "field-check"}),
        }

    def __init__(self, *args, branch: Branch | None = None, lock_branch: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        categories = Category.objects.filter(is_active=True)
        if branch:
            categories = categories.filter(branch=branch)
            if not self.instance.pk:
                self.fields["branch"].initial = branch
        self.fields["category"].queryset = categories.order_by("sort_order", "name")
        if lock_branch and branch:
            self.fields["branch"].widget = forms.HiddenInput()
            self.fields["branch"].initial = branch.pk

    def clean(self):
        cleaned = super().clean()
        branch = cleaned.get("branch")
        category = cleaned.get("category")
        if branch and category and category.branch_id != branch.id:
            self.add_error("category", "Category must belong to the same branch as the product.")
        return cleaned
