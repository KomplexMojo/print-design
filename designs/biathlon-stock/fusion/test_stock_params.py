"""Tests for the fit JSON -> Fusion parameter pipeline (no Fusion needed).

    python3 -m pytest designs/biathlon-stock/fusion -q
"""

import copy
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import stock_params as sp  # noqa: E402

SAMPLE = json.loads((HERE / "samples" / "fit-sample.json").read_text())
PART_PY = (HERE.parent / "part.py").read_text()


def run(doc):
    return sp.resolve(doc, sp.printer_fits(sp.repo_root()))


def test_registry_names_are_valid_and_ordered():
    seen = {f"m_{k}" for k in SAMPLE["measurements"]} | {n for n, _ in sp.RIFLE_PARAMS.values()}
    for p in sp.REGISTRY:
        assert sp.NAME_RE.match(p.name) and p.name not in sp.RESERVED, p.name
        if p.expr:
            refs = sp.names_in(p.expr) - {f"m_{k}" for k in SAMPLE["measurements"]} - {n for n, _ in sp.RIFLE_PARAMS.values()}
            assert refs <= seen, f"{p.name} references {refs - seen} before it is defined"
        seen.add(p.name)
    assert len(sp.BY_NAME) == len(sp.REGISTRY), "duplicate names"


def test_every_fit_app_key_maps():
    for key in SAMPLE["cad_parameters"]:
        assert key in sp.BY_NAME or key in sp.CAD_ALIASES, key


def test_derived_values_match_fit_app():
    rows = run(SAMPLE).by_name()
    for key, entry in SAMPLE["cad_parameters"].items():
        v = entry["value"]
        if isinstance(v, (int, float)) and entry["method"] in ("direct", "derived", "rifle"):
            name = sp.CAD_ALIASES.get(key, key)
            assert rows[name].value == pytest.approx(v, abs=0.06), key


def test_measurement_expressions_used_when_measured():
    rows = run(SAMPLE).by_name()
    assert rows["lop"].expression == "m_AA"
    assert rows["hook_drop"].expression == "m_AF - (m_AC + m_AD / 2)"
    assert rows["face_side"].value == 1 and rows["bolt_dir"].value == 1  # LH stock, right bolt


def test_missing_measurement_falls_back_to_estimate():
    doc = copy.deepcopy(SAMPLE)
    doc["measurements"]["AA"]["value"] = None
    res = run(doc)
    rows = res.by_name()
    assert "m_AA" not in rows
    assert rows["lop"].expression == "335 mm" and rows["lop"].status == "estimate"
    assert any("lop" in w for w in res.warnings)


def test_right_hander_flips_face_side_only():
    doc = copy.deepcopy(SAMPLE)
    doc["athlete"]["stock_handedness"] = "right"
    rows = run(doc).by_name()
    assert rows["face_side"].value == -1 and rows["face_z"].value == -25
    assert rows["bolt_dir"].value == 1  # hardware side unchanged


def test_ibu_flag_on_deep_block():
    doc = copy.deepcopy(SAMPLE)
    sp.BY_NAME["block_height"].default = "150 mm"
    try:
        flags = run(doc).ibu_flags
    finally:
        sp.BY_NAME["block_height"].default = "130 mm"
    assert any(f.startswith("chk_depth_block") for f in flags)


def test_defaults_match_part_py():
    """Registry literals should equal part.py PARAMS until the Fusion model replaces it."""
    scalars = dict(re.findall(r'"(\w+)":\s*(-?[0-9.]+),', PART_PY))
    for p in sp.REGISTRY:
        if p.name in scalars:
            assert sp.evaluate(p.default, {}) == pytest.approx(float(scalars[p.name])), p.name


def test_rejects_other_schema():
    bad = tmp = HERE / "samples" / "_bad.json"
    bad.write_text(json.dumps({"schema": {"id": "x", "version": "1.0.0"}}))
    try:
        with pytest.raises(ValueError):
            sp.load_fit(tmp)
    finally:
        bad.unlink()


def test_part_params_feed_part_py():
    """build123d gets the same numbers as Fusion, in part.py's own shapes."""
    keys = set(re.findall(r'^    "(\w+)":', PART_PY, re.M))
    res = run(SAMPLE)
    out = sp.part_params(res, keys)
    rows = res.by_name()
    assert set(out) <= keys
    assert out["handedness"] == "left" and out["bolt_side"] == "right"
    assert out["lop"] == rows["lop"].value == 335
    assert out["front_tongue"] == (30, 28, 30, -34)
    assert out["mag_holder_count"] == 4 and isinstance(out["mag_holder_count"], int)
    assert set(out) == keys, f"part.py keys the loader does not supply: {keys - set(out)}"
