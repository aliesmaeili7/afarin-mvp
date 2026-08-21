"""9:16-master → 4:5 crop helpers.

Used only by evaluation. Production still generates dedicated 4:5 and 9:16
frames (`image_compose_strategy` is unused).
"""

from PIL import Image

MASTER_NOTE = (
    "compose as a 9:16 master with the subject locked in a central 4:5-safe "
    "region so a vertical center crop becomes a feed still; leave the bottom "
    "of that 4:5 region empty for later typography; Story uses the full frame"
)


def central_4x5_crop(image: Image.Image) -> Image.Image:
    """Feed crop from a 9:16 master: full width, vertically centered 4:5 window."""
    width, height = image.size
    target_height = int(round(width * 5 / 4))
    if target_height <= height:
        top = max(0, (height - target_height) // 2)
        return image.crop((0, top, width, top + target_height))
    target_width = int(round(height * 4 / 5))
    left = max(0, (width - target_width) // 2)
    return image.crop((left, 0, left + target_width, height))
