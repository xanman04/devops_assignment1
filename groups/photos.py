"""Decode bounded uploads and create small metadata-free group photos."""
from io import BytesIO
from pathlib import Path
import warnings

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_EDGE = 1600


def prepare_photo(upload):
    if Path(upload.name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValidationError("Use a JPG, PNG, or WebP photo.")
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Photos must be at most 5 MiB.")
    upload.seek(0)
    raw = upload.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValidationError("Photos must be at most 5 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > MAX_PIXELS:
                    raise ValidationError("Unsupported image or photo exceeds 20 megapixels.")
                if getattr(image, "is_animated", False):
                    raise ValidationError("Use a still photo, not an animated image.")
                image.verify()
            with Image.open(BytesIO(raw)) as image:
                oriented = ImageOps.exif_transpose(image)
                oriented.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
                # New pixel buffer strips EXIF, comments, GPS and other input metadata.
                rgba = oriented.convert("RGBA")
                clean = Image.new("RGB", rgba.size, "white")
                clean.paste(rgba, mask=rgba.getchannel("A"))
                output = BytesIO()
                clean.save(output, format="JPEG", quality=85, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("This file cannot be decoded as a supported photo.")
    return ContentFile(output.getvalue(), name="photo.jpg")
