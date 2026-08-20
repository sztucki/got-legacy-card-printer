from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import jobs
from app.config import JOBS_DIR
from app.jobs import JobStatus, STAGE_FILENAMES
from app.pipeline.run import DEFAULT_FOOTER_HEIGHT_FRACTION, regenerate_bleed_stage, run_pipeline
from app.pipeline.upscale import list_models


class RegenerateBleedRequest(BaseModel):
    sd_strength: Optional[float] = None
    sd_mask_blur: Optional[int] = None
    sd_seed: Optional[int] = None
    remove_footer_text: bool = True
    footer_height_fraction: float = DEFAULT_FOOTER_HEIGHT_FRACTION
    upscale_model: Optional[str] = None

app = FastAPI(title="Legacy Card Bleed Printer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(JOBS_DIR)), name="files")


@app.get("/api/upscale-models")
async def get_upscale_models():
    return {"models": list_models()}


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    rotate_override: Optional[bool] = Form(None),
    upscale_model: Optional[str] = Form(None),
    remove_footer_text: bool = Form(True),
    footer_height_fraction: float = Form(DEFAULT_FOOTER_HEIGHT_FRACTION),
    sd_strength: Optional[float] = Form(None),
    sd_mask_blur: Optional[int] = Form(None),
    sd_seed: Optional[int] = Form(None),
):
    job_id = jobs.create_job()
    original_path = jobs.stage_path(job_id, "original")
    original_path.write_bytes(await file.read())
    jobs.mark_stage_complete(job_id, "original")

    background_tasks.add_task(
        run_pipeline,
        job_id,
        rotate_override,
        upscale_model,
        remove_footer_text,
        footer_height_fraction,
        sd_strength,
        sd_mask_blur,
        sd_seed,
    )
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        state = jobs.get_state(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")

    stage_urls = {
        stage: f"/files/{job_id}/{STAGE_FILENAMES[stage]}"
        for stage in state["stages"]
    }
    return {**state, "job_id": job_id, "stage_urls": stage_urls}


@app.post("/api/jobs/{job_id}/regenerate-bleed")
async def regenerate_bleed(
    job_id: str,
    background_tasks: BackgroundTasks,
    options: RegenerateBleedRequest = RegenerateBleedRequest(),
):
    try:
        state = jobs.get_state(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")

    if state["status"] == JobStatus.PROCESSING.value:
        raise HTTPException(status_code=409, detail="Job is still processing")
    if not state["stages"].get("upscaled"):
        raise HTTPException(
            status_code=400,
            detail="Job hasn't reached the bleed-generation stage yet",
        )

    jobs.set_status(job_id, JobStatus.PROCESSING)
    background_tasks.add_task(
        regenerate_bleed_stage,
        job_id,
        options.sd_strength,
        options.sd_mask_blur,
        options.sd_seed,
        options.remove_footer_text,
        options.footer_height_fraction,
        options.upscale_model,
    )
    return {"job_id": job_id}
