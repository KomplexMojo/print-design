"""biathlon-stock: see brief.md for requirements.

Rough r1 prototype for fit only. Three parts: rear stock, main body, forestock.

Shooting frame:
  X  forward along the bore, 0 at the trigger blade
  Y  up in the shooting position, 0 on the bore line
  Z  lateral, +Z is always the shooter's RIGHT

`handedness` is the top-level switch. The body-fitted features are modelled on a
"face side" and an "away side", then placed for the shooter:
  face side (cheek)   : cheek piece / comb, thumb rest, cast reference
  away side           : palm swell (bed side of grip), spare-mag holder
  LH -> face side is the shooter's right; RH -> the shooter's left.
Hardware that is NOT mirrored with the shooter keeps its own side parameters:
`bolt_side` (the action's bolt handle). The harness rail goes on the side opposite the
spare-mag holder (the face side), per Darren 2026-11-23. A right-bolt action in a
left-handed stock is therefore modelled correctly, not as a mirror image.

Print orientation is chosen per part after placement, so each part lies with its
flat side on the bed: rear stock and main body with the away side down, forestock
with the face side down (the mag holder is on its away side).

All fit values are estimates for a 178 cm male until Darren's measurement sheet
arrives; hardware values are placeholders until the action and sights are chosen.
"""

import math

from build123d import *

from printloop import fits

# Bump on every change that gets printed, and add a row to brief.md's history.
REVISION = 2
MATERIAL = "PLA"
SLICE_PROFILE = "stock-proto"  # PLA prototype presets (printer/presets/biathlon-stock)

PARAMS = {
    # --- athlete (estimates for a 178 cm male; replace from the measurement sheet) ---
    "handedness": "left",            # S/T: "left" or "right"; flips every body-fitted side
    "bolt_side": "left",              # action's bolt handle side; set from the action, not mirrored
    # Carrying-harness rail: one rail on the side opposite the spare-mag holder (face side).
    # Placeholder mounting: heat-set inserts for a bought rail until the rail is measured (AH, AI).
    "harness_rail_holes": (390.0, 410.0),  # forestock inserts, centred on AH = 400 (front connector)
    "harness_rear_position": -250.0,       # -AI: rear connector on the rear stock
    "harness_rear_y": -60.0,               # bore to rear insert centre line (placeholder)
    "harness_insert_pitch": 20.0,          # two inserts per connector
    "harness_rail_y": -30.0,               # bore to insert centre line
    "insert_hole_d": 6.4,                  # M5 heat-set insert, per insert maker
    "insert_depth": 10.0,
    "bolt_notch": (-62.0, 26.0, 12.0),  # placeholder: x centre, length, depth below the stock top
    "lop": 320.0,                     # trigger blade to butt-plate centre (D, AA)
    "cheek_to_eye": 30.0,             # P
    "comb_length": 185.0,             # butt plate to comb front
    "comb_width": 40.0,               # rear stock thickness at the cheek (IBU cap 40)
    "comb_cast": 0.0,                 # R; rear stock shifted away from the face (cast-off for RH, cast-on for LH)
    "buttplate_length": 150.0,        # U, Y
    "buttplate_drop": 60.0,           # bore to butt-plate centre (AC)
    "buttplate_curve_radius": 150.6,  # E
    "hook_drop": 15.0,                # butt-plate bottom to hook tip, vertical (AF)
    "hook_reach": 20.0,               # hook tip behind the butt plate (AE)
    "hook_thickness": 30.0,           # butt plate face to the hook's underside corner
    "hook_radius": 40.0,              # armpit curve (X)
    "grip_angle_deg": 85.0,
    "grip_length": 85.0,              # grip top to grip bottom (F, G)
    "grip_depth": 40.0,               # front to back (K, M)
    "grip_width": 36.0,
    "grip_chamfer": 11.2,             # gives pi * M = 126 mm circumference (M = 40)
    "trigger_reach": 69.0,            # grip centre to trigger blade (H)
    "thumb_rest_height": 62.0,        # bore to thumb-rest centre (N)
    "thumb_rest_depth": 10.0,
    "handstop_position": 350.0,       # trigger blade to hand-stop face (V, AG)
    "handstop_height": 25.0,          # below the forend
    "handstop_length": 52.0,
    "sling_slot_width": 41.0,         # for a <= 40 mm sling
    "sling_slot_height": 8.0,
    "block_position": 160.0,          # trigger to centre of standing block (Z, AJ)
    "block_height": 130.0,            # bore to block bottom (IBU cap 140)
    "block_length": 90.0,
    "block_ramp": 5.0,                # keeps the block front inside the main body
    # --- stock body ---
    "body_width": 50.0,               # main body and forestock thickness
    "wrist_top": -12.0,               # stock top behind the action
    "forend_depth": 55.0,             # bore to forend bottom
    "forend_tip": 455.0,              # trigger to front of the stock (room for 4 slots)
    "edge_chamfer": 3.0,
    "foot_chamfer": 0.4,
    # --- hardware placeholders (until the action is chosen) ---
    "action_rear": -105.0,
    "action_front": 125.0,
    "action_width": 32.0,
    "bore_above_inlet_floor": 20.0,
    "sight_line_above_bore": 50.0,     # AB + P: puts the comb at the current 20 mm
    "barrel_d": 22.0,
    "barrel_float": 2.0,
    "trigger_slot": (-8.0, 28.0, 12.0),   # x from, x to, width
    "finger_hole": (-42.0, 38.0, -82.0, -45.0),  # x0, x1, y0, y1
    "guard_bottom": 90.0,             # bore to bottom of the (printed) guard loop
    "mag_well": (50.0, 100.0, 22.0),  # x from, x to, width
    "spare_mag": (14.0, 32.0, 50.0),  # placeholder: thickness (vertical in the holder),
                                      # cartridge length (lateral, insertion depth), height (along X)
    # --- spare magazine holder (MC 3.1.6.5.3), on the side away from the face ---
    "mag_holder_count": 4,
    # Layout from the Anschütz 1827F reference: mags lie horizontally, end to end, in flush
    # slots along the forend side near its top edge, pushed in sideways.
    "mag_holder_start": 222.0,        # trigger to rear of the first slot
    "mag_holder_wall": 3.5,           # web between slots
    "mag_holder_top": -17.0,          # bore to top of the slots (clears the barrel channel)
    "mag_finger_notch": (12.0, 5.0, 6.0),  # scallop below each slot: length, depth, height
    "prone_hand_length": 80.0,        # hand behind the hand stop in prone (J)
    # --- IBU marking surface (MC 3.1.6.4 l) ---
    "marking_start": 150.0,           # measured from the trigger
    "marking_length": 50.0,
    "marking_height": 40.0,
    # --- splits and joints ---
    "rear_split": -108.0,
    "front_split": 215.0,
    "rear_tongue": (40.0, 22.0, 22.0, -37.0),   # length, height, width, centre y
    "front_tongue": (30.0, 22.0, 30.0, -40.0),   # tie rods run below the mag slots
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
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def _x_hole(x0, x1, y, z, d, up=1):
    """Hole along X with a 45° teardrop roof toward `up` * Z (print up) so it needs no support."""
    r = d / 2 * up
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ.offset(x0)):
            with Locations((y, z)):
                Circle(abs(r))
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
        (-L + p["hook_thickness"], tip[1] - 8),           # butt / hook underside
        (tip[0] + 6, tip[1] - 6),
        tip,                                              # hook tip
        (-L, butt_bot),                                   # butt plate bottom
    ]
    arcs = {
        len(pts) - 2: _arc_mid(tip, (-L, butt_bot), p["hook_radius"], 1),                # armpit curve
        len(pts) - 1: _arc_mid((-L, butt_bot), (-L, butt_top), p["buttplate_curve_radius"], 1),  # concave butt
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


# ---------------------------------------------------------------- spare magazines

def _holder_box(p):
    """Slot band on the away side: x0, x1, y_bot, y_top, slot depth (lateral), slot length."""
    t, length, h = p["spare_mag"]
    n, wall, snug = p["mag_holder_count"], p["mag_holder_wall"], fits.clearance("snug")
    slot_x = h + 2 * snug
    x0 = p["mag_holder_start"]
    x1 = x0 + n * slot_x + (n + 1) * wall
    y_top = p["mag_holder_top"]
    y_bot = y_top - t - 2 * snug
    return x0, x1, y_bot, y_top, length + snug, slot_x


def spare_mag_pockets(p):
    """Flush slots cut into the away-side face (-Z in the model frame), one mag per slot."""
    x0, x1, y_bot, y_top, depth, slot_x = _holder_box(p)
    wall = p["mag_holder_wall"]
    nl, nd, nh = p["mag_finger_notch"]
    z_face = -p["body_width"] / 2
    cut = Part()
    for i in range(p["mag_holder_count"]):
        px = x0 + wall + i * (slot_x + wall)
        cut += _box(px, px + slot_x, y_bot, y_top, z_face - 1, z_face + depth)
        # scallop under the middle of the slot so a gloved finger can pull the mag
        cx = px + slot_x / 2
        cut += _box(cx - nl / 2, cx + nl / 2, y_bot - nh, y_top, z_face - 1, z_face + nd)
    return cut


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
    block_front = p["block_position"] + p["block_length"] / 2 + p["block_ramp"]
    if block_front > p["front_split"] - 3:
        issues.append(f"Standing block front ({block_front:.0f}) crosses the front joint ({p['front_split']:.0f})")
    x0, x1, y_bot, y_top, depth, _ = _holder_box(p)
    if x0 < m1 + 15 or x0 < p["front_split"] + 5:
        issues.append(f"Spare-mag slots start at {x0:.0f}, inside the marking surface or the front joint")
    if x1 > p["forend_tip"] - 8:
        issues.append(f"Spare-mag slots end at {x1:.0f}, past the forend tip ({p['forend_tip']:.0f})")
    r_ch = p["barrel_d"] / 2 + p["barrel_float"]
    if -y_top - r_ch < 3:
        issues.append(f"Spare-mag slots leave {-y_top - r_ch:.1f} mm under the barrel channel")
    fl, fh_, fw, fy = p["front_tongue"]
    dowel_top = fy + fits.hole(p["cross_dowel_d"], "press") / 2
    if y_bot - dowel_top < 2:
        issues.append(f"Spare-mag slots leave {y_bot - dowel_top:.1f} mm above the joint cross-dowel")
    if -p["body_width"] / 2 + depth > p["body_width"] / 2 - 3:
        issues.append("Spare-mag slots are deeper than the forend is wide")
    if any(m0 - 10 < hx < m1 + 10 for hx in p["harness_rail_holes"]):
        issues.append("MC 3.1.6.4l: a harness-rail insert is in the marking surface")
    if x0 <= p["mag_well"][1]:
        issues.append("MC 3.1.6.5.3: spare-mag holder touches the magazine well")
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

    def channel_and_rods(up):
        """Barrel channel and tie-rod holes, teardropped toward the part's print-up side."""
        cut = _x_hole(p["action_front"] - 1, p["forend_tip"] + 1, 0.0, 0.0, 2 * r_ch, up)
        for z in rod_zs:
            cut += _x_hole(mx1, dowel_x + 8, fy, z, fits.hole(p["bolt_d"], "slide"), up)
            cut += _x_hole(mx1, mx1 + cb_depth, fy, z, cb_d, up)
        return cut
    body -= _z_hole(dowel_x, fy, fits.hole(p["cross_dowel_d"], "press"))

    main = body & _box(rs, fs, -500, 500, -W, W)
    fore = body & _box(fs, 1000, -500, 500, -W, W)
    main -= channel_and_rods(1)
    socket = _box(fs - fl - snug, fs + 1, fy - fh_ / 2 - snug, fy + fh_ / 2 + snug,
                  -fw / 2 - snug, fw / 2 + snug)
    main -= socket
    tongue = _box(fs - fl, fs + 0.5, fy - fh_ / 2, fy + fh_ / 2, -fw / 2, fw / 2)
    fore += tongue
    fore -= spare_mag_pockets(p)
    fore -= channel_and_rods(-1)
    for hx in p["harness_rail_holes"]:      # face side = +Z in the model frame
        fore -= _z_hole(hx, p["harness_rail_y"], p["insert_hole_d"],
                        W / 2 - p["insert_depth"], W / 2 + 1)

    # ---- rear stock (its own width; cast shifts it sideways in the assembly only)
    Wb = p["comb_width"]
    c = p["comb_cast"]  # positive moves the rear stock away from the face (-Z here)
    rear = _soften(_slab(pts, -Wb / 2 - c, Wb / 2 - c, arcs), p["edge_chamfer"])
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

    hp, hy = p["harness_insert_pitch"], p["harness_rear_y"]
    for hx in (p["harness_rear_position"] - hp / 2, p["harness_rear_position"] + hp / 2):
        rear -= _z_hole(hx, hy, p["insert_hole_d"], Wb / 2 - c - p["insert_depth"], Wb / 2 - c + 1)

    # ---- place for the shooter. Everything above is modelled with the face side on +Z
    # (true for a left-hander); a right-hander's stock is the mirror image of that.
    face = 1 if p["handedness"] == "left" else -1
    if face < 0:
        rear, main, fore = (x.mirror(Plane.XY) for x in (rear, main, fore))

    # ---- hardware that is not mirrored with the shooter
    bolt = 1 if p["bolt_side"] == "right" else -1
    bx_, blen, bdep = p["bolt_notch"]
    main -= _box(bx_ - blen / 2, bx_ + blen / 2, -bdep, 5, 0, bolt * W)

    # ---- print orientation: rear and main lie on their away side, forestock on its face side
    def lay(part, bed_side):            # bed_side = +1/-1 lateral side that goes on the bed
        return part if bed_side < 0 else part.rotate(Axis.X, 180)

    return {"rear": lay(rear, -face), "main": lay(main, -face), "fore": lay(fore, face)}


if __name__ == "__main__":
    for name, part in build().items():
        print(name, part.bounding_box().size, part.is_valid)
