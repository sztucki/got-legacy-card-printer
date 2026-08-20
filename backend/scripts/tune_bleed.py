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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _reference_images import discover_reference_images, setup_script_env  # noqa: E402

_, REPO_ROOT = setup_script_env(__file__)

from PIL import Image  # noqa: E402

from app.config import TRIM_SIZE_PX  # noqa: E402
from app.pipeline.bleed import generate_bleed  # noqa: E402
from app.pipeline.clean_text import remove_footer_band  # noqa: E402
from app.pipeline.normalize import normalize  # noqa: E402
from app.pipeline.orient import orient  # noqa: E402
from app.pipeline.upscale import upscale  # noqa: E402
from app.pipeline.run import DEFAULT_FOOTER_HEIGHT_FRACTION  # noqa: E402

# Fixed relative to the repo root (not JOBS_DIR, which resolves against
# whatever the caller's cwd happens to be) so output always lands in the
# same, gitignored place regardless of where this is run from.
OUTPUT_DIR = REPO_ROOT / "test-outputs"

# Label -> generate_bleed() keyword overrides, all run against the same
# upscaled + footer-cleaned trim image so results are directly comparable.
# Add/edit entries here to try new parameter combinations.
VARIANTS = {
    "baseline": {},
    "strength_70": {"sd_strength": 0.7},
    "strength_60": {"sd_strength": 0.6},
}

# Diffusion output is seed-sensitive (see test-outputs/seed-diag/ and
# README's Known Issues) - sweeping several seeds per variant turns "did we
# get a lucky roll" into a visible comparison grid instead of a coincidence.
SEEDS = [42, 7, 123, 9999]


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

    # Matches run_pipeline's default (remove_footer_text=True) so tuning
    # results reflect what actually ships.
    cleaned = remove_footer_band(upscaled, DEFAULT_FOOTER_HEIGHT_FRACTION)
    cleaned_path = out_dir / "_cleaned.png"
    cleaned.save(cleaned_path)

    for label, overrides in VARIANTS.items():
        for seed in SEEDS:
            print(f"  generating: {label}_seed{seed} ({overrides or 'defaults'})")
            result = generate_bleed(cleaned, sd_seed=seed, **overrides)
            result.save(out_dir / f"{label}_seed{seed}.png")

    print(f"  wrote variants to {out_dir}")


def main() -> None:
    images = discover_reference_images(REPO_ROOT, sys.argv[1:])
    if images is None:
        return

    for image_path in images:
        tune_one(image_path)


if __name__ == "__main__":
    main()
