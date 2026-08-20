"""Shared helpers for the standalone dev scripts in this directory."""

import sys
from pathlib import Path
from typing import List, Optional, Tuple


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
