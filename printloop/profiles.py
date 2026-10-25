"""Turn Bambu Studio presets into the full configs its CLI needs.

Bambu Studio stores presets as small JSON files that `inherits` from a parent
(user preset -> system preset -> common base). The CLI only accepts complete
configs, so this walks the chain and writes the merged result to printer/profiles/.
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path

from . import config

KINDS = ("machine", "process", "filament")


def default_profile_dirs() -> list[Path]:
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        app = Path("/Applications/BambuStudio.app/Contents/Resources/profiles/BBL")
        data = home / "Library/Application Support/BambuStudio"
    elif system == "Windows":
        app = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Bambu Studio/resources/profiles/BBL"
        data = Path(os.environ.get("APPDATA", home / "AppData/Roaming")) / "BambuStudio"
    else:
        app = Path("/usr/share/bambu-studio/resources/profiles/BBL")
        data = home / ".config/BambuStudio"
    # Order matters: later directories win when two files share a preset name.
    return [app, data / "system/BBL", data / "user"]


def index_presets(dirs: list[Path]) -> dict[str, dict]:
    presets: dict[str, dict] = {}
    for root in dirs:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(data, dict) and "name" in data:
                presets[data["name"]] = {"path": path, "data": data}
    return presets


def flatten(name: str, presets: dict[str, dict]) -> dict:
    chain, seen = [], set()
    current = name
    while current:
        if current in seen:
            raise SystemExit(f"Preset inheritance loop at '{current}'")
        if current not in presets:
            raise SystemExit(f"Preset '{current}' not found (needed by '{name}'). "
                             "Check the name in printer/slicer.yaml or add its folder to extra_profile_dirs.")
        seen.add(current)
        data = presets[current]["data"]
        chain.append(data)
        current = data.get("inherits", "")
    merged: dict = {}
    for data in reversed(chain):
        merged.update(data)
    merged.pop("inherits", None)
    merged["name"] = name
    return merged


def search_dirs() -> list[Path]:
    extra = [Path(p).expanduser() for p in config.slicer_config().get("extra_profile_dirs") or []]
    env = os.environ.get("BAMBU_PROFILE_DIRS")
    if env:
        extra += [Path(p) for p in env.split(os.pathsep)]
    return default_profile_dirs() + extra


def write_profiles(dirs: list[Path] | None = None) -> list[Path]:
    """Flatten the default presets and every variant into printer/profiles/."""
    cfg = config.slicer_config()
    presets = index_presets(dirs or search_dirs())
    if not presets:
        raise SystemExit("No Bambu Studio presets found. Is Bambu Studio installed? "
                         "Set BAMBU_PROFILE_DIRS or extra_profile_dirs in printer/slicer.yaml.")
    config.PROFILES.mkdir(parents=True, exist_ok=True)
    written = []
    sets = {"default": {}} | (cfg.get("variants") or {})
    for variant, spec in sets.items():
        for kind in KINDS:
            if variant != "default" and kind not in spec and not (kind == "process" and spec.get("overrides")):
                continue
            data = flatten(spec.get(kind, cfg["presets"][kind]), presets)
            if kind == "process":
                data.update(spec.get("overrides") or {})
            path = config.PROFILES / f"{kind}{'' if variant == 'default' else '-' + variant}.json"
            path.write_text(json.dumps(data, indent=2, sort_keys=True))
            written.append(path)
    return written


def profile_paths(variant: str | None) -> dict[str, Path]:
    paths = {}
    for kind in KINDS:
        chosen = config.PROFILES / f"{kind}-{variant}.json" if variant else None
        paths[kind] = chosen if chosen and chosen.exists() else config.PROFILES / f"{kind}.json"
        if not paths[kind].exists():
            raise SystemExit(f"Missing {paths[kind].relative_to(config.ROOT)}. Run `printloop profiles` on the "
                             "machine with Bambu Studio installed.")
    return paths
