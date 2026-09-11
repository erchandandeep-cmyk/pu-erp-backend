from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

ALLOWED_UPLOAD_EXTENSIONS = ["doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "pdf"]


class Document(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to="documents/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS)],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_official = models.BooleanField(default=False)

    def __str__(self):
        return self.title
