import os
from pathlib import Path

MM_PER_INCH = 25.4

# Standard trading card sizes. Update these once real reference cards
# (dropped into ../reference-cards/) confirm the actual target dimensions.
TRIM_SIZE_MM = (63.0, 88.0)  # width, height - card size without bleed
BLEED_SIZE_MM = (69.0, 94.5)  # width, height - card size including bleed
BLEED_MARGIN_MM = (BLEED_SIZE_MM[0] - TRIM_SIZE_MM[0]) / 2

TARGET_DPI = int(os.getenv("TARGET_DPI", "600"))


def mm_to_px(mm: float, dpi: int = TARGET_DPI) -> int:
    return round(mm / MM_PER_INCH * dpi)


TRIM_SIZE_PX = (mm_to_px(TRIM_SIZE_MM[0]), mm_to_px(TRIM_SIZE_MM[1]))
BLEED_SIZE_PX = (mm_to_px(BLEED_SIZE_MM[0]), mm_to_px(BLEED_SIZE_MM[1]))
BLEED_MARGIN_PX = mm_to_px(BLEED_MARGIN_MM)

JOBS_DIR = Path(os.getenv("JOBS_DIR", "./jobs")).resolve()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UPSCAYL_BIN_PATH = os.getenv("UPSCAYL_BIN_PATH")
