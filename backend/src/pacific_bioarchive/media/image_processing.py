"""Aspect-ratio-preserving compressed image thumbnails."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .validation import MediaValidationError


@dataclass(frozen=True, slots=True)
class ThumbnailResult:
    data: bytes
    width: int
    height: int
    content_type: str = "image/jpeg"
    extension: str = ".jpg"


def build_thumbnail(
    source: bytes | bytearray | str | Path,
    *,
    max_width: int = 320,
    max_height: int = 320,
    quality: int = 78,
) -> ThumbnailResult:
    if max_width < 1 or max_height < 1:
        raise ValueError("Thumbnail dimensions must be positive")
    if not 1 <= quality <= 95:
        raise ValueError("JPEG quality must be between 1 and 95")
    input_value: BytesIO | Path
    if isinstance(source, (bytes, bytearray)):
        input_value = BytesIO(bytes(source))
    else:
        input_value = Path(source)
    try:
        with Image.open(input_value) as opened:
            image = ImageOps.exif_transpose(opened)
            image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise MediaValidationError("INVALID_IMAGE", "The uploaded image cannot be decoded") from exc

    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")

    output = BytesIO()
    image.save(
        output,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
        subsampling=2,
    )
    return ThumbnailResult(
        data=output.getvalue(),
        width=image.width,
        height=image.height,
    )

