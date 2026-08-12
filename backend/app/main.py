from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import jobs
from app.config import JOBS_DIR
from app.jobs import STAGE_FILENAMES
from app.pipeline.run import run_pipeline

app = FastAPI(title="Legacy Card Bleed Printer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(JOBS_DIR)), name="files")


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    rotate_override: Optional[bool] = Form(None),
):
    job_id = jobs.create_job()
    original_path = jobs.stage_path(job_id, "original")
    original_path.write_bytes(await file.read())
    jobs.mark_stage_complete(job_id, "original")

    background_tasks.add_task(run_pipeline, job_id, rotate_override)
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
