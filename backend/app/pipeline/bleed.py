import base64
import io

from openai import OpenAI
from PIL import Image

from app.config import BLEED_MARGIN_PX, BLEED_SIZE_PX, OPENAI_API_KEY

PROMPT = (
    "Extend this trading card's existing artwork and border outward to fill "
    "the transparent margin, matching the existing art style, colors, and "
    "linework. Do not add any new text, symbols, or elements - purely "
    "continue what is already there."
)


class OpenAINotConfiguredError(RuntimeError):
    pass


def _compose_canvas(trim_image: Image.Image) -> Image.Image:
    """Center the trim image on a transparent canvas sized to the bleed dimensions."""
    canvas = Image.new("RGBA", BLEED_SIZE_PX, (0, 0, 0, 0))
    resized = trim_image.convert("RGBA").resize(
        (BLEED_SIZE_PX[0] - 2 * BLEED_MARGIN_PX, BLEED_SIZE_PX[1] - 2 * BLEED_MARGIN_PX)
    )
    canvas.paste(resized, (BLEED_MARGIN_PX, BLEED_MARGIN_PX))
    return canvas


def _build_mask(canvas: Image.Image) -> Image.Image:
    """Build an edit mask per OpenAI's convention: transparent pixels are
    edited, opaque pixels are preserved. So the border ring (to be
    outpainted) stays transparent, and the trim area (to be protected) is
    painted opaque white."""
    mask = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    protected = Image.new(
        "RGBA",
        (canvas.width - 2 * BLEED_MARGIN_PX, canvas.height - 2 * BLEED_MARGIN_PX),
        (255, 255, 255, 255),
    )
    mask.paste(protected, (BLEED_MARGIN_PX, BLEED_MARGIN_PX))
    return mask


def _to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def generate_bleed(trim_image: Image.Image) -> Image.Image:
    if not OPENAI_API_KEY:
        raise OpenAINotConfiguredError(
            "OPENAI_API_KEY is not set (see backend/.env.example)."
        )

    canvas = _compose_canvas(trim_image)
    mask = _build_mask(canvas)

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.edit(
        model="gpt-image-1",
        image=_to_png_bytes(canvas),
        mask=_to_png_bytes(mask),
        prompt=PROMPT,
        size=f"{BLEED_SIZE_PX[0]}x{BLEED_SIZE_PX[1]}",
    )

    image_bytes = io.BytesIO(base64.b64decode(response.data[0].b64_json))
    return Image.open(image_bytes).convert("RGB")
