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

        # AI bleed generation runs at working resolution, then the whole
        # result (trim + new border) is scaled to final print resolution.
        bled = generate_bleed(normalized)
        bled.save(jobs.stage_path(job_id, "bleed"))
        jobs.mark_stage_complete(job_id, "bleed")

        final_path = jobs.stage_path(job_id, "upscaled")
        if bled.width >= BLEED_SIZE_PX[0] and bled.height >= BLEED_SIZE_PX[1]:
            # The AI result is already at or above target resolution - a
            # plain resize gets there without paying for an unnecessary
            # GPU super-resolution pass that would just be downscaled again.
            bled.resize(BLEED_SIZE_PX, Image.LANCZOS).save(final_path)
        else:
            upscale(
                jobs.stage_path(job_id, "bleed"),
                final_path,
                resize_to=BLEED_SIZE_PX,
            )
        jobs.mark_stage_complete(job_id, "upscaled")

        jobs.set_status(job_id, JobStatus.COMPLETE)
    except Exception as exc:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise
