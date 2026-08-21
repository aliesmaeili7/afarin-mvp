"""Crop math for the 9:16-master evaluation script. No production generate path."""

from PIL import Image

from app.services.campaigns.master_crop import central_4x5_crop


def test_central_4x5_crop_from_9x16() -> None:
    image = Image.new("RGB", (1080, 1920), (10, 20, 30))
    cropped = central_4x5_crop(image)
    assert cropped.size == (1080, 1350)
    # Vertically centered: (1920 - 1350) / 2 = 285.
    assert cropped.getpixel((0, 0)) == (10, 20, 30)


def test_central_4x5_crop_already_4x5() -> None:
    image = Image.new("RGB", (1080, 1350), (1, 2, 3))
    cropped = central_4x5_crop(image)
    assert cropped.size == (1080, 1350)
