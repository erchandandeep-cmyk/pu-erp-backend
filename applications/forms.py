from django import forms

from .models import Application, ApplicationType
from accounts.models import User


class ApplicationForm(forms.ModelForm):

    class Meta:
        model = Application

        fields = [
            "application_type",
            "subject",
            "body",
            "authority",
            "attachment",
        ]

        widgets = {
            "application_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter application subject",
                }
            ),

            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 7,
                    "placeholder": "Enter application details",
                }
            ),

            "authority": forms.Select(
                attrs={
                    "class": "form-select authority-select",
                }
            ),

            "attachment": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        applicant = kwargs.pop("applicant", None)

        super().__init__(*args, **kwargs)

        # Only active application types
        self.fields["application_type"].queryset = (
            ApplicationType.objects.filter(
                active=True
            )
        )

        # Only active employees who can receive applications
        authority_qs = User.objects.filter(
            role__in=[
                User.Role.TEACHER,
                User.Role.HOD,
                User.Role.STAFF,
                User.Role.ADMIN,
            ],
            is_active=True,
            is_active_account=True,
        )

        # Scale-safety: once there are 70+ departments/300+ offices, a
        # student should not see every staff member university-wide -
        # narrow the list to their own org unit (department/college/
        # office) when one is set. Admins (no org_unit needed) still see
        # everyone if org_unit isn't set on the applicant.
        if applicant is not None and getattr(applicant, "org_unit_id", None):
            authority_qs = authority_qs.filter(org_unit_id=applicant.org_unit_id)

        self.fields["authority"].queryset = authority_qs.order_by(
            "first_name",
            "last_name",
        )

        # Display:
        # First Name + Last Name + Role + Org unit (falls back to the
        # legacy free-text department field for users not yet migrated)
        self.fields["authority"].label_from_instance = (
            lambda user:
            f"{user.get_full_name()} — "
            f"{user.get_role_display()} • "
            f"{user.org_unit.name if user.org_unit_id else user.department}"
        )