from typing import Optional

from PIL import Image

from app import jobs
from app.config import BLEED_SIZE_PX
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

        # gpt-image-1 can only generate at a fixed size, well below print
        # resolution, so the AI bleed step runs first and the whole result
        # (trim + new border) is upscaled to final print resolution after.
        bled = generate_bleed(normalized)
        bled.save(jobs.stage_path(job_id, "bleed"))
        jobs.mark_stage_complete(job_id, "bleed")

        upscale(
            jobs.stage_path(job_id, "bleed"),
            jobs.stage_path(job_id, "upscaled"),
            resize_to=BLEED_SIZE_PX,
        )
        jobs.mark_stage_complete(job_id, "upscaled")

        jobs.set_status(job_id, JobStatus.COMPLETE)
    except Exception as exc:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise
