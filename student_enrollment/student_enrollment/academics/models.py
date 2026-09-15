from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from organizations.models import OrgUnit


class AcademicSession(models.Model):
    """
    An academic year, e.g. '2026-27'. Exactly one should be marked
    current at any time - saving a session as current automatically
    un-marks any other, so admins can't accidentally end up with two.
    """

    name = models.CharField(max_length=20, unique=True, help_text="e.g. 2026-27")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicSession.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Programme(models.Model):
    """
    A degree/diploma programme offered by a department, e.g. 'B.Tech
    Mechanical Engineering'. Kept separate from OrgUnit (the department)
    since one department can offer several programmes (UG, PG, PhD).
    """

    class Level(models.TextChoices):
        UG = "UG", "Undergraduate"
        PG = "PG", "Postgraduate"
        PHD = "PHD", "PhD / Research"
        DIPLOMA = "DIPLOMA", "Diploma / Certificate"

    code = models.SlugField(max_length=30, unique=True, help_text="e.g. BTECH-MECH, MSC-CHEM")
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        OrgUnit,
        on_delete=models.PROTECT,
        related_name="programmes",
        limit_choices_to={"unit_type__in": [
            OrgUnit.UnitType.TEACHING_DEPT,
            OrgUnit.UnitType.CONSTITUENT_COLLEGE,
            OrgUnit.UnitType.AFFILIATED_COLLEGE,
        ]},
    )
    level = models.CharField(max_length=10, choices=Level.choices)
    duration_years = models.PositiveSmallIntegerField(default=4)
    total_semesters = models.PositiveSmallIntegerField(default=8)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["department__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class Enrollment(models.Model):
    """
    Links a student to the programme/session/semester/roll number they
    are actually studying under - the single source of truth for 'what
    is this student enrolled in right now', replacing the old ad-hoc
    User.semester/User.section fields (kept on User for backward
    compatibility only, no longer authoritative).

    A student can have more than one Enrollment over time (e.g.
    re-admission, programme change) but should only have ONE with
    status=ACTIVE at a time - enforced in clean(), not a hard DB
    constraint, so historical/legacy data never breaks a migration.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed / Graduated"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        TRANSFERRED = "TRANSFERRED", "Transferred"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": "STUDENT"},
    )
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="enrollments")
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT, related_name="enrollments")
    batch_year = models.PositiveSmallIntegerField(help_text="Year the student's batch started, e.g. 2026")
    roll_number = models.CharField(max_length=40, blank=True)
    current_semester = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    enrolled_on = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-academic_session__start_date", "roll_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["programme", "roll_number"],
                condition=~models.Q(roll_number=""),
                name="unique_roll_number_per_programme",
            )
        ]

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} - {self.programme.code} ({self.academic_session.name})"

    def clean(self):
        if self.status == self.Status.ACTIVE:
            clash = Enrollment.objects.filter(
                student=self.student, status=self.Status.ACTIVE
            ).exclude(pk=self.pk)
            if clash.exists():
                raise ValidationError(
                    f"{self.student} already has an active enrollment "
                    f"({clash.first().programme.code}). Mark it Completed/"
                    f"Withdrawn/Transferred first, or edit that one instead."
                )
