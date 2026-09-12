from django.contrib.auth.models import AbstractUser
from django.db import models

from organizations.models import OrgUnit


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TEACHER = "TEACHER", "Teacher"
        STAFF = "STAFF", "Staff"
        HOD = "HOD", "HOD"
        ADMIN = "ADMIN", "Department Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    employee_or_student_id = models.CharField(max_length=40, unique=True, null=True, blank=True)
    designation = models.CharField(
        max_length=150,
        blank=True,
        help_text="Job title for display only (e.g. 'Registrar', 'Assistant "
        "Professor', 'Section Officer') - separate from 'role', which "
        "controls what they can do in the app.",
    )
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(
        max_length=120,
        default="Mechanical Engineering",
        blank=True,
        help_text="Legacy free-text field, kept so old data still works. "
        "New code should use 'org_unit' instead.",
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        help_text="The department / college / regional centre / office this "
        "user belongs to.",
    )
    semester = models.PositiveSmallIntegerField(null=True, blank=True)
    section = models.CharField(max_length=20, blank=True)
    is_active_account = models.BooleanField(default=True)
    signature = models.ImageField(
    upload_to="signatures/",
    blank=True,
    null=True
)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.is_active_account = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_or_student_id or self.username} - {self.get_role_display()}"

    @property
    def display_name(self):
        return self.get_full_name() or self.username
