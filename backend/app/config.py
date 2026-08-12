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

# gpt-image-1's images.edit endpoint only accepts a fixed set of output
# sizes (its aspect ratio doesn't match the card's), so generation happens
# on this canvas, but only a centered sub-rectangle matching the card's true
# aspect ratio is actually used - the rest is letterboxing that gets cropped
# away after generation. This avoids stretching the card art to a different
# aspect ratio at either the compose or the final-resize step.
GPT_IMAGE_GENERATION_SIZE_PX = (1024, 1536)

_target_aspect = BLEED_SIZE_PX[0] / BLEED_SIZE_PX[1]
_gen_w, _gen_h = GPT_IMAGE_GENERATION_SIZE_PX
if _gen_w / _gen_h > _target_aspect:
    _work_h = _gen_h
    _work_w = round(_gen_h * _target_aspect)
else:
    _work_w = _gen_w
    _work_h = round(_gen_w / _target_aspect)

# The sub-rectangle of the generation canvas whose aspect ratio matches
# BLEED_SIZE_PX, and its centered offset within that canvas.
GPT_IMAGE_WORK_SIZE_PX = (_work_w, _work_h)
GPT_IMAGE_WORK_OFFSET_PX = ((_gen_w - _work_w) // 2, (_gen_h - _work_h) // 2)
GPT_IMAGE_BLEED_MARGIN_PX = round(BLEED_MARGIN_PX * _work_w / BLEED_SIZE_PX[0])

JOBS_DIR = Path(os.getenv("JOBS_DIR", "./jobs")).resolve()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UPSCAYL_BIN_PATH = os.getenv("UPSCAYL_BIN_PATH")
UPSCAYL_MODELS_DIR = os.getenv("UPSCAYL_MODELS_DIR")
UPSCAYL_MODEL_NAME = os.getenv("UPSCAYL_MODEL_NAME", "upscayl-standard-4x")
