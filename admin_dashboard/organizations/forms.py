from django import forms
from .models import OrgUnit


class OrgUnitForm(forms.ModelForm):
    class Meta:
        model = OrgUnit
        fields = ["code", "name", "unit_type", "parent", "contact_email", "contact_phone", "address", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. MECH, RC-BTI, VC"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "unit_type": forms.Select(attrs={"class": "form-select"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
