from django import forms
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q

from apps.accounts.models import Role, User
from apps.branches.models import Branch
from core.services.auth_service import AuthService


def _input(widget_class=forms.TextInput, **extra):
    return widget_class(attrs={"class": "field-input", **extra})


class StaffUserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=_input(forms.PasswordInput, autocomplete="new-password"),
        help_text="Required for Owner or Administrator (web console). Optional for Cashier if a PIN is set. Leave blank when editing to keep the current password.",
    )
    password_confirm = forms.CharField(
        required=False,
        label="Confirm password",
        widget=_input(forms.PasswordInput, autocomplete="new-password"),
    )
    pin = forms.CharField(
        required=False,
        label="Cashier PIN",
        widget=_input(forms.PasswordInput, autocomplete="new-password", inputmode="numeric"),
        help_text="Required 4–8 digit PIN for tablet cashiers. Leave blank when editing to keep the current PIN.",
    )
    pin_confirm = forms.CharField(
        required=False,
        label="Confirm PIN",
        widget=_input(forms.PasswordInput, autocomplete="new-password", inputmode="numeric"),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "branch",
            "roles",
            "is_active",
            "is_staff",
        )
        labels = {
            "is_staff": "Django admin access",
        }
        help_texts = {
            "is_staff": "Lets this person open /django-admin/. Console and tablet login use roles, not this flag.",
            "roles": "Owner or Administrator for the web console. Cashier for the POS tablet.",
        }
        widgets = {
            "username": _input(placeholder="username", autocomplete="off"),
            "first_name": _input(placeholder="First name"),
            "last_name": _input(placeholder="Last name"),
            "email": _input(forms.EmailInput, placeholder="email@example.com"),
            "phone": _input(placeholder="Optional phone"),
            "branch": forms.Select(attrs={"class": "field-input"}),
            "roles": forms.CheckboxSelectMultiple(attrs={"class": "checkbox-list"}),
            "is_active": forms.CheckboxInput(attrs={"class": "field-check"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "field-check"}),
        }

    def __init__(self, *args, branch: Branch | None = None, lock_branch: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        creating = not self.instance.pk
        self.fields["roles"].required = True
        self.fields["roles"].queryset = Role.objects.filter(is_active=True)
        if self.instance.pk:
            self.fields["roles"].queryset = Role.objects.filter(
                Q(is_active=True) | Q(pk__in=self.instance.roles.values("pk"))
            )
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        self.fields["branch"].required = False
        if branch and creating:
            self.fields["branch"].initial = branch
        if lock_branch and branch:
            self.fields["branch"].widget = forms.HiddenInput()
            self.fields["branch"].initial = branch.pk
        self.order_fields(
            [
                "username",
                "branch",
                "first_name",
                "last_name",
                "email",
                "phone",
                "roles",
                "password",
                "password_confirm",
                "pin",
                "pin_confirm",
                "is_active",
                "is_staff",
            ]
        )

    def clean_username(self) -> str:
        return (self.cleaned_data.get("username") or "").strip()

    def clean_pin(self) -> str:
        pin = (self.cleaned_data.get("pin") or "").strip()
        if pin and (not pin.isdigit() or not 4 <= len(pin) <= 8):
            raise forms.ValidationError("PIN must be 4 to 8 digits.")
        return pin

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password") or ""
        confirm = cleaned.get("password_confirm") or ""
        if password or confirm:
            if password != confirm:
                self.add_error("password_confirm", "Passwords do not match.")
            elif password:
                validate_password(password, user=self.instance)
        pin = cleaned.get("pin") or ""
        pin_confirm = cleaned.get("pin_confirm") or ""
        if pin or pin_confirm:
            if pin != pin_confirm:
                self.add_error("pin_confirm", "PINs do not match.")
        roles = list(cleaned.get("roles") or [])
        if not roles:
            self.add_error("roles", "Select at least one role.")
            return cleaned
        cashier_only = all(role.code == "cashier" for role in roles)
        creating = not self.instance.pk
        if cashier_only:
            has_pin = bool(pin) or (not creating and bool(self.instance.pin_hash))
            if not has_pin:
                self.add_error("pin", "Cashiers need a 4–8 digit PIN for the tablet.")
        else:
            has_password = bool(password) or (not creating and self.instance.has_usable_password())
            if not has_password:
                self.add_error("password", "A password is required for web console access.")
        return cleaned

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        elif not user.pk:
            user.set_unusable_password()
        pin = self.cleaned_data.get("pin")
        if pin:
            user.pin_hash = AuthService.hash_pin(pin)
        if commit:
            user.save()
            self.save_m2m()
        return user
