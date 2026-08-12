import base64
import io

from openai import OpenAI
from PIL import Image

from app.config import (
    GPT_IMAGE_BLEED_MARGIN_PX,
    GPT_IMAGE_GENERATION_SIZE_PX,
    GPT_IMAGE_WORK_OFFSET_PX,
    GPT_IMAGE_WORK_SIZE_PX,
    OPENAI_API_KEY,
)

PROMPT = (
    "Extend this trading card's existing artwork and border outward to fill "
    "the transparent margin, matching the existing art style, colors, and "
    "linework. Do not add any new text, symbols, or elements - purely "
    "continue what is already there."
)


class OpenAINotConfiguredError(RuntimeError):
    pass


def _work_rect() -> tuple:
    x, y = GPT_IMAGE_WORK_OFFSET_PX
    w, h = GPT_IMAGE_WORK_SIZE_PX
    return (x, y, x + w, y + h)


def _compose_canvas(trim_image: Image.Image) -> Image.Image:
    """Place the trim image, centered with the correct bleed margin, inside
    the work rectangle - itself centered on gpt-image-1's fixed generation
    canvas. The work rectangle's aspect ratio matches the card's true aspect
    ratio (unlike the full generation canvas), so no stretching occurs."""
    canvas = Image.new("RGBA", GPT_IMAGE_GENERATION_SIZE_PX, (0, 0, 0, 0))
    work_x, work_y = GPT_IMAGE_WORK_OFFSET_PX
    work_w, work_h = GPT_IMAGE_WORK_SIZE_PX
    inner_size = (
        work_w - 2 * GPT_IMAGE_BLEED_MARGIN_PX,
        work_h - 2 * GPT_IMAGE_BLEED_MARGIN_PX,
    )
    resized = trim_image.convert("RGBA").resize(inner_size)
    canvas.paste(
        resized, (work_x + GPT_IMAGE_BLEED_MARGIN_PX, work_y + GPT_IMAGE_BLEED_MARGIN_PX)
    )
    return canvas


def _build_mask(canvas: Image.Image) -> Image.Image:
    """Build an edit mask per OpenAI's convention: transparent pixels are
    edited, opaque pixels are preserved. So everywhere outside the trim
    (including the generation canvas's letterbox margin, which gets
    discarded after generation) stays transparent/editable, and the trim
    area is painted opaque white to protect it."""
    work_x, work_y = GPT_IMAGE_WORK_OFFSET_PX
    work_w, work_h = GPT_IMAGE_WORK_SIZE_PX
    mask = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    protected = Image.new(
        "RGBA",
        (
            work_w - 2 * GPT_IMAGE_BLEED_MARGIN_PX,
            work_h - 2 * GPT_IMAGE_BLEED_MARGIN_PX,
        ),
        (255, 255, 255, 255),
    )
    mask.paste(
        protected, (work_x + GPT_IMAGE_BLEED_MARGIN_PX, work_y + GPT_IMAGE_BLEED_MARGIN_PX)
    )
    return mask


def _to_png_file(image: Image.Image, name: str) -> tuple:
    """Return a (filename, bytes, mimetype) tuple - the OpenAI SDK needs an
    explicit mimetype here, since raw bytes get sent as
    application/octet-stream and rejected by the images edit endpoint."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return (name, buf.read(), "image/png")


def generate_bleed(trim_image: Image.Image) -> Image.Image:
    """Generate a trim+bleed image at the card's true aspect ratio.

    The result is sized GPT_IMAGE_WORK_SIZE_PX, not final print resolution -
    the caller is expected to scale the whole returned image afterwards to
    reach the true target pixel dimensions, since gpt-image-1 can't generate
    at print DPI directly.
    """
    if not OPENAI_API_KEY:
        raise OpenAINotConfiguredError(
            "OPENAI_API_KEY is not set (see backend/.env.example)."
        )

    canvas = _compose_canvas(trim_image)
    mask = _build_mask(canvas)

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.edit(
        model="gpt-image-1",
        image=_to_png_file(canvas, "canvas.png"),
        mask=_to_png_file(mask, "mask.png"),
        prompt=PROMPT,
        size=f"{GPT_IMAGE_GENERATION_SIZE_PX[0]}x{GPT_IMAGE_GENERATION_SIZE_PX[1]}",
    )

    image_bytes = io.BytesIO(base64.b64decode(response.data[0].b64_json))
    generated = Image.open(image_bytes).convert("RGB")
    return generated.crop(_work_rect())
