from django import forms
from .models import AcademicSession, Programme, Enrollment, Course, CourseRegistration, Exam


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


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["code", "name", "programme", "semester_number", "credits", "course_type", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. CS201"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "programme": forms.Select(attrs={"class": "form-select"}),
            "semester_number": forms.NumberInput(attrs={"class": "form-control"}),
            "credits": forms.NumberInput(attrs={"class": "form-control"}),
            "course_type": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CourseRegistrationForm(forms.ModelForm):
    class Meta:
        model = CourseRegistration
        fields = ["student", "course", "academic_session", "status"]
        widgets = {
            "student": forms.Select(attrs={"class": "form-select"}),
            "course": forms.Select(attrs={"class": "form-select"}),
            "academic_session": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        self.fields["student"].queryset = User.objects.filter(role=User.Role.STUDENT).order_by("first_name")

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        for f in ["student", "course", "academic_session", "status"]:
            if f in cleaned:
                setattr(instance, f, cleaned[f])
        try:
            instance.clean()
        except forms.ValidationError as exc:
            raise forms.ValidationError(exc)
        return cleaned


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ["course", "academic_session", "exam_type", "exam_date", "max_marks", "passing_marks", "min_attendance_percent", "is_published"]
        widgets = {
            "course": forms.Select(attrs={"class": "form-select"}),
            "academic_session": forms.Select(attrs={"class": "form-select"}),
            "exam_type": forms.Select(attrs={"class": "form-select"}),
            "exam_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "max_marks": forms.NumberInput(attrs={"class": "form-control"}),
            "passing_marks": forms.NumberInput(attrs={"class": "form-control"}),
            "min_attendance_percent": forms.NumberInput(attrs={"class": "form-control"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        for f in ["passing_marks", "max_marks"]:
            if f in cleaned:
                setattr(instance, f, cleaned[f])
        try:
            instance.clean()
        except forms.ValidationError as exc:
            raise forms.ValidationError(exc)
        return cleaned
