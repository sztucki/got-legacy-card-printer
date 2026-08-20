"""Shared helper for the standalone dev scripts in this directory."""

from pathlib import Path
from typing import List, Optional


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
