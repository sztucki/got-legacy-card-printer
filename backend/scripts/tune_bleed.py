"""Standalone dev script to iterate on IOPaint bleed-generation parameters
without going through the FastAPI server or the browser upload flow.

Usage:
    backend/venv/bin/python backend/scripts/tune_bleed.py [image_path ...]

With no arguments, runs against every image found under reference-cards/.
Outputs go to backend/jobs/_tune/<image-stem>/<variant-label>.png so
variants can be compared side by side. Requires a running IOPaint server
(see README.md).
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
from app.pipeline.bleed import generate_bleed  # noqa: E402
from app.pipeline.normalize import normalize  # noqa: E402
from app.pipeline.orient import orient  # noqa: E402
from app.pipeline.upscale import upscale  # noqa: E402

# Fixed relative to this script (not JOBS_DIR, which resolves against
# whatever the caller's cwd happens to be) so output always lands in the
# same, already-gitignored place regardless of where this is run from.
OUTPUT_DIR = BACKEND_DIR / "jobs" / "_tune"

# Label -> generate_bleed() keyword overrides, all run against the same
# upscaled trim image so results are directly comparable. Add/edit entries
# here to try new parameter combinations.
VARIANTS = {
    "baseline": {},
    "stronger_negative": {
        "negative_prompt": (
            "blank space, empty area, solid color, plain background, white "
            "border, blurry, low detail, text, watermark, flat color, "
            "smooth gradient"
        )
    },
    "more_overshoot": {"generation_overshoot": 2.0},
    "more_steps": {"sd_steps": 80},
}


def tune_one(image_path: Path) -> None:
    print(f"--- {image_path.name} ---")
    out_dir = OUTPUT_DIR / image_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    original = Image.open(image_path)
    oriented = orient(original, rotate_override=None)
    normalized = normalize(oriented)

    normalized_path = out_dir / "_normalized.png"
    normalized.save(normalized_path)
    upscaled_path = out_dir / "_upscaled.png"
    upscale(normalized_path, upscaled_path, resize_to=TRIM_SIZE_PX)
    upscaled = Image.open(upscaled_path)

    for label, overrides in VARIANTS.items():
        print(f"  generating: {label} ({overrides or 'defaults'})")
        result = generate_bleed(upscaled, **overrides)
        result.save(out_dir / f"{label}.png")

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
        tune_one(image_path)


if __name__ == "__main__":
    main()
