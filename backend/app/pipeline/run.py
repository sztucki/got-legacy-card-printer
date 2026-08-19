from typing import Optional

from PIL import Image

from app import jobs
from app.config import BLEED_SIZE_PX, TRIM_SIZE_PX, UPSCAYL_MODEL_NAME
from app.jobs import JobStatus
from app.pipeline.bleed import generate_bleed
from app.pipeline.normalize import normalize
from app.pipeline.orient import orient
from app.pipeline.upscale import upscale


def run_pipeline(
    job_id: str,
    rotate_override: Optional[bool] = None,
    upscale_model: Optional[str] = None,
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

        bled = generate_bleed(Image.open(upscaled_path))
        if bled.size != BLEED_SIZE_PX:
            bled = bled.resize(BLEED_SIZE_PX, Image.LANCZOS)
        bled.save(jobs.stage_path(job_id, "bleed"))
        jobs.mark_stage_complete(job_id, "bleed")

        jobs.set_status(job_id, JobStatus.COMPLETE)
    except Exception as exc:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise
