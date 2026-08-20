import json
import threading
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

from app.config import JOBS_DIR

STATE_FILENAME = "state.json"

# Guards the check-then-act sequence in try_start_processing() so two
# concurrent requests against the same job (e.g. a fast double-click on
# "Regenerate bleed") can't both pass the status check and both schedule a
# generation against the same stage files.
_status_lock = threading.Lock()


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


STAGE_FILENAMES = {
    "original": "00-original.png",
    "oriented": "01-oriented.png",
    "normalized": "02-normalized.png",
    "upscaled": "03-upscaled.png",
    "cleaned": "04-cleaned.png",
    "bleed": "05-bleed.png",
}


def create_job() -> str:
    job_id = uuid.uuid4().hex
    job_dir(job_id).mkdir(parents=True, exist_ok=True)
    _write_state(
        job_id,
        {"status": JobStatus.PENDING.value, "stages": {}, "error": None, "params": {}},
    )
    return job_id


def set_params(job_id: str, params: dict) -> None:
    """Record the settings (footer removal, upscale model, bleed strength/etc.)
    a job was last generated with, so the frontend's regenerate panel can
    default to "whatever this job was actually generated with" rather than
    hardcoded constants that might silently override the user's original
    choices (e.g. footer-text removal) on a bare re-roll."""
    state = get_state(job_id)
    state["params"] = params
    _write_state(job_id, state)


def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def stage_path(job_id: str, stage: str) -> Path:
    return job_dir(job_id) / STAGE_FILENAMES[stage]


def set_status(job_id: str, status: JobStatus, error: Optional[str] = None) -> None:
    state = get_state(job_id)
    state["status"] = status.value
    state["error"] = error
    _write_state(job_id, state)


def try_start_processing(job_id: str, required_stage: Optional[str] = None) -> Optional[str]:
    """Atomically check the job isn't already processing (and, if given,
    that required_stage is complete) and transition it to PROCESSING.

    Returns None on success. Otherwise returns a reason ("processing" or
    "not_ready") without changing anything, so a caller with two concurrent
    requests for the same job can't have both pass the check and both start
    a generation against the same stage files."""
    with _status_lock:
        state = get_state(job_id)
        if state["status"] == JobStatus.PROCESSING.value:
            return "processing"
        if required_stage and not state["stages"].get(required_stage):
            return "not_ready"
        state["status"] = JobStatus.PROCESSING.value
        state["error"] = None
        _write_state(job_id, state)
        return None


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
