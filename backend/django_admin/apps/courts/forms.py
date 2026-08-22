from django import forms

from apps.branches.models import Branch
from apps.courts.models import Booking, Court, CourtRate
from apps.customers.models import Customer


def _input(widget_class=forms.TextInput, **extra):
    return widget_class(attrs={"class": "field-input", **extra})


class CourtForm(forms.ModelForm):
    class Meta:
        model = Court
        fields = ("branch", "code", "name", "status", "hourly_rate", "sort_order", "is_active")
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "code": _input(placeholder="C1"),
            "name": _input(placeholder="Court 1"),
            "status": forms.Select(attrs={"class": "field-input"}),
            "hourly_rate": _input(forms.NumberInput, step="0.01", min="0"),
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


class CourtRateForm(forms.ModelForm):
    class Meta:
        model = CourtRate
        fields = ("court", "weekday", "hourly_rate", "is_active")
        widgets = {
            "court": forms.Select(attrs={"class": "field-input"}),
            "weekday": forms.Select(attrs={"class": "field-input"}),
            "hourly_rate": _input(forms.NumberInput, step="0.01", min="0"),
            "is_active": forms.CheckboxInput(attrs={"class": "field-check"}),
        }

    def __init__(self, *args, branch: Branch | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        courts = Court.objects.filter(is_active=True)
        if branch:
            courts = courts.filter(branch=branch)
        self.fields["court"].queryset = courts


class BookingForm(forms.Form):
    court = forms.ModelChoiceField(queryset=Court.objects.none(), widget=forms.Select(attrs={"class": "field-input"}))
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    start_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"class": "field-input", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"],
    )
    end_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"class": "field-input", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"],
    )
    payment_method = forms.ChoiceField(
        choices=Booking.PaymentMethod.choices,
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    notes = forms.CharField(required=False, widget=_input(placeholder="Optional notes"))

    def __init__(self, *args, branch: Branch | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        courts = Court.objects.filter(is_active=True)
        customers = Customer.objects.filter(is_active=True)
        if branch:
            courts = courts.filter(branch=branch)
            customers = customers.filter(branch=branch)
        self.fields["court"].queryset = courts
        self.fields["customer"].queryset = customers
        self.fields["customer"].empty_label = "Walk-in"


class BookingRefundForm(forms.Form):
    method = forms.ChoiceField(
        choices=Booking.PaymentMethod.choices,
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    reason = forms.CharField(required=False, widget=_input(placeholder="Optional reason"))
