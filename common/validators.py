import os

from django.core.exceptions import ValidationError

# Wherever a form in the app needs "upload any file" (applications,
# announcements, documents, and future modules), it should reuse this
# list rather than inventing its own, so the allowed file types stay
# consistent across the whole ERP.
DOCUMENT_EXTENSIONS = [".pdf", ".doc", ".docx", ".xls", ".xlsx"]
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"]
ALL_UPLOAD_EXTENSIONS = DOCUMENT_EXTENSIONS + IMAGE_EXTENSIONS

MAX_UPLOAD_SIZE_MB = 15
MAX_IMAGE_SIZE_MB = 5


def _validate(file, allowed_extensions, max_size_mb):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Unsupported file type '{ext or 'unknown'}'. "
            f"Allowed types: {', '.join(allowed_extensions)}"
        )
    max_bytes = max_size_mb * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"File is too large. Maximum allowed size is {max_size_mb} MB.")


def validate_upload_file(file):
    """Use on any general attachment/document field (.pdf/.doc/.docx/.xls/.xlsx/.jpg/.jpeg/.png)."""
    _validate(file, ALL_UPLOAD_EXTENSIONS, MAX_UPLOAD_SIZE_MB)


def validate_image_file(file):
    """Use on image-only fields such as signatures/photos (.jpg/.jpeg/.png)."""
    _validate(file, IMAGE_EXTENSIONS, MAX_IMAGE_SIZE_MB)
