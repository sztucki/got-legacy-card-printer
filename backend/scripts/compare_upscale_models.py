"""Standalone dev script to compare Upscayl models against each other on real
card art, without going through the FastAPI server or the browser upload flow.

Usage:
    backend/venv/bin/python backend/scripts/compare_upscale_models.py [image_path ...]

With no arguments, runs against every image found under reference-cards/.
Outputs go to test-outputs/upscale-models/<image-stem>/<model-name>.png so
models can be compared side by side. Only needs Upscayl configured (see
backend/.env.example) - no IOPaint/bleed step involved, so it's fast.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _reference_images import (  # noqa: E402
    prepare_normalized,
    run_over_reference_images,
    setup_script_env,
)

_, REPO_ROOT = setup_script_env(__file__)

from app.config import TRIM_SIZE_PX  # noqa: E402
from app.pipeline.upscale import list_models, upscale  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "test-outputs" / "upscale-models"


def compare_one(image_path: Path) -> None:
    out_dir = OUTPUT_DIR / image_path.stem
    _, normalized_path = prepare_normalized(image_path, out_dir)

    # Same models the frontend's picker offers (list_models() sorts the
    # configured default first) - stays in sync automatically if
    # UPSCAYL_MODELS_DIR's contents change, rather than a separately
    # maintained hardcoded list that can silently drift from what's
    # actually available.
    for model_name in list_models():
        print(f"  upscaling with: {model_name}")
        upscale(
            normalized_path,
            out_dir / f"{model_name}.png",
            resize_to=TRIM_SIZE_PX,
            model_name=model_name,
        )

    print(f"  wrote variants to {out_dir}")


def main() -> None:
    run_over_reference_images(REPO_ROOT, sys.argv[1:], compare_one)


if __name__ == "__main__":
    main()
