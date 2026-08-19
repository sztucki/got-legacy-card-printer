import base64
import io
import threading

import requests
from PIL import Image

from app.config import BLEED_MARGIN_MM, IOPAINT_API_URL, TRIM_SIZE_MM

PROMPT = (
    "Extend this trading card's existing artwork, border, and frame pattern "
    "outward to fill the new margin, continuing the same texture, colors, "
    "and linework as if the art originally extended this far - especially "
    "any border/frame decoration, not just the background. Do not add any "
    "new text, symbols, or objects - purely continue what is already there."
)
NEGATIVE_PROMPT = (
    "blank space, empty area, solid color, plain background, white border, "
    "blurry, low detail, text, watermark"
)

REQUEST_TIMEOUT_SECONDS = 300

# How far past the actual bleed margin to generate before cropping back down
# to it - gives the diffusion model room to work with so the kept edge isn't
# the noisy outer boundary of its own generation.
GENERATION_OVERSHOOT = 1.5

SD_STEPS = 50
SD_GUIDANCE_SCALE = 7.5
# Blend width (px) at the seam between original and generated pixels - kept
# as an explicit constant (independent of IOPaint's own default) so it stays
# sensible as the margin size changes.
SD_MASK_BLUR = 12

# Stable Diffusion on Apple's MPS backend cannot safely run two overlapping
# generations - concurrent requests have been observed to crash the IOPaint
# server outright (Metal command encoder assertion failure). Jobs run in a
# threadpool, so this serializes all outpainting calls within this process.
_iopaint_lock = threading.Lock()


class IOPaintNotAvailableError(RuntimeError):
    pass


def _to_base64_png(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def generate_bleed(
    trim_image: Image.Image,
    *,
    prompt: str = PROMPT,
    negative_prompt: str = NEGATIVE_PROMPT,
    sd_steps: int = SD_STEPS,
    sd_guidance_scale: float = SD_GUIDANCE_SCALE,
    sd_mask_blur: int = SD_MASK_BLUR,
    generation_overshoot: float = GENERATION_OVERSHOOT,
) -> Image.Image:
    """Outpaint a bleed margin around the trim image using a local IOPaint
    server (a Stable Diffusion inpainting model with built-in outpainting/
    'extender' support: given the original image and how far to extend on
    each side, IOPaint builds the expanded canvas and mask itself).

    Keyword args override the module-level defaults above without editing
    this file - used by backend/scripts/tune_bleed.py to compare variants.

    Requires a local IOPaint server already running, e.g.:
      iopaint start --model=runwayml/stable-diffusion-inpainting --device=mps
    See backend/.env.example.
    """
    trim_rgb = trim_image.convert("RGB")
    width, height = trim_rgb.size

    # normalize.py already crops to the exact trim aspect ratio, so mm-per-px
    # is consistent across both axes - a single margin fraction (from mm)
    # applies cleanly to this image's actual pixel width.
    margin_fraction = BLEED_MARGIN_MM / TRIM_SIZE_MM[0]
    margin = max(1, round(width * margin_fraction))
    generation_margin = max(margin, round(margin * generation_overshoot))

    # IOPaint's API requires a mask matching the input image's size, but it's
    # unused when use_extender=True (the server builds its own expansion
    # mask internally) - any correctly-sized placeholder works.
    dummy_mask = Image.new("L", (width, height), 0)

    payload = {
        "image": _to_base64_png(trim_rgb),
        "mask": _to_base64_png(dummy_mask),
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "use_extender": True,
        "extender_x": -generation_margin,
        "extender_y": -generation_margin,
        "extender_width": width + 2 * generation_margin,
        "extender_height": height + 2 * generation_margin,
        "sd_steps": sd_steps,
        "sd_guidance_scale": sd_guidance_scale,
        "sd_mask_blur": sd_mask_blur,
    }

    try:
        with _iopaint_lock:
            response = requests.post(
                f"{IOPAINT_API_URL}/api/v1/inpaint",
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
    except requests.ConnectionError as exc:
        raise IOPaintNotAvailableError(
            f"Couldn't reach the local IOPaint server at {IOPAINT_API_URL}. "
            "Start it first, e.g.: iopaint start "
            "--model=runwayml/stable-diffusion-inpainting --device=mps "
            "(see backend/.env.example)."
        ) from exc
    except requests.Timeout as exc:
        raise IOPaintNotAvailableError(
            f"IOPaint server at {IOPAINT_API_URL} didn't respond within "
            f"{REQUEST_TIMEOUT_SECONDS}s. Outpainting can be slow on CPU-only "
            "setups - try a GPU device (--device=mps/cuda), a lighter model, "
            "or raise REQUEST_TIMEOUT_SECONDS."
        ) from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"IOPaint request failed ({response.status_code}): {response.text}"
        )

    generated = Image.open(io.BytesIO(response.content)).convert("RGB")

    # Crop back down from the overshoot margin to the actual bleed margin,
    # keeping the clean center of the generation and discarding its noisier
    # outer edge.
    trim_offset = generation_margin - margin
    crop_box = (
        trim_offset,
        trim_offset,
        trim_offset + width + 2 * margin,
        trim_offset + height + 2 * margin,
    )
    return generated.crop(crop_box)
