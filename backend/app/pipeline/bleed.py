import base64
import io
import threading

import requests
from PIL import Image

from app.config import BLEED_MARGIN_MM, IOPAINT_API_URL, TRIM_SIZE_MM

PROMPT = (
    "Extend this trading card's existing artwork and border outward to fill "
    "the new margin, matching the existing art style, colors, and linework. "
    "Do not add any new text, symbols, or elements - purely continue what "
    "is already there."
)

REQUEST_TIMEOUT_SECONDS = 300

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


def generate_bleed(trim_image: Image.Image) -> Image.Image:
    """Outpaint a bleed margin around the trim image using a local IOPaint
    server (a Stable Diffusion inpainting model with built-in outpainting/
    'extender' support: given the original image and how far to extend on
    each side, IOPaint builds the expanded canvas and mask itself).

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

    # IOPaint's API requires a mask matching the input image's size, but it's
    # unused when use_extender=True (the server builds its own expansion
    # mask internally) - any correctly-sized placeholder works.
    dummy_mask = Image.new("L", (width, height), 0)

    payload = {
        "image": _to_base64_png(trim_rgb),
        "mask": _to_base64_png(dummy_mask),
        "prompt": PROMPT,
        "use_extender": True,
        "extender_x": -margin,
        "extender_y": -margin,
        "extender_width": width + 2 * margin,
        "extender_height": height + 2 * margin,
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

    return Image.open(io.BytesIO(response.content)).convert("RGB")
