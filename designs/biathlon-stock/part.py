"""biathlon-stock: see brief.md for requirements.

Rough r1 prototype for fit only. Three parts: rear stock, main body, forestock.

Frame while modelling (shooting frame = print frame):
  X  forward along the bore, 0 at the trigger blade
  Y  up in the shooting position, 0 on the bore line
  Z  lateral. +Z is the shooter's right for a left-handed stock. In print, Z is up,
     so every part lies on its side with the bed on the -Z face.

A left-handed and a right-handed stock are mirror images, so the printed geometry
is the same for both: the handed features (cheek side, thumb rest) always sit on the
top (+Z) side and the palm side lies flat on the bed. `handedness` only says which
side of the shooter +Z is.

All fit values are estimates for a 178 cm male until Darren's measurement sheet
arrives; hardware values are placeholders until the action and sights are chosen.
"""

import math

from build123d import *

from printloop import fits

# Bump on every change that gets printed, and add a row to brief.md's history.
REVISION = 1
MATERIAL = "PLA"
SLICE_PROFILE = None

PARAMS = {
    # --- athlete (estimates for a 178 cm male; replace from the measurement sheet) ---
    "handedness": "left",            # S/T
    "lop": 335.0,                     # trigger blade to butt-plate centre (D, AA)
    "cheek_to_eye": 27.0,             # P
    "comb_length": 185.0,             # butt plate to comb front
    "comb_width": 40.0,               # rear stock thickness at the cheek (IBU cap 40)
    "comb_cast": 0.0,                 # R; lateral offset of the rear stock (assembly only)
    "buttplate_length": 120.0,        # U, Y
    "buttplate_drop": 60.0,           # bore to butt-plate centre (AC)
    "buttplate_curve_radius": 150.0,  # E
    "hook_drop": 55.0,                # butt-plate bottom to hook tip, vertical (AF)
    "hook_reach": 30.0,               # hook tip behind the butt plate (AE)
    "hook_radius": 40.0,              # armpit curve (X)
    "grip_angle_deg": 85.0,
    "grip_length": 85.0,              # grip top to grip bottom (F, G)
    "grip_depth": 48.0,               # front to back (K, M)
    "grip_width": 40.0,
    "grip_chamfer": 14.0,             # rounds the grip to ~143 mm circumference
    "trigger_reach": 69.0,            # grip centre to trigger blade (H)
    "thumb_rest_height": 62.0,        # bore to thumb-rest centre (N)
    "thumb_rest_depth": 10.0,
    "handstop_position": 380.0,       # trigger blade to hand-stop face (V, AG)
    "handstop_height": 25.0,          # below the forend
    "handstop_length": 52.0,
    "sling_slot_width": 41.0,         # for a <= 40 mm sling
    "sling_slot_height": 8.0,
    "block_position": 150.0,          # trigger to centre of standing block (Z, AJ)
    "block_height": 130.0,            # bore to block bottom (IBU cap 140)
    "block_length": 90.0,
    "block_ramp": 15.0,
    # --- stock body ---
    "body_width": 50.0,               # main body and forestock thickness
    "wrist_top": -12.0,               # stock top behind the action
    "forend_depth": 55.0,             # bore to forend bottom
    "forend_tip": 440.0,              # trigger to front of the stock
    "edge_chamfer": 3.0,
    "foot_chamfer": 0.4,
    # --- hardware placeholders (until the action is chosen) ---
    "action_rear": -105.0,
    "action_front": 125.0,
    "action_width": 32.0,
    "bore_above_inlet_floor": 20.0,
    "sight_line_above_bore": 37.0,
    "barrel_d": 22.0,
    "barrel_float": 2.0,
    "trigger_slot": (-8.0, 28.0, 12.0),   # x from, x to, width
    "finger_hole": (-42.0, 38.0, -82.0, -45.0),  # x0, x1, y0, y1
    "guard_bottom": 90.0,             # bore to bottom of the (printed) guard loop
    "mag_well": (50.0, 100.0, 22.0),  # x from, x to, width
    # --- IBU marking surface (MC 3.1.6.4 l) ---
    "marking_start": 150.0,           # measured from the trigger
    "marking_length": 50.0,
    "marking_height": 40.0,
    # --- splits and joints ---
    "rear_split": -108.0,
    "front_split": 215.0,
    "rear_tongue": (40.0, 22.0, 22.0, -37.0),   # length, height, width, centre y
    "front_tongue": (30.0, 28.0, 30.0, -34.0),
    "bolt_d": 6.0,                    # M6
    "cross_dowel_d": 10.0,
    "tie_rod_spacing": 16.0,          # two M6 rods from the mag well into the forestock
    "tie_rod_counterbore": (11.0, 7.0),
}


# ---------------------------------------------------------------- helpers

def _arc_mid(a, b, radius, inward):
    """Midpoint of an arc from a to b with the given radius, bulging to `inward` side (+1/-1)."""
    (ax, ay), (bx, by) = a, b
    cx, cy = (ax + bx) / 2, (ay + by) / 2
    chord = math.hypot(bx - ax, by - ay)
    s = radius - math.sqrt(max(radius**2 - (chord / 2) ** 2, 0))
    nx, ny = (by - ay) / chord, -(bx - ax) / chord
    return (cx + inward * s * nx, cy + inward * s * ny)


def _slab(points, z0, z1, arcs=None):
    """Extrude a closed XY outline from z0 to z1. `arcs` maps a segment start index to an arc midpoint."""
    arcs = arcs or {}
    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z0)):
            with BuildLine():
                n = len(points)
                for i in range(n):
                    a, b = points[i], points[(i + 1) % n]
                    if i in arcs:
                        ThreePointArc(a, arcs[i], b)
                    else:
                        Line(a, b)
            make_face()
        extrude(amount=z1 - z0)
    return bp.part


def _box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def _x_hole(x0, x1, y, z, d):
    """Hole along X, teardrop pointing +Z (print up) so it needs no support."""
    r = d / 2
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ.offset(x0)):
            with Locations((y, z)):
                Circle(r)
                # 45° teardrop roof toward +Z (sketch's local Y is world Z)
                Polygon((0, r * math.sqrt(2)), (-r / math.sqrt(2), r / math.sqrt(2)),
                        (r / math.sqrt(2), r / math.sqrt(2)), align=None)
        extrude(amount=x1 - x0)
    return bp.part


def _z_hole(x, y, d, z0=-100, z1=100):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0)


def _soften(part, size):
    try:
        return chamfer(part.edges(), size)
    except Exception:
        return part


# ---------------------------------------------------------------- outline

def outline(p):
    L = p["lop"]
    comb_top = p["sight_line_above_bore"] - p["cheek_to_eye"]
    butt_top = -p["buttplate_drop"] + p["buttplate_length"] / 2
    butt_bot = -p["buttplate_drop"] - p["buttplate_length"] / 2
    tip = (-L - p["hook_reach"], butt_bot - p["hook_drop"])
    fd, tipx = p["forend_depth"], p["forend_tip"]
    bx, bl, bh, br = p["block_position"], p["block_length"], p["block_height"], p["block_ramp"]
    gfront = p["finger_hole"][1] + 7
    grip_top_front = -p["trigger_reach"] + p["grip_depth"] / 2

    pts = [
        (-L, butt_top),                                   # 0 heel
        (-L + 12, comb_top),
        (-L + p["comb_length"], comb_top),
        (-L + p["comb_length"] + 25, p["wrist_top"]),
        (p["action_rear"] - 10, p["wrist_top"]),
        (p["action_rear"], 0.0),
        (tipx - 8, 0.0),
        (tipx, -8.0),
        (tipx, -fd + 5),
        (tipx - 5, -fd),
        (bx + bl / 2 + br, -fd),                          # standing block
        (bx + bl / 2, -bh),
        (bx - bl / 2, -bh),
        (bx - bl / 2 - br, -fd),
        (gfront, -fd),                                    # trigger guard loop
        (gfront - 5, -p["guard_bottom"]),
        (grip_top_front, -p["guard_bottom"]),
        (grip_top_front, -55.0),
        (-p["trigger_reach"] - p["grip_depth"] / 2 - 7, -55.0),   # wrist underside
        (-130.0, -52.0),
        (-L + 60, butt_bot - 15),                         # butt underside
        (-L + 25, butt_bot - p["hook_drop"] + 5),         # hook underside
        (tip[0] + 8, tip[1] - 6),
        tip,                                              # 23 hook tip
        (-L, butt_bot),                                   # 24 butt plate bottom
    ]
    arcs = {
        23: _arc_mid(tip, (-L, butt_bot), p["hook_radius"], 1),                # armpit curve
        24: _arc_mid((-L, butt_bot), (-L, butt_top), p["buttplate_curve_radius"], 1),  # concave butt
    }
    return pts, arcs


def grip(p):
    top = -50.0
    bottom = top - p["grip_length"]
    lean = math.tan(math.radians(90 - p["grip_angle_deg"])) * p["grip_length"]
    front = -p["trigger_reach"] + p["grip_depth"] / 2
    back = front - p["grip_depth"]
    z0 = -p["body_width"] / 2
    z1 = z0 + p["grip_width"]
    pts = [(front, top), (back, top), (back - lean, bottom + 6),
           (back - lean + 6, bottom), (front - lean - 4, bottom), (front - lean, bottom + 4)]
    g = _slab(pts, z0, z1)
    # Round the grip: chamfer the four long edges that run down the grip.
    long_edges = g.edges().filter_by(lambda e: abs(e.tangent_at(0.5).Y) > 0.9)
    try:
        g = chamfer(long_edges, p["grip_chamfer"])
    except Exception:
        pass
    # Thumb rest pad on the +Z (thumb) side.
    y = -p["thumb_rest_height"]
    pad = _box(back + 6, front - 4, y - 6, y + 6, z1 - 1, z1 + p["thumb_rest_depth"])
    return g + _soften(pad, 2)


# ---------------------------------------------------------------- IBU checks

def ibu_checks(p) -> list[str]:
    """Return a list of rule problems (empty when all computed checks pass)."""
    issues = []
    depth = max(p["forend_depth"], p["block_height"], p["guard_bottom"],
                p["forend_depth"] + p["handstop_height"])
    if depth > 140:
        issues.append(f"MC 3.1.6.4a: depth below bore {depth:.0f} mm > 140 mm")
    if p["comb_width"] > 40:
        issues.append(f"MC 3.1.6.4b: cheek piece {p['comb_width']:.0f} mm > 40 mm")
    m0, m1 = p["marking_start"], p["marking_start"] + p["marking_length"]
    if p["front_split"] < m1 + 15:
        issues.append(f"MC 3.1.6.4l: front joint at {p['front_split']:.0f} is inside or within 15 mm of the marking surface ({m0:.0f}-{m1:.0f})")
    if p["forend_depth"] - 2 * p["edge_chamfer"] < p["marking_height"]:
        issues.append("MC 3.1.6.4l: flat side of the forend is under 40 mm high")
    if p["sling_slot_width"] - 1 > 40:
        issues.append("MC 3.1.6.4h: sling slot implies a sling wider than 40 mm")
    return issues


# ---------------------------------------------------------------- build

def build(p: dict = PARAMS):
    for issue in ibu_checks(p):
        print("IBU ⚠️ ", issue)

    W = p["body_width"]
    pts, arcs = outline(p)
    rs, fs = p["rear_split"], p["front_split"]
    snug = fits.clearance("snug")
    loose = fits.clearance("loose")
    slide = fits.clearance("slide")

    # ---- main body + forestock as one slab, cut, then split
    body = _soften(_slab(pts, -W / 2, W / 2, arcs), p["edge_chamfer"])
    body = body & _box(rs, 1000, -500, 500, -W, W)
    body += grip(p)
    hs0 = p["handstop_position"]
    hs = _box(hs0, hs0 + p["handstop_length"], -p["forend_depth"] - p["handstop_height"],
              -p["forend_depth"] + 2, -W / 2, W / 2)
    body += _soften(hs, 3)

    floor = -p["bore_above_inlet_floor"]
    aw = p["action_width"] + 2 * loose
    body -= _box(p["action_rear"], p["action_front"], floor, 5, -aw / 2, aw / 2)
    tx0, tx1, tw = p["trigger_slot"]
    body -= _box(tx0, tx1, p["finger_hole"][3] - 1, floor + 1, -tw / 2 - loose, tw / 2 + loose)
    fx0, fx1, fy0, fy1 = p["finger_hole"]
    with BuildPart() as fh:
        with BuildSketch(Plane.XY.offset(-W)):
            with Locations(((fx0 + fx1) / 2, (fy0 + fy1) / 2)):
                RectangleRounded(fx1 - fx0, fy1 - fy0, 10)
        extrude(amount=2 * W)
    body -= fh.part
    mx0, mx1, mw = p["mag_well"]
    body -= _box(mx0 - slide, mx1 + slide, -p["forend_depth"] - 1, floor + 1,
                 -mw / 2 - slide, mw / 2 + slide)
    r_ch = p["barrel_d"] / 2 + p["barrel_float"]
    body -= _x_hole(p["action_front"] - 1, p["forend_tip"] + 1, 0.0, 0.0, 2 * r_ch)
    body -= _box(p["action_front"] - 1, p["forend_tip"] + 1, 0, 50, -r_ch, r_ch)
    sx0 = hs0 + (p["handstop_length"] - p["sling_slot_width"]) / 2
    sy = -p["forend_depth"] - p["handstop_height"] / 2
    with BuildPart() as slot:
        with BuildSketch(Plane.XY.offset(-W)):
            with Locations((sx0 + p["sling_slot_width"] / 2, sy)):
                RectangleRounded(p["sling_slot_width"], p["sling_slot_height"], 3)
        extrude(amount=2 * W)
    body -= slot.part

    # Front joint: forestock tongue into a main-body socket, pulled together by two
    # M6 tie rods whose heads sit in the mag well's front wall (outside the marking surface)
    # and whose nuts are steel cross-dowels in the forestock.
    fl, fh_, fw, fy = p["front_tongue"]
    cb_d, cb_depth = p["tie_rod_counterbore"]
    rod_zs = (-p["tie_rod_spacing"] / 2, p["tie_rod_spacing"] / 2)
    dowel_x = fs + 35
    rod_holes = Part()
    for z in rod_zs:
        rod_holes += _x_hole(mx1, dowel_x + 8, fy, z, fits.hole(p["bolt_d"], "slide"))
        rod_holes += _x_hole(mx1, mx1 + cb_depth, fy, z, cb_d)
    body -= rod_holes
    body -= _z_hole(dowel_x, fy, fits.hole(p["cross_dowel_d"], "press"))

    main = body & _box(rs, fs, -500, 500, -W, W)
    fore = body & _box(fs, 1000, -500, 500, -W, W)
    socket = _box(fs - fl - snug, fs + 1, fy - fh_ / 2 - snug, fy + fh_ / 2 + snug,
                  -fw / 2 - snug, fw / 2 + snug)
    main -= socket
    tongue = _box(fs - fl, fs + 0.5, fy - fh_ / 2, fy + fh_ / 2, -fw / 2, fw / 2)
    tongue -= rod_holes
    fore += tongue

    # ---- rear stock (its own width; cast shifts it sideways in the assembly only)
    Wb = p["comb_width"]
    rear = _soften(_slab(pts, -Wb / 2, Wb / 2, arcs), p["edge_chamfer"])
    rear = rear & _box(-1000, rs, -500, 500, -W, W)
    rl, rh, rw, ry = p["rear_tongue"]
    rtongue = _box(rs - 0.5, rs + rl, ry - rh / 2, ry + rh / 2, -rw / 2, rw / 2)
    rear += rtongue
    main -= _box(rs - 1, rs + rl + snug, ry - rh / 2 - snug, ry + rh / 2 + snug,
                 -rw / 2 - snug, rw / 2 + snug)
    bolt = fits.hole(p["bolt_d"], "slide")
    for bxp in (rs + 10, rs + rl - 10):
        main -= _z_hole(bxp, ry, bolt)
        rear -= _z_hole(bxp, ry, bolt)

    return {"rear": rear, "main": main, "fore": fore}


if __name__ == "__main__":
    for name, part in build().items():
        print(name, part.bounding_box().size, part.is_valid)
