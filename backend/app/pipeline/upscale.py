import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from app.config import UPSCAYL_BIN_PATH, UPSCAYL_MODEL_NAME, UPSCAYL_MODELS_DIR


class UpscaylNotConfiguredError(RuntimeError):
    pass


def upscale(
    input_path: Path, output_path: Path, resize_to: Optional[Tuple[int, int]] = None
) -> None:
    """Upscale an image by invoking the Upscayl CLI as a subprocess.

    If resize_to is given, the model's fixed scale factor (e.g. 4x) is
    followed by an exact resize to those dimensions (via the CLI's -r flag)
    so the output lands on a precise target pixel size.

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
        "-n", UPSCAYL_MODEL_NAME,
    ]
    if resize_to:
        command += ["-r", f"{resize_to[0]}x{resize_to[1]}"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Upscayl CLI failed (exit {result.returncode}): {result.stderr.strip()}"
        )
