"""Printability checks for the H2S, run on every build.

Each check returns {"check", "status", "detail"} where status is pass, warn or fail.
A fail means the part will not print as modeled; a warn means it probably prints
but deserves a look (or a deliberate note in the brief explaining why it is fine).
"""

from __future__ import annotations

import math

import numpy as np
import trimesh


def _result(check: str, status: str, detail: str) -> dict:
    return {"check": check, "status": status, "detail": detail}


def check_solid(shape) -> list[dict]:
    results = []
    solids = shape.solids()
    if not solids:
        return [_result("solid", "fail", "No solid geometry; did build() return a sketch or a face?")]
    results.append(_result("solid", "pass" if shape.is_valid else "fail",
                           f"{len(solids)} solid(s), OCC validity {'ok' if shape.is_valid else 'FAILED'}"))
    if len(solids) > 1:
        results.append(_result("bodies", "warn",
                               f"{len(solids)} separate solids in one body; return a dict of parts if that is intended"))
    return results


def check_mesh(mesh: trimesh.Trimesh, printer: dict, material: str) -> list[dict]:
    rules = printer["rules"]
    pr = printer["printer"]
    results = []

    # Tessellating poles and seams can leave a couple of zero-area slivers; only real gaps matter.
    open_edges = len(trimesh.grouping.group_rows(mesh.edges_sorted, require_count=1))
    if open_edges == 0:
        results.append(_result("watertight", "pass", "mesh is closed"))
    elif open_edges <= 10:
        results.append(_result("watertight", "pass", f"{open_edges} open edge(s) from tessellation; harmless"))
    else:
        results.append(_result("watertight", "fail" if open_edges > 100 else "warn",
                               f"{open_edges} open edges; the geometry has gaps the slicer may repair badly"))

    # Fit in the build volume (the part may be rotated on the plate, so compare sorted XY).
    ext = mesh.bounding_box.extents
    vol = np.array(pr["build_volume_mm"], dtype=float)
    margin = 2 * pr.get("bed_margin_mm", 0)
    fits_xy = np.sort(ext[:2]) <= np.sort(vol[:2] - margin)
    fits = bool(np.all(fits_xy)) and ext[2] <= vol[2]
    results.append(_result("build_volume", "pass" if fits else "fail",
                           f"part {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm, bed {vol[0]:.0f} x {vol[1]:.0f} x {vol[2]:.0f} mm"))

    normals = mesh.face_normals
    areas = mesh.area_faces
    zmin = mesh.bounds[0][2]
    face_zmax = mesh.vertices[mesh.faces][:, :, 2].max(axis=1)
    on_bed = (normals[:, 2] < -0.999) & (face_zmax - zmin < 1e-3)

    contact = float(areas[on_bed].sum())
    aspect = ext[2] / max(math.sqrt(contact), 1e-6)
    if contact < 1:
        status = "fail"
    elif contact < rules["min_bed_contact_mm2"] or aspect > rules["max_height_to_base"]:
        status = "warn"
    else:
        status = "pass"
    results.append(_result("bed_contact", status,
                           f"{contact:.0f} mm² flat on the bed, height {aspect:.1f}x the base width "
                           f"(min {rules['min_bed_contact_mm2']} mm², max {rules['max_height_to_base']}x). "
                           "Model the part in print orientation with a flat face at z=0; add a brim or wider base if tall"))

    # Overhangs: downward faces steeper than the limit, measured from vertical, excluding the bed face.
    limit = math.radians(rules["max_overhang_deg"] + 1)  # 45° chamfers themselves are fine
    overhang = (normals[:, 2] < -math.sin(limit)) & ~on_bed
    oh_area = float(areas[overhang].sum())
    pct = 100 * oh_area / float(areas.sum())
    if oh_area < 1:
        results.append(_result("overhangs", "pass", f"none steeper than {rules['max_overhang_deg']}°"))
    else:
        zs = mesh.triangles_center[overhang][:, 2]
        status = "warn" if pct > rules["max_overhang_area_pct"] else "pass"
        results.append(_result("overhangs", status,
                               f"{oh_area:.0f} mm² ({pct:.1f}% of surface) steeper than {rules['max_overhang_deg']}° "
                               f"between z={zs.min():.1f} and z={zs.max():.1f} mm; bridges and holes count here too. "
                               "Chamfer at 45°, teardrop horizontal holes, or plan for supports"))

    # Wall thickness: cast rays inward from sampled surface points.
    thickness = wall_thickness(mesh)
    if thickness.size:
        thin = np.mean(thickness < rules["min_wall_mm"]) * 100
        fragile = np.mean(thickness < rules["warn_wall_mm"]) * 100
        p2 = float(np.percentile(thickness, 2))
        if thin > 1:
            status = "fail" if thin > 5 else "warn"
        elif fragile > 5:
            status = "warn"
        else:
            status = "pass"
        results.append(_result("wall_thickness", status,
                               f"2nd percentile {p2:.2f} mm; {thin:.1f}% of surface under {rules['min_wall_mm']} mm, "
                               f"{fragile:.1f}% under {rules['warn_wall_mm']} mm"))

    density = printer["material"]["density_g_cm3"].get(material, 1.24)
    volume_cm3 = mesh.volume / 1000
    results.append(_result("estimate", "pass",
                           f"{volume_cm3:.1f} cm³ solid; at most {volume_cm3 * density:.0f} g of {material} "
                           "(the slicer's figure with infill will be lower)"))
    return results


def wall_thickness(mesh: trimesh.Trimesh, samples: int = 3000) -> np.ndarray:
    """Distance from each sampled surface point to the opposite wall along the inward normal."""
    points, face_idx = trimesh.sample.sample_surface(mesh, samples, seed=1)
    normals = mesh.face_normals[face_idx]
    origins = points - normals * 1e-3
    locations, ray_idx, _ = mesh.ray.intersects_location(origins, -normals, multiple_hits=False)
    if not len(ray_idx):
        return np.array([])
    return np.linalg.norm(locations - origins[ray_idx], axis=1)


def summarize(results: list[dict]) -> str:
    worst = "pass"
    for r in results:
        if r["status"] == "fail":
            return "fail"
        if r["status"] == "warn":
            worst = "warn"
    return worst
