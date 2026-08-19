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

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

from PIL import Image  # noqa: E402

from app.config import TRIM_SIZE_PX  # noqa: E402
from app.pipeline.normalize import normalize  # noqa: E402
from app.pipeline.orient import orient  # noqa: E402
from app.pipeline.upscale import upscale  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "test-outputs" / "upscale-models"

# upscayl-standard-4x is the project's current default - kept first as the
# baseline to compare the others against.
MODELS = [
    "upscayl-standard-4x",
    "high-fidelity-4x",
    "ultramix-balanced-4x",
    "remacri-4x",
    "ultrasharp-4x",
]


def compare_one(image_path: Path) -> None:
    print(f"--- {image_path.name} ---")
    out_dir = OUTPUT_DIR / image_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    original = Image.open(image_path)
    oriented = orient(original, rotate_override=None)
    normalized = normalize(oriented)
    normalized_path = out_dir / "_normalized.png"
    normalized.save(normalized_path)

    for model_name in MODELS:
        print(f"  upscaling with: {model_name}")
        upscale(
            normalized_path,
            out_dir / f"{model_name}.png",
            resize_to=TRIM_SIZE_PX,
            model_name=model_name,
        )

    print(f"  wrote variants to {out_dir}")


def main() -> None:
    args = sys.argv[1:]
    if args:
        images = [Path(a) for a in args]
    else:
        images = sorted(REPO_ROOT.glob("reference-cards/**/*.tif")) + sorted(
            REPO_ROOT.glob("reference-cards/**/*.jpg")
        )
        if not images:
            print("No images found under reference-cards/ - pass image paths explicitly.")
            return

    for image_path in images:
        compare_one(image_path)


if __name__ == "__main__":
    main()
