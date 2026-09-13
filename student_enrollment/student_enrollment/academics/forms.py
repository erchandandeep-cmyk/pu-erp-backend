from django import forms
from .models import AcademicSession, Programme, Enrollment


class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ["name", "start_date", "end_date", "is_current"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 2026-27"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = ["code", "name", "department", "level", "duration_years", "total_semesters", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. BTECH-MECH"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "level": forms.Select(attrs={"class": "form-select"}),
            "duration_years": forms.NumberInput(attrs={"class": "form-control"}),
            "total_semesters": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["student", "programme", "academic_session", "batch_year", "roll_number", "current_semester", "status"]
        widgets = {
            "student": forms.Select(attrs={"class": "form-select"}),
            "programme": forms.Select(attrs={"class": "form-select"}),
            "academic_session": forms.Select(attrs={"class": "form-select"}),
            "batch_year": forms.NumberInput(attrs={"class": "form-control"}),
            "roll_number": forms.TextInput(attrs={"class": "form-control"}),
            "current_semester": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        self.fields["student"].queryset = User.objects.filter(role=User.Role.STUDENT).order_by("first_name")

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        instance.student = cleaned.get("student", instance.student)
        instance.status = cleaned.get("status", instance.status)
        try:
            instance.clean()
        except forms.ValidationError as exc:
            raise forms.ValidationError(exc)
        return cleaned
