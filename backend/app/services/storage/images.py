import io

from PIL import Image, UnidentifiedImageError

from app.core import messages
from app.core.errors import ApiError, invalid

ACCEPTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
_EXTENSION_BY_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_MAX_PIXELS = 8000


def extension_for(mime_type: str) -> str:
    return _EXTENSION_BY_MIME.get(mime_type, "bin")


def validate_upload(content: bytes, mime_type: str, max_bytes: int) -> str:
    """
    Re-validates an upload server side.

    The browser already downscales before sending, but the client is not a
    trust boundary: MIME type, size and dimensions are all checked again here
    (spec §27). Returns the canonical file extension.
    """
    if mime_type not in ACCEPTED_MIME_TYPES:
        raise invalid(messages.UNSUPPORTED_IMAGE_TYPE)

    if len(content) > max_bytes:
        raise invalid(messages.IMAGE_TOO_LARGE)

    if not content:
        raise invalid(messages.INVALID_IMAGE)

    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
            detected = Image.MIME.get(image.format or "", "")
    except (UnidentifiedImageError, OSError) as error:
        raise invalid(messages.INVALID_IMAGE) from error

    # A .png that is really something else must not slip through on the
    # client-declared header alone.
    if detected not in ACCEPTED_MIME_TYPES:
        raise invalid(messages.UNSUPPORTED_IMAGE_TYPE)

    if width <= 0 or height <= 0 or width > _MAX_PIXELS or height > _MAX_PIXELS:
        raise invalid(messages.INVALID_IMAGE)

    return extension_for(detected)


def guard_storage_failure(error: Exception) -> ApiError:
    return ApiError("upload_failed", messages.UPLOAD_FAILED)
