from django import forms
from django.contrib.auth import authenticate
from .models import User

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
