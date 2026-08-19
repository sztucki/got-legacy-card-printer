import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from app.config import UPSCAYL_BIN_PATH, UPSCAYL_MODEL_NAME, UPSCAYL_MODELS_DIR


class UpscaylNotConfiguredError(RuntimeError):
    pass


def list_models() -> List[str]:
    """Model names available in UPSCAYL_MODELS_DIR (one per .param file),
    sorted with the configured default (UPSCAYL_MODEL_NAME) first. Used to
    populate the frontend's model picker."""
    if not UPSCAYL_MODELS_DIR:
        return [UPSCAYL_MODEL_NAME]
    names = sorted(p.stem for p in Path(UPSCAYL_MODELS_DIR).glob("*.param"))
    if UPSCAYL_MODEL_NAME in names:
        names.remove(UPSCAYL_MODEL_NAME)
        names.insert(0, UPSCAYL_MODEL_NAME)
    return names


def upscale(
    input_path: Path,
    output_path: Path,
    resize_to: Optional[Tuple[int, int]] = None,
    model_name: str = UPSCAYL_MODEL_NAME,
) -> None:
    """Upscale an image by invoking the Upscayl CLI as a subprocess.

    If resize_to is given, the model's fixed scale factor (e.g. 4x) is
    followed by an exact resize to those dimensions (via the CLI's -r flag)
    so the output lands on a precise target pixel size.

    model_name overrides UPSCAYL_MODEL_NAME without touching env vars - used
    by backend/scripts/compare_upscale_models.py to compare candidates.

    Raises UpscaylNotConfiguredError if UPSCAYL_BIN_PATH isn't set or the
    binary can't be found, rather than silently skipping the step.
    """
    if not UPSCAYL_BIN_PATH:
        raise UpscaylNotConfiguredError(
            "UPSCAYL_BIN_PATH is not set. Install Upscayl and point this env "
            "var at its bundled CLI binary (see backend/.env.example)."
        )
    if not shutil.which(UPSCAYL_BIN_PATH) and not Path(UPSCAYL_BIN_PATH).is_file():
        raise UpscaylNotConfiguredError(
            f"Upscayl CLI binary not found at UPSCAYL_BIN_PATH={UPSCAYL_BIN_PATH!r}."
        )
    if not UPSCAYL_MODELS_DIR:
        raise UpscaylNotConfiguredError(
            "UPSCAYL_MODELS_DIR is not set. The bundled Upscayl CLI doesn't "
            "ship its own default model, so this must point at a folder of "
            ".bin/.param model files (see backend/.env.example)."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # -i/-o/-m/-n match the realesrgan-ncnn-vulkan CLI that Upscayl bundles.
    # -m/-n are required because the bundled models folder doesn't include
    # the binary's built-in default model name (realesrgan-x4plus).
    command = [
        UPSCAYL_BIN_PATH,
        "-i", str(input_path),
        "-o", str(output_path),
        "-m", UPSCAYL_MODELS_DIR,
        "-n", model_name,
    ]
    if resize_to:
        command += ["-r", f"{resize_to[0]}x{resize_to[1]}"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Upscayl CLI failed (exit {result.returncode}): {result.stderr.strip()}"
        )
