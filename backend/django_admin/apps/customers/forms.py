from django import forms

from apps.branches.models import Branch
from apps.customers.models import Customer


def _input(widget_class=forms.TextInput, **extra):
    return widget_class(attrs={"class": "field-input", **extra})


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("branch", "name", "mobile", "email", "notes", "is_active")
        widgets = {
            "branch": forms.Select(attrs={"class": "field-input"}),
            "name": _input(placeholder="Customer name"),
            "mobile": _input(placeholder="Mobile"),
            "email": _input(forms.EmailInput, placeholder="email@example.com"),
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
