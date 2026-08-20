"""Shared helpers for the standalone dev scripts in this directory."""

import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple


def setup_script_env(script_file: str) -> Tuple[Path, Path]:
    """Common bootstrap for these scripts: puts backend/ on sys.path (for
    `app.*` imports) and loads backend/.env. Call this before importing
    anything from `app`. Returns (backend_dir, repo_root)."""
    scripts_dir = Path(script_file).resolve().parent
    backend_dir = scripts_dir.parent
    repo_root = backend_dir.parent
    sys.path.insert(0, str(backend_dir))

    from dotenv import load_dotenv

    load_dotenv(backend_dir / ".env")

    return backend_dir, repo_root


def discover_reference_images(repo_root: Path, args: List[str]) -> Optional[List[Path]]:
    """Explicit image paths if given as CLI args, otherwise every .tif/.jpg
    under reference-cards/. Returns None (after printing a message) if
    neither yields anything to run against."""
    if args:
        return [Path(a) for a in args]

    images = sorted(repo_root.glob("reference-cards/**/*.tif")) + sorted(
        repo_root.glob("reference-cards/**/*.jpg")
    )
    if not images:
        print("No images found under reference-cards/ - pass image paths explicitly.")
        return None
    return images


def run_over_reference_images(repo_root: Path, argv: List[str], fn: Callable[[Path], None]) -> None:
    """Shared main() body: discover_reference_images() against argv, then
    call fn(image_path) for each, printing a per-image header. Does nothing
    (after discover_reference_images' own message) if no images are found."""
    images = discover_reference_images(repo_root, argv)
    if images is None:
        return

    for image_path in images:
        print(f"--- {image_path.name} ---")
        fn(image_path)


def prepare_normalized(image_path: Path, out_dir: Path):
    """Common orient+normalize prefix these scripts each run before
    diverging into their own upscale/bleed comparison. Creates out_dir,
    writes _normalized.png into it, and returns (normalized_image,
    normalized_path)."""
    from PIL import Image

    from app.pipeline.normalize import normalize
    from app.pipeline.orient import orient

    out_dir.mkdir(parents=True, exist_ok=True)
    original = Image.open(image_path)
    oriented = orient(original, rotate_override=None)
    normalized = normalize(oriented)
    normalized_path = out_dir / "_normalized.png"
    normalized.save(normalized_path)
    return normalized, normalized_path
