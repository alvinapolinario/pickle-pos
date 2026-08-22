from django import forms

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.membership.models import Membership, MembershipTier


def _input(widget_class=forms.TextInput, **extra):
    return widget_class(attrs={"class": "field-input", **extra})


class MembershipTierForm(forms.ModelForm):
    class Meta:
        model = MembershipTier
        fields = (
            "branch",
            "code",
            "name",
            "court_discount_pct",
            "canteen_discount_pct",
            "priority_booking",
            "points_per_peso",
            "sort_order",
            "is_active",
        )
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "code": _input(placeholder="PREMIUM"),
            "name": _input(placeholder="Premium"),
            "court_discount_pct": _input(forms.NumberInput, step="0.01"),
            "canteen_discount_pct": _input(forms.NumberInput, step="0.01"),
            "priority_booking": forms.CheckboxInput(attrs={"class": "field-check"}),
            "points_per_peso": _input(forms.NumberInput, step="0.0001"),
            "sort_order": _input(forms.NumberInput),
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


class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ("branch", "customer", "tier", "started_on", "expires_on", "notes")
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "customer": forms.Select(attrs={"class": "field-input"}),
            "tier": forms.Select(attrs={"class": "field-input"}),
            "started_on": _input(forms.DateInput, type="date"),
            "expires_on": _input(forms.DateInput, type="date"),
            "notes": _input(placeholder="Optional note"),
        }

    def __init__(self, *args, branch: Branch | None = None, lock_branch: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        customers = Customer.objects.filter(is_active=True)
        tiers = MembershipTier.objects.filter(is_active=True)
        if branch:
            customers = customers.filter(branch=branch)
            tiers = tiers.filter(branch=branch)
            if not self.instance.pk:
                self.fields["branch"].initial = branch
        self.fields["customer"].queryset = customers
        self.fields["tier"].queryset = tiers
        if lock_branch and branch:
            self.fields["branch"].widget = forms.HiddenInput()
            self.fields["branch"].initial = branch.pk
