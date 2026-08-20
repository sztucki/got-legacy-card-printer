import base64
import io
import threading

import requests
from PIL import Image, ImageFilter

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
# How closely the generated margin should stick to the replicated source
# pixels vs. fully hallucinate new content (1.0 = ignore them entirely).
# IOPaint's built-in use_extender mode hard-codes this to 1.0, which was
# producing wild, unrelated content (jagged/green noise) over plain regions
# like a card's solid-color footer bar - building the padded canvas and mask
# ourselves (below) lets us set this lower instead.
SD_STRENGTH = 0.85
# IOPaint defaults to seed 42 when none is given. That happened to produce a
# visible seam artifact in the leather-texture border on one test card - a
# diffusion model's output is seed-sensitive, and 42 wasn't a good roll for
# that specific input. 123 tested clean on the same case; not a permanent
# fix (still just one fixed seed, so another input could hit a bad roll of
# its own) but a better default for now.
SD_SEED = 123

# A card's credit-line text (illustrator, copyright, card number) typically
# sits right at the trim's bottom edge. A wide seam blur there lets those
# real text pixels influence the generation, and the diffusion model
# continues them into the new margin as garbled pseudo-text - confirmed by
# comparing generations of the same input across several seeds (see
# test-outputs/seed-diag/).
#
# IOPaint's own sd_mask_blur only affects one place: its optional final
# alpha-blend step (result*mask + original*(1-mask), gated by
# sd_keep_unmasked_area) - per its source (iopaint/model/base.py's
# _pad_forward), the mask handed to the *diffusion model itself* is always
# the hard, unblurred one, and it also thresholds any mask we send to binary
# before that blend (iopaint/api.py's api_inpaint), so baking a blur
# gradient into the mask pixels we upload has no effect either. So instead
# of relying on IOPaint's own blend, generate_bleed() requests a raw,
# unblended generation (sd_keep_unmasked_area=False) and does this blend
# itself in Python, with a smaller blur radius near text_edge than the
# other edges.
SD_MASK_BLUR_TEXT_EDGE = 3
TEXT_EDGE = "bottom"

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


def _replicate_pad(image: Image.Image, margin: int) -> Image.Image:
    """Pad image on all sides by margin px, replicating edge pixels (like
    cv2.BORDER_REPLICATE) - gives the model a same-color starting point to
    denoise from rather than an arbitrary fill. Pure PIL, no numpy: a 1px
    edge strip resized with NEAREST to the margin's thickness repeats each
    edge pixel exactly, which is what edge-replication is."""
    width, height = image.size
    padded = Image.new("RGB", (width + 2 * margin, height + 2 * margin))
    padded.paste(image, (margin, margin))

    top = image.crop((0, 0, width, 1)).resize((width, margin), Image.NEAREST)
    bottom = image.crop((0, height - 1, width, height)).resize((width, margin), Image.NEAREST)
    left = image.crop((0, 0, 1, height)).resize((margin, height), Image.NEAREST)
    right = image.crop((width - 1, 0, width, height)).resize((margin, height), Image.NEAREST)
    padded.paste(top, (margin, 0))
    padded.paste(bottom, (margin, margin + height))
    padded.paste(left, (0, margin))
    padded.paste(right, (margin + width, margin))

    tl = image.crop((0, 0, 1, 1)).resize((margin, margin), Image.NEAREST)
    tr = image.crop((width - 1, 0, width, 1)).resize((margin, margin), Image.NEAREST)
    bl = image.crop((0, height - 1, 1, height)).resize((margin, margin), Image.NEAREST)
    br = image.crop((width - 1, height - 1, width, height)).resize((margin, margin), Image.NEAREST)
    padded.paste(tl, (0, 0))
    padded.paste(tr, (margin + width, 0))
    padded.paste(bl, (0, margin + height))
    padded.paste(br, (margin + width, margin + height))

    return padded


def _blur_mask_per_edge(
    mask: Image.Image,
    *,
    generation_margin: int,
    trim_size: tuple,
    sd_mask_blur: int,
    sd_mask_blur_text_edge: int,
    text_edge: str,
) -> Image.Image:
    """Blur the binary protect/generate mask ourselves, using a smaller
    radius near text_edge than everywhere else, for use as our own
    alpha-blend mask (see SD_MASK_BLUR_TEXT_EDGE's module docstring for why
    this has to happen on our side rather than via IOPaint's sd_mask_blur)."""
    if not text_edge or sd_mask_blur_text_edge == sd_mask_blur:
        return mask.filter(ImageFilter.GaussianBlur(sd_mask_blur)) if sd_mask_blur else mask

    wide_blur = mask.filter(ImageFilter.GaussianBlur(sd_mask_blur)) if sd_mask_blur else mask
    sharp_blur = (
        mask.filter(ImageFilter.GaussianBlur(sd_mask_blur_text_edge))
        if sd_mask_blur_text_edge
        else mask
    )

    trim_width, trim_height = trim_size
    padded_width, padded_height = mask.size
    # Wide enough to fully cover both blur radii's transition zone around
    # the seam, however either was configured.
    buffer_px = max(1, 4 * max(sd_mask_blur, sd_mask_blur_text_edge))

    if text_edge == "bottom":
        seam = generation_margin + trim_height
        band_box = (0, max(0, seam - buffer_px), padded_width, min(padded_height, seam + buffer_px))
    elif text_edge == "top":
        seam = generation_margin
        band_box = (0, max(0, seam - buffer_px), padded_width, min(padded_height, seam + buffer_px))
    elif text_edge == "left":
        seam = generation_margin
        band_box = (max(0, seam - buffer_px), 0, min(padded_width, seam + buffer_px), padded_height)
    elif text_edge == "right":
        seam = generation_margin + trim_width
        band_box = (max(0, seam - buffer_px), 0, min(padded_width, seam + buffer_px), padded_height)
    else:
        raise ValueError(f"Unknown text_edge: {text_edge!r} (expected top/bottom/left/right)")

    blurred = wide_blur.copy()
    blurred.paste(sharp_blur.crop(band_box), band_box[:2])
    return blurred


def _iopaint_inpaint(
    image: Image.Image,
    mask: Image.Image,
    *,
    prompt: str,
    negative_prompt: str,
    sd_steps: int,
    sd_guidance_scale: float,
    sd_strength: float,
    sd_seed: int,
) -> Image.Image:
    """POST one image+mask to IOPaint's plain inpaint endpoint and return the
    raw generated result (same size as the input, unblended - the caller
    does its own mask alpha-blend against the source image; see
    SD_MASK_BLUR_TEXT_EDGE's module docstring for why)."""
    payload = {
        "image": _to_base64_png(image),
        "mask": _to_base64_png(mask),
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "sd_steps": sd_steps,
        "sd_guidance_scale": sd_guidance_scale,
        # We do our own blur/blend in Python afterward (see
        # SD_MASK_BLUR_TEXT_EDGE) - IOPaint's own sd_mask_blur only affects
        # its own blend step, so it's moot when sd_keep_unmasked_area=False.
        "sd_mask_blur": 0,
        "sd_strength": sd_strength,
        "sd_seed": sd_seed,
        "sd_keep_unmasked_area": False,
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


def generate_bleed(
    trim_image: Image.Image,
    *,
    prompt: str = PROMPT,
    negative_prompt: str = NEGATIVE_PROMPT,
    sd_steps: int = SD_STEPS,
    sd_guidance_scale: float = SD_GUIDANCE_SCALE,
    sd_mask_blur: int = SD_MASK_BLUR,
    sd_mask_blur_text_edge: int = SD_MASK_BLUR_TEXT_EDGE,
    text_edge: str = TEXT_EDGE,
    sd_strength: float = SD_STRENGTH,
    sd_seed: int = SD_SEED,
    generation_overshoot: float = GENERATION_OVERSHOOT,
) -> Image.Image:
    """Outpaint a bleed margin around the trim image using a local IOPaint
    server (a Stable Diffusion inpainting model).

    Builds the expanded canvas and mask ourselves (edge-replicate padding +
    a mask covering just the new margin) and calls IOPaint's plain inpaint
    endpoint, rather than its use_extender mode - that mode hard-codes
    sd_strength=1.0 (full regeneration from noise, no anchor to the source
    pixels), which produced wild, unrelated content over plain regions like
    a card's solid-color footer bar. Doing it ourselves lets sd_strength
    stay tunable.

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

    padded = _replicate_pad(trim_rgb, generation_margin)
    mask = Image.new("L", padded.size, 255)
    mask.paste(Image.new("L", (width, height), 0), (generation_margin, generation_margin))

    raw_generated = _iopaint_inpaint(
        padded,
        mask,
        prompt=prompt,
        negative_prompt=negative_prompt,
        sd_steps=sd_steps,
        sd_guidance_scale=sd_guidance_scale,
        sd_strength=sd_strength,
        sd_seed=sd_seed,
    )

    # Blend the raw generation back onto the original padded canvas
    # ourselves, using a mask blurred with a smaller radius near text_edge
    # than the other edges - see SD_MASK_BLUR_TEXT_EDGE's module docstring
    # for why this can't be delegated to IOPaint's own sd_mask_blur/
    # sd_keep_unmasked_area.
    alpha = _blur_mask_per_edge(
        mask,
        generation_margin=generation_margin,
        trim_size=(width, height),
        sd_mask_blur=sd_mask_blur,
        sd_mask_blur_text_edge=sd_mask_blur_text_edge,
        text_edge=text_edge,
    )
    generated = Image.composite(raw_generated, padded, alpha)

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
