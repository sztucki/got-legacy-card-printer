import os
from pathlib import Path

MM_PER_INCH = 25.4

# Measured from reference-cards/example-card/1_Bonifer_ENG.tif (822x1122px @
# 300 DPI = 69.6x95.0mm) - a real printable card with correct bleed. Trim
# size assumes a standard 3mm bleed margin per side; update if a reference
# card without bleed becomes available to measure directly.
BLEED_SIZE_MM = (69.6, 95.0)  # width, height - card size including bleed
BLEED_MARGIN_MM = 3.0
TRIM_SIZE_MM = (
    BLEED_SIZE_MM[0] - 2 * BLEED_MARGIN_MM,
    BLEED_SIZE_MM[1] - 2 * BLEED_MARGIN_MM,
)

# Matches the reference card's own resolution.
TARGET_DPI = int(os.getenv("TARGET_DPI", "300"))


def mm_to_px(mm: float, dpi: int = TARGET_DPI) -> int:
    return round(mm / MM_PER_INCH * dpi)


TRIM_SIZE_PX = (mm_to_px(TRIM_SIZE_MM[0]), mm_to_px(TRIM_SIZE_MM[1]))
BLEED_SIZE_PX = (mm_to_px(BLEED_SIZE_MM[0]), mm_to_px(BLEED_SIZE_MM[1]))
BLEED_MARGIN_PX = mm_to_px(BLEED_MARGIN_MM)

JOBS_DIR = Path(os.getenv("JOBS_DIR", "./jobs")).resolve()

UPSCAYL_BIN_PATH = os.getenv("UPSCAYL_BIN_PATH")
UPSCAYL_MODELS_DIR = os.getenv("UPSCAYL_MODELS_DIR")
UPSCAYL_MODEL_NAME = os.getenv("UPSCAYL_MODEL_NAME", "upscayl-standard-4x")

# URL of a locally running IOPaint server (`iopaint start --model=...
# --device=...`) used for AI bleed outpainting. See backend/.env.example.
IOPAINT_API_URL = os.getenv("IOPAINT_API_URL", "http://127.0.0.1:8080")
