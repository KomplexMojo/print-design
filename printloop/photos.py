"""Add photos to a design: reference shots for ideation, and print results for refinement.

Photos are re-encoded as JPEG (longest side 2400 px), rotated upright, and stripped of
EXIF metadata such as GPS location, so the repo stays small and shareable. Each photo
gets an entry in photos/index.yaml with a caption so later sessions know what it shows.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml
from PIL import Image, ImageOps

from . import config

try:  # iPhone HEIC/HEIF photos
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

KINDS = ("ref", "print")
MAX_SIDE = 2400


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "photo"


def add_photo(name: str, source: Path, kind: str = "ref", caption: str = "", revision: int | None = None) -> dict:
    if kind not in KINDS:
        raise SystemExit(f"kind must be one of {', '.join(KINDS)}")
    folder = config.design_dir(name) / "photos" / kind
    folder.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        base = f"{date.today():%Y%m%d}-{_slug(caption or source.stem)}"
        target = folder / f"{base}.jpg"
        n = 2
        while target.exists():
            target = folder / f"{base}-{n}.jpg"
            n += 1
        img.save(target, "JPEG", quality=85, optimize=True)
        size = img.size

    if kind == "print" and revision is None:
        revision = config.load_part_module(name).REVISION
    entry = {
        "file": str(target.relative_to(config.design_dir(name))),
        "kind": kind,
        "caption": caption,
        "date": date.today().isoformat(),
        "original": source.name,
        "size_px": list(size),
    }
    if revision is not None:
        entry["revision"] = revision

    index_path = config.design_dir(name) / "photos" / "index.yaml"
    index = (yaml.safe_load(index_path.read_text()) or []) if index_path.exists() else []
    index.append(entry)
    index_path.write_text(yaml.safe_dump(index, sort_keys=False, allow_unicode=True))
    return entry
