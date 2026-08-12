import base64
import io

from openai import OpenAI
from PIL import Image

from app.config import GPT_IMAGE_BLEED_MARGIN_PX, GPT_IMAGE_GENERATION_SIZE_PX, OPENAI_API_KEY

PROMPT = (
    "Extend this trading card's existing artwork and border outward to fill "
    "the transparent margin, matching the existing art style, colors, and "
    "linework. Do not add any new text, symbols, or elements - purely "
    "continue what is already there."
)


class OpenAINotConfiguredError(RuntimeError):
    pass


def _compose_canvas(trim_image: Image.Image) -> Image.Image:
    """Center the trim image on a transparent canvas sized to gpt-image-1's
    generation size (the trim is downsampled to fit - this step is about
    generating plausible bleed content, not final resolution)."""
    canvas = Image.new("RGBA", GPT_IMAGE_GENERATION_SIZE_PX, (0, 0, 0, 0))
    inner_size = (
        GPT_IMAGE_GENERATION_SIZE_PX[0] - 2 * GPT_IMAGE_BLEED_MARGIN_PX,
        GPT_IMAGE_GENERATION_SIZE_PX[1] - 2 * GPT_IMAGE_BLEED_MARGIN_PX,
    )
    resized = trim_image.convert("RGBA").resize(inner_size)
    canvas.paste(resized, (GPT_IMAGE_BLEED_MARGIN_PX, GPT_IMAGE_BLEED_MARGIN_PX))
    return canvas


def _build_mask(canvas: Image.Image) -> Image.Image:
    """Build an edit mask per OpenAI's convention: transparent pixels are
    edited, opaque pixels are preserved. So the border ring (to be
    outpainted) stays transparent, and the trim area (to be protected) is
    painted opaque white."""
    mask = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    protected = Image.new(
        "RGBA",
        (
            canvas.width - 2 * GPT_IMAGE_BLEED_MARGIN_PX,
            canvas.height - 2 * GPT_IMAGE_BLEED_MARGIN_PX,
        ),
        (255, 255, 255, 255),
    )
    mask.paste(protected, (GPT_IMAGE_BLEED_MARGIN_PX, GPT_IMAGE_BLEED_MARGIN_PX))
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
    """Generate a trim+bleed image at gpt-image-1's fixed generation size.

    The result is NOT at final print resolution - the caller is expected to
    upscale the whole returned image afterwards to reach the true target
    pixel dimensions, since gpt-image-1 can't generate at print DPI directly.
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
    return Image.open(image_bytes).convert("RGB")
