"""Build a design: run part.py, export STEP + STL, check printability, render a preview."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

import numpy as np
import trimesh
from build123d import Location, Shape, export_step, export_stl

from . import check, config


def _parts(result) -> dict[str, Shape]:
    if isinstance(result, dict):
        return dict(result)
    return {"part": result}


def _on_bed(shape: Shape) -> Shape:
    """Drop the part so its lowest point sits at z=0, the way it will print."""
    bb = shape.bounding_box()
    return shape.moved(Location((0, 0, -bb.min.Z)))


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=config.ROOT,
                             capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain", "designs"], cwd=config.ROOT,
                               capture_output=True, text=True).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def build(name: str, overrides: dict | None = None, preview: bool = True) -> dict:
    module = config.load_part_module(name)
    params = {**module.PARAMS, **(overrides or {})}
    material = getattr(module, "MATERIAL", config.printer_config()["material"]["default"])
    printer = config.printer_config()
    out = config.out_dir(name)
    stem = config.stem(name, module.REVISION)

    report = {
        "design": name,
        "revision": module.REVISION,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": _git_commit(),
        "material": material,
        "params": params,
        "parts": {},
    }

    meshes = []
    for part_name, shape in _parts(module.build(params)).items():
        shape = _on_bed(shape)
        base = stem if part_name == "part" else f"{stem}-{part_name}"
        step_path, stl_path = out / f"{base}.step", out / f"{base}.stl"
        export_step(shape, str(step_path))
        export_stl(shape, str(stl_path), tolerance=0.01, angular_tolerance=0.1)
        mesh = trimesh.load_mesh(stl_path)
        meshes.append((part_name, mesh))

        results = check.check_solid(shape) + check.check_mesh(mesh, printer, material)
        bb = shape.bounding_box()
        report["parts"][part_name] = {
            "step": step_path.name,
            "stl": stl_path.name,
            "size_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
            "volume_mm3": round(shape.volume, 1),
            "status": check.summarize(results),
            "checks": results,
        }

    report["status"] = check.summarize([{"status": p["status"]} for p in report["parts"].values()])
    if preview:
        report["preview"] = render_preview(meshes, out / f"{stem}-preview.png", f"{name} r{module.REVISION}")

    (out / "report.json").write_text(json.dumps(report, indent=2))
    (out / "report.md").write_text(format_report(report))
    return report


def render_preview(meshes: list[tuple[str, trimesh.Trimesh]], path, title: str) -> str:
    """Three views (iso, front, top) so a human or Claude can eyeball the geometry."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    views = [("iso", 25, -55), ("front", 0, -90), ("top", 90, -90)]
    fig = plt.figure(figsize=(12, 4.4))
    light = np.array([0.4, -0.6, 0.7]) / np.linalg.norm([0.4, -0.6, 0.7])
    colors = ["#4f8fd6", "#e0884f", "#5bb07a", "#b06fc4"]

    # Lay multiple parts side by side along X.
    placed, offset = [], 0.0
    for i, (_, mesh) in enumerate(meshes):
        m = mesh.copy()
        m.apply_translation([offset - m.bounds[0][0], 0, 0])
        offset = m.bounds[1][0] + 5
        placed.append((m, colors[i % len(colors)]))
    lo = np.min([m.bounds[0] for m, _ in placed], axis=0)
    hi = np.max([m.bounds[1] for m, _ in placed], axis=0)
    span = (hi - lo).max() / 2
    mid = (hi + lo) / 2

    for i, (label, elev, azim) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        for m, color in placed:
            shade = 0.45 + 0.55 * np.clip(m.face_normals @ light, 0, 1)
            base = np.array(matplotlib.colors.to_rgb(color))
            fc = np.outer(shade, base).clip(0, 1)
            # Edges in the face colour hide the seams between thin CAD triangles.
            poly = Poly3DCollection(m.triangles, facecolors=fc, edgecolors=fc, linewidths=0.3)
            ax.add_collection3d(poly)
        for axis, c in zip("xyz", mid):
            getattr(ax, f"set_{axis}lim")(c - span, c + span)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(label)
        ax.set_axis_off()
    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path.name


def format_report(report: dict) -> str:
    icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
    lines = [f"# {report['design']} r{report['revision']}: {icon[report['status']]} {report['status']}", "",
             f"Built {report['built_at']} from commit {report['commit'] or 'n/a'}, material {report['material']}.", ""]
    lines += ["Params: " + ", ".join(f"`{k}={v}`" for k, v in report["params"].items()), ""]
    for part_name, part in report["parts"].items():
        x, y, z = part["size_mm"]
        lines += [f"## {part_name} ({x} x {y} x {z} mm) {icon[part['status']]}", ""]
        lines += [f"- {icon[c['status']]} **{c['check']}**: {c['detail']}" for c in part["checks"]]
        lines.append("")
    return "\n".join(lines)
