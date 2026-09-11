from django.conf import settings
from django.db import models

from common.validators import validate_upload_file

class Announcement(models.Model):
    class Audience(models.TextChoices):
        ALL = "ALL", "Everyone"
        STUDENTS = "STUDENTS", "Students"
        TEACHERS = "TEACHERS", "Teachers"
        STAFF = "STAFF", "Staff"
        HOD = "HOD", "HOD"

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    attachment = models.FileField(
        upload_to="announcements/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_upload_file],
        help_text="Allowed: PDF, DOC/DOCX, XLS/XLSX, JPG, JPEG, PNG (max 15 MB).",
    )
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    published_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
