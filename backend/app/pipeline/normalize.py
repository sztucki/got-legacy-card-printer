from PIL import Image

from app.config import TRIM_SIZE_PX


def normalize(image: Image.Image) -> Image.Image:
    """Center-crop the image to the trim aspect ratio."""
    target_ratio = TRIM_SIZE_PX[0] / TRIM_SIZE_PX[1]
    current_ratio = image.width / image.height

    if current_ratio > target_ratio:
        new_width = round(image.height * target_ratio)
        left = (image.width - new_width) // 2
        box = (left, 0, left + new_width, image.height)
    else:
        new_height = round(image.width / target_ratio)
        top = (image.height - new_height) // 2
        box = (0, top, image.width, top + new_height)

    return image.crop(box)
