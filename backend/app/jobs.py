import json
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

from app.config import JOBS_DIR

STATE_FILENAME = "state.json"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


STAGE_FILENAMES = {
    "original": "00-original.png",
    "oriented": "01-oriented.png",
    "normalized": "02-normalized.png",
    "bleed": "03-bleed.png",
    "upscaled": "04-upscaled.png",
}


def create_job() -> str:
    job_id = uuid.uuid4().hex
    job_dir(job_id).mkdir(parents=True, exist_ok=True)
    _write_state(job_id, {"status": JobStatus.PENDING.value, "stages": {}, "error": None})
    return job_id


def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def stage_path(job_id: str, stage: str) -> Path:
    return job_dir(job_id) / STAGE_FILENAMES[stage]


def set_status(job_id: str, status: JobStatus, error: Optional[str] = None) -> None:
    state = get_state(job_id)
    state["status"] = status.value
    state["error"] = error
    _write_state(job_id, state)


def mark_stage_complete(job_id: str, stage: str) -> None:
    state = get_state(job_id)
    state["stages"][stage] = True
    _write_state(job_id, state)


def get_state(job_id: str) -> dict:
    path = job_dir(job_id) / STATE_FILENAME
    if not path.exists():
        raise FileNotFoundError(f"Unknown job: {job_id}")
    return json.loads(path.read_text())


def _write_state(job_id: str, state: dict) -> None:
    path = job_dir(job_id) / STATE_FILENAME
    path.write_text(json.dumps(state))
