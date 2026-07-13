"""
apps/core/validators.py
─────────────────────────
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.template.defaultfilters import filesizeformat

# Deliberately generous but bounded — covers everything MediaAsset.FileType
# lists (image/video/document/audio) without allowing arbitrary executables.
ALLOWED_MEDIA_EXTENSIONS = [
    "jpg", "jpeg", "png", "gif", "webp", "svg",
    "mp4", "webm", "mov",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "mp3", "wav", "ogg",
]

MAX_MEDIA_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def validate_media_file_size(file) -> None:
    if file.size > MAX_MEDIA_UPLOAD_SIZE_BYTES:
        raise ValidationError(
            f"File too large ({filesizeformat(file.size)}). "
            f"Maximum size is {filesizeformat(MAX_MEDIA_UPLOAD_SIZE_BYTES)}."
        )


validate_media_file_extension = FileExtensionValidator(allowed_extensions=ALLOWED_MEDIA_EXTENSIONS)
