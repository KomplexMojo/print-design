"""Paths and settings shared by the printloop commands."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DESIGNS = ROOT / "designs"
PRINTER = ROOT / "printer"
PROFILES = PRINTER / "profiles"
TEMPLATE = DESIGNS / "_template"


def printer_config() -> dict:
    return yaml.safe_load((PRINTER / "h2s.yaml").read_text())


def slicer_config() -> dict:
    return yaml.safe_load((PRINTER / "slicer.yaml").read_text())


def design_dir(name: str) -> Path:
    path = DESIGNS / name
    if not (path / "part.py").exists():
        known = ", ".join(sorted(p.name for p in DESIGNS.iterdir() if (p / "part.py").exists() and p.name != "_template"))
        raise SystemExit(f"No design named '{name}'. Known designs: {known or 'none yet'}")
    return path


def out_dir(name: str) -> Path:
    path = DESIGNS / name / "out"
    path.mkdir(exist_ok=True)
    return path


def load_part_module(name: str):
    """Import designs/<name>/part.py as a fresh module."""
    path = design_dir(name) / "part.py"
    spec = importlib.util.spec_from_file_location(f"design_{name.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for attr in ("PARAMS", "REVISION", "build"):
        if not hasattr(module, attr):
            raise SystemExit(f"{path} must define {attr}")
    return module


def stem(name: str, revision: int) -> str:
    return f"{name}-r{revision}"
