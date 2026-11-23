"""Fusion 360 script: load a biathlon fit record into the active design's User Parameters.

Run it either way:
  * Fusion > Utilities > Add-Ins > Scripts and Add-Ins > + (this folder) > Run.
    A file dialog asks for the fit JSON unless FIT_JSON below is set.
  * Through the Autodesk Fusion MCP server (`fusion_mcp_execute`, featureType "script"):
    send this file's text with FIT_JSON set to an absolute path.

Behaviour (idempotent, safe to re-run after every new measurement):
  1. Reads and validates the JSON with stock_params.py (same folder, stdlib only).
  2. Pass 1 creates any missing parameter with its literal value, so every name exists.
  3. Pass 2 sets each parameter's expression in registry order (m_* first, chk_* last).
  4. Skips any parameter whose comment starts with "[manual]" (Darren's hand overrides).
  5. Never deletes. Reports "[fit]" parameters that are no longer in the registry.
  6. Prints a summary and every chk_* below zero (IBU or layout margin broken).
Nothing is saved; save the document yourself when the result looks right.
"""

import os
import sys
import traceback

import adsk.core
import adsk.fusion

FIT_JSON = None  # absolute path to a fit record; None opens a file dialog

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
# When run through the MCP the script has no __file__: point at the repo copy.
FALLBACK_DIR = os.path.expanduser("~/Documents/GitHub/print-design/designs/biathlon-stock/fusion")


def _import_stock_params():
    folder = HERE or FALLBACK_DIR
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import importlib
    import stock_params
    return importlib.reload(stock_params)   # pick up registry edits without restarting Fusion


def _pick_file(ui):
    dlg = ui.createFileDialog()
    dlg.title = "Biathlon fit record (JSON)"
    dlg.filter = "Fit record (*.json)"
    if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
        return None
    return dlg.filename


def load(design, path, sp, log=print):
    params = design.userParameters
    res = sp.resolve(sp.load_fit(path), sp.printer_fits(sp.repo_root()))
    created, updated, skipped, unchanged = [], [], [], []

    # Pass 1: make sure every name exists (literal value), so pass 2 expressions resolve.
    for r in res.rows:
        p = params.itemByName(r.name)
        if p is None:
            params.add(r.name, adsk.core.ValueInput.createByString(sp.literal(r.value, r.unit)), r.unit, r.comment)
            created.append(r.name)

    # Pass 2: expressions and comments, in dependency order.
    for r in res.rows:
        p = params.itemByName(r.name)
        if p.comment.startswith(sp.MANUAL):
            skipped.append(r.name)
            continue
        if p.unit != r.unit:
            log(f"unit mismatch on {r.name}: design has '{p.unit}', registry '{r.unit}'. Left as is.")
            skipped.append(r.name)
            continue
        if p.expression != r.expression or p.comment != r.comment:
            p.expression = r.expression
            p.comment = r.comment
            if r.name not in created:
                updated.append(r.name)
        else:
            unchanged.append(r.name)

    owned = {r.name for r in res.rows}
    stale = [params.item(i).name for i in range(params.count)
             if params.item(i).comment.startswith(sp.TAG) and params.item(i).name not in owned]

    # Read back what Fusion computed (internal units are cm / rad) for the checks.
    broken = []
    for r in res.rows:
        if r.name.startswith("chk_"):
            v_mm = params.itemByName(r.name).value * 10.0
            if v_mm < -1e-6:
                broken.append(f"{r.name} = {v_mm:.1f} mm  ({sp.BY_NAME[r.name].note})")

    log(f"Fit record: {path}")
    log(f"created {len(created)}, updated {len(updated)}, unchanged {len(unchanged)}, manual/skipped {len(skipped)}")
    for w in res.warnings:
        log("warning: " + w)
    if stale:
        log("no longer in the registry (left in place): " + ", ".join(stale))
    for b in broken:
        log("IBU/layout ⚠️  " + b)
    if not broken:
        log("All chk_* margins >= 0.")
    return {"created": created, "updated": updated, "skipped": skipped, "stale": stale, "broken": broken}


def run(_context: str):
    app = adsk.core.Application.get()
    ui = app.userInterface
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        raise RuntimeError("Open or create a Fusion design first.")
    if design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
        raise RuntimeError("The design must be parametric (capture design history on).")
    path = FIT_JSON or _pick_file(ui)
    if not path:
        return
    sp = _import_stock_params()
    lines = []

    def log(msg):
        print(msg)
        lines.append(msg)

    try:
        load(design, path, sp, log)
    except Exception:
        if ui and "__file__" in globals():          # interactive run: show the error
            ui.messageBox(traceback.format_exc())
        raise
    if ui and "__file__" in globals():
        ui.messageBox("\n".join(lines[-25:]), "Biathlon stock parameters")
