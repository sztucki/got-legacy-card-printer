import random
import shutil
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from app import jobs
from app.config import BLEED_SIZE_PX, TRIM_SIZE_PX, UPSCAYL_MODEL_NAME
from app.jobs import JobStatus
from app.pipeline.bleed import SD_MASK_BLUR, SD_STRENGTH, generate_bleed
from app.pipeline.clean_text import remove_footer_band
from app.pipeline.normalize import normalize
from app.pipeline.orient import orient
from app.pipeline.upscale import upscale

DEFAULT_FOOTER_HEIGHT_FRACTION = 0.08


def _clean_footer(
    job_id: str, upscaled_path: Path, remove_footer_text: bool, footer_height_fraction: float
) -> Image.Image:
    cleaned_path = jobs.stage_path(job_id, "cleaned")
    if remove_footer_text:
        cleaned = remove_footer_band(Image.open(upscaled_path), footer_height_fraction)
        cleaned.save(cleaned_path)
    else:
        # Nothing to change - copy the file rather than decode+re-encode a
        # duplicate PNG of identical pixel data.
        shutil.copyfile(upscaled_path, cleaned_path)
        cleaned = Image.open(cleaned_path)
    jobs.mark_stage_complete(job_id, "cleaned")
    return cleaned


def _generate_and_save_bleed(
    job_id: str,
    cleaned: Image.Image,
    sd_strength: Optional[float],
    sd_mask_blur: Optional[int],
    sd_seed: int,
) -> Tuple[float, int]:
    """Generates and saves the bleed stage. Returns the strength/mask_blur
    actually used (module defaults if the caller didn't override them), so
    callers can record what was really applied rather than a possibly-None
    override that only means something in light of generate_bleed()'s
    current defaults."""
    resolved_strength = sd_strength if sd_strength is not None else SD_STRENGTH
    resolved_mask_blur = sd_mask_blur if sd_mask_blur is not None else SD_MASK_BLUR

    bled = generate_bleed(cleaned, sd_strength=resolved_strength, sd_mask_blur=resolved_mask_blur, sd_seed=sd_seed)
    if bled.size != BLEED_SIZE_PX:
        bled = bled.resize(BLEED_SIZE_PX, Image.LANCZOS)
    bled.save(jobs.stage_path(job_id, "bleed"))
    jobs.mark_stage_complete(job_id, "bleed")
    return resolved_strength, resolved_mask_blur


def _finish_bleed_generation(
    job_id: str,
    cleaned: Image.Image,
    resolved_upscale_model: Optional[str],
    remove_footer_text: bool,
    footer_height_fraction: float,
    sd_strength: Optional[float],
    sd_mask_blur: Optional[int],
    sd_seed: Optional[int],
) -> None:
    """Shared tail of run_pipeline and regenerate_bleed_stage once each has
    its own cleaned image and resolved upscale model ready: generate the
    bleed, record what was actually used, mark the job complete."""
    # A blank seed means "random" on both the upload form and the regenerate
    # panel (they share the same BleedTuningFields component and copy).
    seed = sd_seed if sd_seed is not None else random.randint(0, 2**31 - 1)
    resolved_strength, resolved_mask_blur = _generate_and_save_bleed(job_id, cleaned, sd_strength, sd_mask_blur, seed)

    jobs.set_params(
        job_id,
        {
            "upscale_model": resolved_upscale_model,
            "remove_footer_text": remove_footer_text,
            "footer_height_fraction": footer_height_fraction,
            "sd_strength": resolved_strength,
            "sd_mask_blur": resolved_mask_blur,
        },
    )
    jobs.set_status(job_id, JobStatus.COMPLETE)


def run_pipeline(
    job_id: str,
    rotate_override: Optional[bool] = None,
    upscale_model: Optional[str] = None,
    remove_footer_text: bool = True,
    footer_height_fraction: float = DEFAULT_FOOTER_HEIGHT_FRACTION,
    sd_strength: Optional[float] = None,
    sd_mask_blur: Optional[int] = None,
    sd_seed: Optional[int] = None,
) -> None:
    try:
        jobs.set_status(job_id, JobStatus.PROCESSING)

        original = Image.open(jobs.stage_path(job_id, "original"))

        oriented = orient(original, rotate_override=rotate_override)
        oriented.save(jobs.stage_path(job_id, "oriented"))
        jobs.mark_stage_complete(job_id, "oriented")

        normalized = normalize(oriented)
        normalized.save(jobs.stage_path(job_id, "normalized"))
        jobs.mark_stage_complete(job_id, "normalized")

        # Upscale the trim art to full print resolution *before* outpainting
        # the bleed margin, so IOPaint has real pixel budget to generate into
        # instead of a handful of px that a later upscale would just stretch
        # into a flat/blurry band.
        resolved_upscale_model = upscale_model or UPSCAYL_MODEL_NAME
        upscaled_path = jobs.stage_path(job_id, "upscaled")
        upscale(
            jobs.stage_path(job_id, "normalized"),
            upscaled_path,
            resize_to=TRIM_SIZE_PX,
            model_name=resolved_upscale_model,
        )
        jobs.mark_stage_complete(job_id, "upscaled")

        cleaned = _clean_footer(job_id, upscaled_path, remove_footer_text, footer_height_fraction)

        _finish_bleed_generation(
            job_id,
            cleaned,
            resolved_upscale_model,
            remove_footer_text,
            footer_height_fraction,
            sd_strength,
            sd_mask_blur,
            sd_seed,
        )
    except Exception as exc:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise


def regenerate_bleed_stage(
    job_id: str,
    sd_strength: Optional[float] = None,
    sd_mask_blur: Optional[int] = None,
    sd_seed: Optional[int] = None,
    remove_footer_text: bool = True,
    footer_height_fraction: float = DEFAULT_FOOTER_HEIGHT_FRACTION,
    upscale_model: Optional[str] = None,
) -> None:
    """Re-run the bleed-generation stage (and, if upscale_model is given, the
    upscale step too) for an already-processed job, without repeating
    orient/normalize. Lets a bad stochastic roll be re-rolled cheaply instead
    of re-running the whole (much slower) pipeline, and lets bleed/footer/
    upscale params be experimented with interactively against an
    already-uploaded card. Only the bleed params explicitly passed in
    override generate_bleed()'s module defaults; sd_seed=None picks a fresh
    random seed rather than reusing the original fixed default. upscale_model
    left as None skips re-upscaling (the common, cheap case - re-upscaling is
    an explicit opt-in since it's much slower than a bleed-only re-roll), and
    keeps the previously-recorded model in the job's params rather than
    overwriting it with None."""
    try:
        upscaled_path = jobs.stage_path(job_id, "upscaled")
        if upscale_model is not None:
            upscale(
                jobs.stage_path(job_id, "normalized"),
                upscaled_path,
                resize_to=TRIM_SIZE_PX,
                model_name=upscale_model,
            )
            jobs.mark_stage_complete(job_id, "upscaled")
            resolved_upscale_model = upscale_model
        else:
            resolved_upscale_model = jobs.get_state(job_id).get("params", {}).get("upscale_model")

        cleaned = _clean_footer(job_id, upscaled_path, remove_footer_text, footer_height_fraction)

        _finish_bleed_generation(
            job_id,
            cleaned,
            resolved_upscale_model,
            remove_footer_text,
            footer_height_fraction,
            sd_strength,
            sd_mask_blur,
            sd_seed,
        )
    except Exception as exc:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise
