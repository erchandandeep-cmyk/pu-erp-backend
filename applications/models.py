import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

ALLOWED_UPLOAD_EXTENSIONS = ["doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "pdf"]


class ApplicationType(models.Model):

    name = models.CharField(
        max_length=120
    )

    description = models.TextField(
        blank=True
    )

    default_authority_role = models.CharField(
        max_length=20,
        choices=settings.AUTH_USER_MODEL and [
            ("TEACHER", "Teacher"),
            ("HOD", "HOD"),
            ("STAFF", "Staff"),
            ("ADMIN", "Department Admin"),
        ] or [],
        default="HOD",
    )

    active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.name


class Application(models.Model):

    class Status(models.TextChoices):

        SUBMITTED = "SUBMITTED", "Submitted"

        UNDER_REVIEW = (
            "UNDER_REVIEW",
            "Under Review",
        )

        FORWARDED = (
            "FORWARDED",
            "Forwarded",
        )

        APPROVED = (
            "APPROVED",
            "Approved",
        )

        REJECTED = (
            "REJECTED",
            "Rejected",
        )

        COMPLETED = (
            "COMPLETED",
            "Completed",
        )

    application_id = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )

    application_type = models.ForeignKey(
        ApplicationType,
        on_delete=models.PROTECT,
    )

    subject = models.CharField(
        max_length=200
    )

    body = models.TextField()

    authority = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_applications",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )

    current_remark = models.TextField(
        blank=True
    )

    attachment = models.FileField(
        upload_to="applications/%Y/%m/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS)],
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # -----------------------------------------------------
    # ARCHIVE
    # -----------------------------------------------------

    is_archived = models.BooleanField(
        default=False
    )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    def save(self, *args, **kwargs):

        if not self.application_id:

            unit_code = "GEN"
            org_unit = getattr(self.applicant, "org_unit", None)
            if org_unit is not None:
                unit_code = org_unit.code

            self.application_id = (
                f"APP-{unit_code}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

        super().save(
            *args,
            **kwargs
        )

    def __str__(self):

        return self.application_id


class ApplicationHistory(models.Model):

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="history",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    action = models.CharField(
        max_length=80
    )

    remark = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "-created_at"
        ]

    def __str__(self):

        return (
            f"{self.application.application_id} "
            f"- {self.action}"
        )