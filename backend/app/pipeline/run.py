from typing import Optional

from PIL import Image

from app import jobs
from app.jobs import JobStatus
from app.pipeline.bleed import generate_bleed
from app.pipeline.normalize import normalize
from app.pipeline.orient import orient
from app.pipeline.upscale import upscale


def run_pipeline(job_id: str, rotate_override: Optional[bool] = None) -> None:
    try:
        jobs.set_status(job_id, JobStatus.PROCESSING)

        original = Image.open(jobs.stage_path(job_id, "original"))

        oriented = orient(original, rotate_override=rotate_override)
        oriented.save(jobs.stage_path(job_id, "oriented"))
        jobs.mark_stage_complete(job_id, "oriented")

        normalized = normalize(oriented)
        normalized.save(jobs.stage_path(job_id, "normalized"))
        jobs.mark_stage_complete(job_id, "normalized")

        upscale(jobs.stage_path(job_id, "normalized"), jobs.stage_path(job_id, "upscaled"))
        jobs.mark_stage_complete(job_id, "upscaled")

        upscaled = Image.open(jobs.stage_path(job_id, "upscaled"))
        final = generate_bleed(upscaled)
        final.save(jobs.stage_path(job_id, "bleed"))
        jobs.mark_stage_complete(job_id, "bleed")

        jobs.set_status(job_id, JobStatus.COMPLETE)
    except Exception as exc:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise
