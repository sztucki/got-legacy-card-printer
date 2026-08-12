import shutil
import subprocess
from pathlib import Path

from app.config import UPSCAYL_BIN_PATH


class UpscaylNotConfiguredError(RuntimeError):
    pass


def upscale(input_path: Path, output_path: Path) -> None:
    """Upscale an image by invoking the Upscayl CLI as a subprocess.

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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # -i/-o match the realesrgan-ncnn-vulkan CLI that Upscayl bundles; adjust
    # if your installed binary's flags differ (e.g. add -n <model> -s <scale>).
    result = subprocess.run(
        [UPSCAYL_BIN_PATH, "-i", str(input_path), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Upscayl CLI failed (exit {result.returncode}): {result.stderr.strip()}"
        )
