from typing import Optional

from PIL import Image

from app.config import TRIM_SIZE_PX


def orient(image: Image.Image, rotate_override: Optional[bool] = None) -> Image.Image:
    """Normalize the card to the correct side (orientation).

    If `rotate_override` is given (True/False), that decision is used as-is -
    this lets the caller override the heuristic when it gets it wrong.
    Otherwise, rotate 90 degrees if that better matches the target trim
    aspect ratio than the image's current orientation.
    """
    if rotate_override is True:
        return image.rotate(-90, expand=True)
    if rotate_override is False:
        return image

    target_ratio = TRIM_SIZE_PX[0] / TRIM_SIZE_PX[1]
    current_ratio = image.width / image.height
    rotated_ratio = image.height / image.width

    if abs(rotated_ratio - target_ratio) < abs(current_ratio - target_ratio):
        return image.rotate(-90, expand=True)
    return image
