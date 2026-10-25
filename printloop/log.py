"""The print log: one YAML list per design, newest entry last.

Every printed revision gets an entry with what was expected, what came off the
bed, and what to change next. The refine step reads this before editing part.py.
"""

from __future__ import annotations

import json
from datetime import date

import yaml

from . import config


def log_path(name: str):
    return config.design_dir(name) / "log.yaml"


def read_log(name: str) -> list[dict]:
    path = log_path(name)
    return (yaml.safe_load(path.read_text()) or []) if path.exists() else []


def latest_slice(name: str, revision: int) -> dict | None:
    out = config.DESIGNS / name / "out"
    files = sorted(out.glob(f"{config.stem(name, revision)}*.slice.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        return None
    data = json.loads(files[-1].read_text())
    plate = (data.get("plates") or [{}])[0]
    return {"file": data["file"], "variant": data["variant"], "profiles": data["profiles"],
            "time": plate.get("time"), "weight_g": plate.get("weight_g")}


def add_entry(name: str, result: str, measurements: list[str], issues: list[str], next_steps: list[str],
              notes: str | None, photos: list[str], revision: int | None = None) -> dict:
    module = config.load_part_module(name)
    revision = revision or module.REVISION
    report_path = config.DESIGNS / name / "out" / "report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}

    entry = {
        "revision": revision,
        "date": date.today().isoformat(),
        "commit": report.get("commit"),
        "params": report.get("params") if report.get("revision") == revision else module.PARAMS,
        "slice": latest_slice(name, revision),
        "result": result,
        "measurements": [_parse_measure(m) for m in measurements],
        "issues": issues,
        "next": next_steps,
        "notes": notes,
        "photos": photos,
    }
    entry = {k: v for k, v in entry.items() if v not in (None, [], "")}
    entries = read_log(name) + [entry]
    log_path(name).write_text(yaml.safe_dump(entries, sort_keys=False, allow_unicode=True))
    return entry


def _parse_measure(text: str) -> dict:
    """feature=expected:measured, e.g. hole_d=10.0:9.82"""
    feature, _, values = text.partition("=")
    expected, _, measured = values.partition(":")
    e, m = float(expected), float(measured)
    return {"feature": feature, "expected": e, "measured": m, "error": round(m - e, 3)}
