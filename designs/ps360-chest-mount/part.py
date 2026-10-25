"""ps360-chest-mount: replacement camera mount for the Insta360 chest strap.

A round, keyed disc that the strap's connector screw clamps to the chest plate,
with a 3-prong GoPro-style clevis on its rim for the camera arm. See brief.md and
schematic.png.

Modeled in a design frame first (Z is the disc axis, back face on z=0, the clevis
on +Y, pivot axis along X), then turned into the print orientation chosen by
`orientation`:
  "side": clevis plane flat on the bed, so layers run along the prongs and through
          their roots (the original snapped across its layers there). Needs supports.
  "flat": back face on the bed. Prints with almost no support but puts layer lines
          across the prong roots.
"""

from build123d import *

from printloop import fits

# Bump on every change that gets printed, and add a row to brief.md's history.
REVISION = 1
MATERIAL = "PETG"
SLICE_PROFILE = "petg-strong"

# Every dimension a print might prove wrong belongs here, in mm.
# Most come from calliper beam-scale readings (±0.5); see the brief's open questions.
PARAMS = {
    # Disc
    "disc_od": 30.7,
    "plate_t": 3.6,               # disc plate, back face to the front face around the hub
    "hub_d": 15.5,                # raised front hub (photo scale, ±2)
    "hub_h": 2.2,                 # plate_t + hub_h = 5.8 overall
    "connector_screw_d": 11.0,    # assumed: original hole 11.8 is this plus a loose fit
    # Back face, against the chest plate
    "key_ring_d": 22.4,           # keyed ring standing 1 mm proud of the back face, into the chest plate
    "key_ring_h": 1.0,            # Darren: the ring sits 1 mm below the back face
    "key_tab_w": 3.0,             # guess: width of the chest plate's slots for the two tabs
    "key_tab_len": 1.0,           # guess: how far each tab sticks out past the ring
    "key_tab_angle": 0.0,         # degrees from the clevis direction; photo shows a tab toward the clevis
    "sink_d": 15.0,               # sunken surface inside the ring, around the screw hole (photo scale, ±1)
    "sink_depth": 1.5,            # guess: how far that surface sits below the ring's face
    "rim_step_w": 1.0,            # guess: relief step around the back outer edge
    "rim_step_h": 0.5,            # guess; 0 removes it
    # Clevis (3 prongs, pivot axis parallel to the disc face)
    "prong_t": 3.4,
    "arm_prong_t": 2.9,           # assumed: camera arm's prong, so the gap matches the original 3.4
    "pivot_from_axis": 15.0,      # Darren, measured
    "pivot_from_back": 21.75,     # 28.7 back face to lobe tip, less the lobe radius
    "lobe_r": 6.95,
    "thumbscrew_d": 5.0,          # M5 thumbscrew shank
    "arm_lobe_r": 6.95,           # assumed: the camera arm's lobe matches ours
    "prong_root_fillet": 1.2,     # the original snapped at a sharp prong root
    "waist_from_back": 10.8,      # narrowest point of the arm (photo scale, ±2)
    "waist_inner_from_axis": 11.5,
    "waist_fillet": 6.0,
    "arm_root_fillet": 2.5,       # inside fillet where the arm meets the plate
    # Cosmetic and print setup
    "index_mark_w": 0.8,
    "index_mark_len": 4.0,
    "index_mark_depth": 0.4,
    "orientation": "side",        # "side" or "flat", see the docstring
    "bed_flat": 0.6,              # side only: flat on the disc rim so it sits on the bed
    "foot_chamfer": 0.4,          # counters elephant's foot on the first layer
}


def clevis_width(p: dict) -> float:
    return 3 * p["prong_t"] + 2 * gap_width(p)


def gap_width(p: dict) -> float:
    return p["arm_prong_t"] + 2 * fits.clearance("slide")


def arm_profile(p: dict) -> Sketch:
    """Side profile of the arm in the design YZ plane, as a sketch on Plane.YZ (local x = Y, y = Z)."""
    rim_r = p["disc_od"] / 2
    py, pz = p["pivot_from_axis"], p["pivot_from_back"]
    # Outer edge: one arc centred on the disc axis, level with the pivot, tangent to the lobe.
    outer_r = py + p["lobe_r"]
    leave_z = pz - (outer_r**2 - rim_r**2) ** 0.5  # where the arc leaves the rim (≈ 6.1)
    lobe_in = py - p["lobe_r"]
    waist = (p["waist_inner_from_axis"], p["waist_from_back"])
    root = (p["hub_d"] / 2, p["plate_t"])
    with BuildSketch(Plane.YZ) as sk:
        with BuildLine():
            Line((root[0], 0), (rim_r, 0))
            Line((rim_r, 0), (rim_r, leave_z))
            RadiusArc((rim_r, leave_z), (outer_r, pz), -outer_r)
            CenterArc((py, pz), p["lobe_r"], 0, 180)
            Line((lobe_in, pz), waist)
            Line(waist, root)
            Line(root, (root[0], 0))
        make_face()
        verts = sk.vertices()
        fillet(verts.filter_by_position(Axis.X, waist[0] - 0.01, waist[0] + 0.01), p["waist_fillet"])
        fillet(sk.vertices().filter_by_position(Axis.Y, root[1] - 0.01, root[1] + 0.01)
               .filter_by_position(Axis.X, root[0] - 0.01, root[0] + 0.01), p["arm_root_fillet"])
    return sk.sketch


def build_design_frame(p: dict) -> Part:
    rim_r = p["disc_od"] / 2
    width = clevis_width(p)
    gap = gap_width(p)
    ring_d = fits.shaft(p["key_ring_d"], "slide")
    tab_w = fits.shaft(p["key_tab_w"], "slide")
    pivot = (0, p["pivot_from_axis"], p["pivot_from_back"])

    with BuildPart() as part:
        # Disc plate and front hub
        Cylinder(rim_r, p["plate_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, 0, p["plate_t"])):
            Cylinder(p["hub_d"] / 2, p["hub_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Clevis arm: the side profile extruded across all three prongs
        add(extrude(arm_profile(p), amount=width / 2, both=True))

        # Gaps for the camera arm's two prongs. The cutter is a puck around the pivot whose
        # rims are rounded, which leaves a fillet at every prong root instead of a sharp corner.
        slot_r = p["arm_lobe_r"] + fits.clearance("loose") + p["prong_root_fillet"]
        for sx in (-1, 1):
            x = sx * (p["prong_t"] + gap) / 2
            with BuildPart(mode=Mode.PRIVATE) as cutter:
                with Locations(Location(pivot[:0] + (x,) + pivot[1:], (0, 90, 0))):
                    Cylinder(slot_r, gap)
                fillet(cutter.edges().filter_by(GeomType.CIRCLE), p["prong_root_fillet"] - 0.01)
            add(cutter.part, mode=Mode.SUBTRACT)

        # Pivot hole for the thumbscrew, through all three prongs
        pivot_d = fits.hole(p["thumbscrew_d"], "slide")
        with Locations(Location(pivot, (0, 90, 0))):
            Cylinder(pivot_d / 2, width + 2, mode=Mode.SUBTRACT)
            if p["orientation"] == "flat":
                # Horizontal hole when printed flat: teardrop point toward +Z (design frame)
                with Locations(Location((-pivot_d / 2 * 0.7071, 0, 0), (0, 0, 45))):
                    Box(pivot_d / 2, pivot_d / 2, width + 2, mode=Mode.SUBTRACT,
                        align=(Align.CENTER, Align.CENTER, Align.CENTER))


        # Back face: keyed ring with two tabs 180° apart, standing proud into the chest plate
        with Locations((0, 0, -p["key_ring_h"])):
            Cylinder(ring_d / 2, p["key_ring_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
            for a in (p["key_tab_angle"], p["key_tab_angle"] + 180):
                with Locations(Location((0, 0, 0), (0, 0, a))):
                    with Locations((0, ring_d / 2 + p["key_tab_len"] / 2 - 0.5, 0)):
                        Box(tab_w, p["key_tab_len"] + 1, p["key_ring_h"],
                            align=(Align.CENTER, Align.CENTER, Align.MIN))
            # Sunken surface inside the ring
            Cylinder(p["sink_d"] / 2, p["sink_depth"], mode=Mode.SUBTRACT,
                     align=(Align.CENTER, Align.CENTER, Align.MIN))
        if p["rim_step_h"] > 0:
            with BuildSketch():
                Circle(rim_r + 5)
                Circle(rim_r - p["rim_step_w"], mode=Mode.SUBTRACT)
            extrude(amount=p["rim_step_h"], mode=Mode.SUBTRACT)

        # Centre hole for the connector screw
        Cylinder(fits.hole(p["connector_screw_d"], "loose") / 2, 20, mode=Mode.SUBTRACT)

        # Front index mark on the rim opposite the clevis
        with Locations((0, -(rim_r - 1 - p["index_mark_len"] / 2), p["plate_t"])):
            Box(p["index_mark_w"], p["index_mark_len"], 2 * p["index_mark_depth"], mode=Mode.SUBTRACT)

        if p["orientation"] == "side":
            # Flat on the disc rim at -X so the part stands on the bed
            with Locations((-rim_r, 0, 0)):
                Box(2 * p["bed_flat"], 40, 40, mode=Mode.SUBTRACT)
        else:
            # The ring is what touches the bed; chamfer its outer edge and the screw hole's
            chamfer(part.edges().group_by(Axis.Z)[0], p["foot_chamfer"])
    return part.part


def build(p: dict = PARAMS):
    """Return the part in its print orientation (build.py drops it onto z=0)."""
    part = build_design_frame(p)
    if p["orientation"] == "side":
        part = part.rotate(Axis.Y, -90)  # -X, the rim flat, goes down onto the bed
    elif p["orientation"] != "flat":
        raise ValueError(f"orientation must be 'side' or 'flat', not {p['orientation']!r}")
    return part


if __name__ == "__main__":
    # Live preview in the OCP CAD Viewer (VS Code) if it is installed.
    try:
        from ocp_vscode import show
        show(build())
    except ImportError:
        print(build().bounding_box())
