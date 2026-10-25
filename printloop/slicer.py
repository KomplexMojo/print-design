"""Slice a built design with the Bambu Studio CLI and read back time and filament."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from . import config, profiles


def find_bambu_studio() -> str:
    configured = os.environ.get("BAMBU_STUDIO") or config.slicer_config().get("bambu_studio")
    candidates = [configured] if configured else []
    system = platform.system()
    if system == "Darwin":
        candidates.append("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
    elif system == "Windows":
        candidates.append(str(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Bambu Studio/bambu-studio.exe"))
    candidates += [shutil.which("bambu-studio") or "", shutil.which("BambuStudio") or ""]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise SystemExit("Bambu Studio not found. Set bambu_studio in printer/slicer.yaml or the BAMBU_STUDIO env var.")


def read_slice_info(path: Path) -> dict:
    """Pull per-plate time and filament from Metadata/slice_info.config in a sliced 3MF."""
    info = {"plates": []}
    with zipfile.ZipFile(path) as z:
        if "Metadata/slice_info.config" not in z.namelist():
            return info
        root = ET.fromstring(z.read("Metadata/slice_info.config"))
    for plate in root.iter("plate"):
        meta = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
        filaments = [{k: f.get(k) for k in ("type", "color", "used_m", "used_g")} for f in plate.findall("filament")]
        seconds = int(float(meta.get("prediction", 0) or 0))
        info["plates"].append({
            "index": meta.get("index"),
            "time_s": seconds,
            "time": f"{seconds // 3600}h {seconds % 3600 // 60}m",
            "weight_g": float(meta.get("weight", 0) or 0),
            "filaments": filaments,
        })
    return info


def slice_design(name: str, variant: str | None = None, extra_args: list[str] | None = None) -> dict:
    out = config.out_dir(name)
    report_path = out / "report.json"
    if not report_path.exists():
        raise SystemExit(f"Build {name} first: printloop build {name}")
    report = json.loads(report_path.read_text())
    if report["status"] == "fail":
        print("warning: printability checks failed; slicing anyway", file=sys.stderr)

    module = config.load_part_module(name)
    if module.REVISION != report["revision"]:
        raise SystemExit(f"part.py is at r{module.REVISION} but the last build was r{report['revision']}; rebuild first")
    variant = variant or getattr(module, "SLICE_PROFILE", None)
    paths = profiles.profile_paths(variant)
    stem = config.stem(name, report["revision"]) + (f"-{variant}" if variant else "")
    target = out / f"{stem}.gcode.3mf"
    stls = [str(out / p["stl"]) for p in report["parts"].values()]

    cmd = [
        find_bambu_studio(),
        "--arrange", "1",
        "--load-settings", f"{paths['machine']};{paths['process']}",
        "--load-filaments", str(paths["filament"]),
        "--slice", "0",
        "--debug", "2",
        "--outputdir", str(out),
        "--export-3mf", target.name,
        *(extra_args or []),
        *stls,
    ]
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    (out / "slice.log").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    if not target.exists() and (config.ROOT / target.name).exists():
        shutil.move(config.ROOT / target.name, target)
    if proc.returncode != 0 or not target.exists():
        raise SystemExit(f"Bambu Studio exited with {proc.returncode}; see {(out / 'slice.log').relative_to(config.ROOT)}")

    result = {
        "design": name,
        "revision": report["revision"],
        "variant": variant or "default",
        "file": target.name,
        "profiles": {k: json.loads(p.read_text()).get("name") for k, p in paths.items()},
        **read_slice_info(target),
    }
    (out / f"{stem}.slice.json").write_text(json.dumps(result, indent=2))
    return result


def open_in_bambu_studio(path: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", "-a", "BambuStudio", str(path)], check=False)
    elif system == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen([find_bambu_studio(), str(path)])
