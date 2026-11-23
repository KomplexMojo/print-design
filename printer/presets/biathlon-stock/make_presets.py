"""Write the biathlon-stock Bambu Studio user presets (printer, process, filament).

Each preset is a small user preset that `inherits` a Bambu Studio system preset for the
H2S and only overrides what the stock needs. Import the JSON files with
File > Import > Import Configs in Bambu Studio. Edit the tables below, then run
`python printer/presets/biathlon-stock/make_presets.py` to regenerate.

Parent names were checked against Bambu Studio's installed BBL profiles on 2026-11-23.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
VERSION = "2.0.0.0"   # oldest preset format we target; Bambu Studio accepts newer apps reading it

PRINTER_04 = "H2S 0.4 hardened - Stock proto"
PRINTER_06 = "H2S 0.6 hardened - Stock final"
SYS_04 = "Bambu Lab H2S 0.4 nozzle"
SYS_06 = "Bambu Lab H2S 0.6 nozzle"


def x3(v):
    """Per-extruder-variant values (Standard, High Flow, E3D High Flow)."""
    return [str(v)] * 3


def user_preset(kind: str, name: str, inherits: str, settings: dict) -> dict:
    data = {"type": kind, "name": name, "inherits": inherits, "from": "User",
            "instantiation": "true", "is_custom_defined": "0", "version": VERSION}
    data[{"machine": "printer_settings_id", "process": "print_settings_id",
          "filament": "filament_settings_id"}[kind]] = [name] if kind == "filament" else name
    data.update(settings)
    return data


# ------------------------------------------------------------------ printers
PRINTERS = {
    PRINTER_04: (SYS_04, {"nozzle_type": ["hardened_steel"] * 3}),
    PRINTER_06: (SYS_06, {"nozzle_type": ["hardened_steel"] * 3}),
}

# ------------------------------------------------------------------ process
# Shared by every process preset: supports only where painted (inlet ceiling, mag well,
# joint sockets), no prime tower for single-material plates, aligned seam on the back edge.
COMMON = {
    "enable_support": "1",
    "support_type": "tree(manual)",       # only painted enforcers get support
    "support_threshold_angle": "30",
    "support_on_build_plate_only": "0",   # inlet/mag-well ceilings rise from the part itself
    "support_interface_top_layers": "3",
    "support_interface_bottom_layers": "2",
    "support_interface_pattern": "rectilinear",
    "enable_prime_tower": "0",
    "seam_position": "aligned",
    "wall_generator": "classic",
    "xy_hole_compensation": "0",          # hole sizes come from printloop.fits in the CAD
    "xy_contour_compensation": "0",
    "print_sequence": "by layer",
}

PROTO = {   # 0.4 nozzle, 0.24 mm, PLA (indoor fit) or PETG HF (outdoor dry-fire)
    **COMMON,
    "layer_height": "0.24",
    "top_shell_layers": "4",
    "bottom_shell_layers": "4",
    "top_shell_thickness": "0.8",
    "sparse_infill_pattern": "grid",
    "support_top_z_distance": "0.2",
    "support_bottom_z_distance": "0.2",
    "support_object_xy_distance": "0.35",
    "brim_type": "auto_brim",
    "elefant_foot_compensation": "0.15",
}

FINAL = {   # 0.6 hardened nozzle, 0.24 mm, PAHT-CF, strength first
    **COMMON,
    "layer_height": "0.24",
    "top_shell_layers": "7",
    "bottom_shell_layers": "6",
    "top_shell_thickness": "1.6",
    "bottom_shell_thickness": "1.4",
    "sparse_infill_pattern": "gyroid",    # isotropic, no crossing-over-itself weak points
    "infill_wall_overlap": "25%",
    "outer_wall_speed": x3(60),
    "inner_wall_speed": x3(100),
    "sparse_infill_speed": x3(150),
    "internal_solid_infill_speed": x3(120),
    "top_surface_speed": x3(80),
    "initial_layer_speed": x3(30),
    "initial_layer_infill_speed": x3(50),
    "support_top_z_distance": "0.24",
    "support_bottom_z_distance": "0.24",
    "support_object_xy_distance": "0.5",
    "brim_type": "outer_only",
    "brim_object_gap": "0",
    "elefant_foot_compensation": "0.2",
}

PROCESSES = {
    # name: (parent, printer, settings, description)
    "Stock proto rear 0.24 @H2S 0.4": ("0.24mm Standard @BBL H2S", "04", {
        **PROTO, "wall_loops": "3", "sparse_infill_density": "15%", "brim_width": "5"},
        "Biathlon stock rear: prototype. On its side, away side down. PLA or PETG HF."),
    "Stock proto main 0.24 @H2S 0.4": ("0.24mm Standard @BBL H2S", "04", {
        **PROTO, "wall_loops": "4", "sparse_infill_density": "20%",
        "brim_type": "outer_only", "brim_width": "5"},
        "Biathlon stock main body: prototype. Diagonal, on its side. Paint supports in inlet, mag well, joint sockets."),
    "Stock proto fore 0.24 @H2S 0.4": ("0.24mm Standard @BBL H2S", "04", {
        **PROTO, "wall_loops": "3", "sparse_infill_density": "15%", "brim_width": "5"},
        "Biathlon stock forestock: prototype. On its side, face side down."),
    "Stock final rear 0.24 @H2S 0.6": ("0.24mm Balanced Quality @BBL H2S 0.6 nozzle", "06", {
        **FINAL, "wall_loops": "6", "sparse_infill_density": "35%", "brim_width": "8"},
        "Biathlon stock rear: final PAHT-CF. Add 100% modifiers at the tongue, hook root and pad inserts."),
    "Stock final main 0.24 @H2S 0.6": ("0.24mm Balanced Quality @BBL H2S 0.6 nozzle", "06", {
        **FINAL, "wall_loops": "8", "sparse_infill_density": "50%", "brim_width": "10"},
        "Biathlon stock main body: final PAHT-CF. Add 100% modifiers at both joints, pillars and the wrist."),
    "Stock final fore 0.24 @H2S 0.6": ("0.24mm Balanced Quality @BBL H2S 0.6 nozzle", "06", {
        **FINAL, "wall_loops": "6", "sparse_infill_density": "40%", "brim_width": "8"},
        "Biathlon stock forestock: final PAHT-CF. Add 100% modifiers at the dovetail, hand stop and rail inserts."),
    "Stock final ASA accessory 0.24 @H2S 0.6": ("0.24mm Balanced Quality @BBL H2S 0.6 nozzle", "06", {
        **COMMON, "support_type": "tree(auto)", "wall_loops": "4", "top_shell_layers": "5",
        "bottom_shell_layers": "5", "sparse_infill_pattern": "gyroid", "sparse_infill_density": "40%",
        "brim_type": "outer_only", "brim_width": "5"},
        "Biathlon stock accessories in ASA (spacers, covers, cheek shims)."),
    "Stock final TPU pad 0.24 @H2S 0.6": ("0.24mm Balanced Quality @BBL H2S 0.6 nozzle", "06", {
        **COMMON, "enable_support": "0", "wall_loops": "3", "top_shell_layers": "5",
        "bottom_shell_layers": "4", "sparse_infill_pattern": "gyroid", "sparse_infill_density": "20%",
        "outer_wall_speed": x3(30), "inner_wall_speed": x3(40), "sparse_infill_speed": x3(50),
        "initial_layer_speed": x3(20), "brim_type": "no_brim"},
        "Biathlon stock butt pad in TPU 90A, flat on its mounting face. External spool."),
}

# ------------------------------------------------------------------ filament
FILAMENTS = {
    # name: (parent, printer, settings, description)
    "Stock PLA Basic proto @H2S 0.4": ("Bambu PLA Basic @BBL H2S", "04", {},
        "Prototype fit parts, indoors only. AMS 2 Pro, dry 50 C 8 h if opened > 1 week."),
    "Stock PETG HF outdoor @H2S 0.4": ("Bambu PETG HF @BBL H2S", "04", {
        "fan_max_speed": ["40"], "fan_min_speed": ["10"]},
        "Outdoor dry-fire prototypes. AMS 2 Pro, dry 65 C 8 h. Less fan for layer bond."),
    "Stock PAHT-CF final @H2S 0.6": ("Bambu PAHT-CF @BBL H2S 0.6 nozzle", "06", {
        "chamber_temperatures": ["65"], "fan_max_speed": ["20"], "fan_min_speed": ["0"],
        "overhang_fan_speed": ["40"]},
        "Final structural parts. Dry 80 C 12 h in a dryer, print from it via external spool. Glue on plate."),
    "Stock ASA final @H2S 0.6": ("Bambu ASA @BBL H2S 0.6 nozzle", "06", {
        "chamber_temperatures": ["65"], "fan_max_speed": ["25"]},
        "Accessories. AMS 2 Pro, dry 65 C 12 h."),
    "Stock TPU 90A pad @H2S 0.6": ("Bambu TPU 90A @BBL H2S 0.6 nozzle", "06", {},
        "Butt pad. External spool only (soft TPU is not AMS-safe). Dry 65 C 8 h."),
}


def main() -> None:
    printer_names = {"04": [SYS_04, PRINTER_04], "06": [SYS_06, PRINTER_06]}
    out = {}
    for name, (parent, s) in PRINTERS.items():
        out[f"machine/{name}.json"] = user_preset("machine", name, parent, s)
    for name, (parent, p, s, desc) in PROCESSES.items():
        out[f"process/{name}.json"] = user_preset("process", name, parent,
            {**s, "description": desc, "compatible_printers": printer_names[p]})
    for name, (parent, p, s, desc) in FILAMENTS.items():
        out[f"filament/{name}.json"] = user_preset("filament", name, parent,
            {**s, "description": desc, "compatible_printers": printer_names[p]})
    for rel, data in out.items():
        path = HERE / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=4, sort_keys=True) + "\n")
    print(f"wrote {len(out)} presets to {HERE}")


if __name__ == "__main__":
    main()
