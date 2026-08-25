from django import forms
from django.db.models import Q

from apps.branches.models import Branch
from apps.expenses.models import Expense, ExpenseCategory


def _input(widget_class=forms.TextInput, **extra):
    return widget_class(attrs={"class": "field-input", **extra})


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ("branch", "name", "is_active")
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "name": _input(placeholder="e.g. Utilities"),
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


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ("branch", "category", "amount", "incurred_on", "notes")
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "category": forms.Select(attrs={"class": "field-input"}),
            "amount": _input(forms.NumberInput, step="0.01", min="0.01"),
            "incurred_on": forms.DateInput(attrs={"class": "field-input", "type": "date"}, format="%Y-%m-%d"),
            "notes": _input(placeholder="Optional notes"),
        }

    def __init__(self, *args, branch: Branch | None = None, lock_branch: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        categories = ExpenseCategory.objects.filter(is_active=True)
        if branch:
            categories = categories.filter(branch=branch)
            if not self.instance.pk:
                self.fields["branch"].initial = branch
        if self.instance.pk and self.instance.category_id:
            categories = ExpenseCategory.objects.filter(Q(pk__in=categories) | Q(pk=self.instance.category_id))
        self.fields["category"].queryset = categories
        if lock_branch and branch:
            self.fields["branch"].widget = forms.HiddenInput()
            self.fields["branch"].initial = branch.pk
