from django import forms
from django.contrib.auth import authenticate
from .models import User


class UserCreateForm(forms.ModelForm):
    """
    For an admin manually creating a single account (student, teacher,
    HOD, staff, or an administrative post like VC/Registrar/Dean).
    Bulk creation (many accounts at once) uses the CSV/Excel importer
    instead - this form is for one-off accounts.
    """

    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), min_length=8)

    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "role", "designation", "org_unit",
            "employee_or_student_id", "phone", "semester", "section",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "designation": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Registrar, Assistant Professor"}),
            "org_unit": forms.Select(attrs={"class": "form-select"}),
            "employee_or_student_id": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "semester": forms.NumberInput(attrs={"class": "form-control"}),
            "section": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.actor = kwargs.pop("actor", None)
        super().__init__(*args, **kwargs)
        for name in ["first_name", "role"]:
            self.fields[name].required = True

    def clean_role(self):
        role = self.cleaned_data["role"]
        admin_value = getattr(User.Role, "ADMIN", None)
        admin_value = getattr(admin_value, "value", admin_value)
        actor_is_admin = bool(
            self.actor and (self.actor.is_superuser or self.actor.role == admin_value)
        )
        if role == admin_value and not actor_is_admin:
            raise forms.ValidationError(
                "Only an Admin/Superuser can create another Admin-level account."
            )
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_active = True
        user.is_active_account = True
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """
    Edit an existing account: role, designation, org unit, contact
    details, and active/inactive status. Does not change the password -
    use the separate 'reset password' action for that.
    """

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email",
            "role", "designation", "org_unit",
            "employee_or_student_id", "phone", "semester", "section",
            "is_active_account",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "designation": forms.TextInput(attrs={"class": "form-control"}),
            "org_unit": forms.Select(attrs={"class": "form-select"}),
            "employee_or_student_id": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "semester": forms.NumberInput(attrs={"class": "form-control"}),
            "section": forms.TextInput(attrs={"class": "form-control"}),
            "is_active_account": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), min_length=8, label="New password")


class LoginForm(forms.Form):
    user_id = forms.CharField(label="User ID")
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        user_id = cleaned.get("user_id")
        password = cleaned.get("password")
        if user_id and password:
            user = User.objects.filter(employee_or_student_id__iexact=user_id).first()
            if not user:
                user = User.objects.filter(username__iexact=user_id).first()
            if not user:
                raise forms.ValidationError("Invalid User ID or password.")
            auth_user = authenticate(username=user.username, password=password)
            if not auth_user or not auth_user.is_active or not auth_user.is_active_account:
                raise forms.ValidationError("Invalid User ID/password or inactive account.")
            cleaned["user"] = auth_user
        return cleaned
