import random
from typing import Optional

from PIL import Image

from app import jobs
from app.config import BLEED_SIZE_PX, TRIM_SIZE_PX, UPSCAYL_MODEL_NAME
from app.jobs import JobStatus
from app.pipeline.bleed import generate_bleed
from app.pipeline.clean_text import remove_footer_band
from app.pipeline.normalize import normalize
from app.pipeline.orient import orient
from app.pipeline.upscale import upscale

DEFAULT_FOOTER_HEIGHT_FRACTION = 0.08


def run_pipeline(
    job_id: str,
    rotate_override: Optional[bool] = None,
    upscale_model: Optional[str] = None,
    remove_footer_text: bool = False,
    footer_height_fraction: float = DEFAULT_FOOTER_HEIGHT_FRACTION,
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
        upscaled_path = jobs.stage_path(job_id, "upscaled")
        upscale(
            jobs.stage_path(job_id, "normalized"),
            upscaled_path,
            resize_to=TRIM_SIZE_PX,
            model_name=upscale_model or UPSCAYL_MODEL_NAME,
        )
        jobs.mark_stage_complete(job_id, "upscaled")

        cleaned_path = jobs.stage_path(job_id, "cleaned")
        if remove_footer_text:
            remove_footer_band(Image.open(upscaled_path), footer_height_fraction).save(cleaned_path)
        else:
            Image.open(upscaled_path).save(cleaned_path)
        jobs.mark_stage_complete(job_id, "cleaned")

        bled = generate_bleed(Image.open(cleaned_path))
        if bled.size != BLEED_SIZE_PX:
            bled = bled.resize(BLEED_SIZE_PX, Image.LANCZOS)
        bled.save(jobs.stage_path(job_id, "bleed"))
        jobs.mark_stage_complete(job_id, "bleed")

        jobs.set_status(job_id, JobStatus.COMPLETE)
    except Exception as exc:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise


def regenerate_bleed_stage(job_id: str) -> None:
    """Re-run just the bleed-generation stage for an already-processed job,
    with a fresh random seed, without repeating orient/normalize/upscale/
    footer-clean. Lets a bad stochastic roll be re-rolled cheaply instead of
    re-running the whole (much slower) pipeline."""
    try:
        jobs.set_status(job_id, JobStatus.PROCESSING)

        cleaned = Image.open(jobs.stage_path(job_id, "cleaned"))
        seed = random.randint(0, 2**31 - 1)

        bled = generate_bleed(cleaned, sd_seed=seed)
        if bled.size != BLEED_SIZE_PX:
            bled = bled.resize(BLEED_SIZE_PX, Image.LANCZOS)
        bled.save(jobs.stage_path(job_id, "bleed"))
        jobs.mark_stage_complete(job_id, "bleed")

        jobs.set_status(job_id, JobStatus.COMPLETE)
    except Exception as exc:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise
