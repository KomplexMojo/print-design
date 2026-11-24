"""Fusion 360 script: build the demo stock from the User Parameters ("Hybrid" restyle).

Run after fusion_load_params.py in the same design. Every sketch point is pinned by two
driving dimensions whose expressions are User Parameter expressions, so changing a
parameter (or re-running the loader with a new fit record) moves the geometry. Features
(extrudes, fillets, chamfers) take their sizes from parameter expressions too. Nothing is
typed as a number except the sketch datum (a fixed point 1000 mm below and behind the
trigger, so every dimension stays positive whatever sign a coordinate has).

Layout (see README.md §5 and §10):
  root      = skeleton: user parameters, the side-outline sketch with the two split lines
  rear_stock / main_body / forestock = rigid components (PAHT-CF); each extrudes its own
              region of the shared outline and adds its own features
  action_cradle = the only part that touches the barrelled action: receiver bed, bedding-screw pillars,
              trigger slot and magazine well. Its dimensions are the act_* parameters, which the loader
              fills from the preset for the fit record's action type (stock_params.ACTIONS). It drops into
              a pocket of fixed section in the main body and is fused to it for printing (FUSE_ACTION).
  tpu_grip / tpu_prone_pad = soft parts (TPU) carried on rigid cores; grip_cap locks the sleeve
  hardware_M6 = bolts and nuts, for reading the joints only

Style ("Hybrid", Darren 2026-11-24): flowing rigid surfaces (profile corners rounded with
parameter radii, a faceted and rounded belly under the forend, rounded side edges) combined
with straight-edged geometric windows (truss windows in the butt, the block window, the row
of spare-mag slots).

Handedness: every lateral feature uses face_side / bolt_dir signed planes and distances.
Nothing is mirrored.

Demo shortcuts (flag in the doc, not in the print model): no teardrop holes, no trigger slot,
no front harness mount, grip and pad surfaces are smooth (no finger grooves or texture yet).
"""

import math
import os
import sys

import adsk.core
import adsk.fusion

DATUM = 1000.0  # mm
FUSE_ACTION = False  # True joins the action cradle into the main body (the printed part); False keeps it apart for review

# r2 values (PR 3) that differ from the r1 registry defaults: written as [manual] so the
# loader leaves them alone on the next run. New demo-only shape parameters are [demo].
DEMO_PARAMS = [
    ("sight_line_above_bore", "mm", "50 mm", "[manual] r2: AB + P puts the comb at the current 20 mm"),
    ("forend_tip", "mm", "455 mm", "[manual] r2: room for four flush slots"),
    ("forend_depth", "mm", "62 mm", "[manual] restyle: 6 mm webs above and below the mag slots; IBU MC 3.1.6.4 a"),
    ("grip_depth", "mm", "40 mm", "[manual] r2: from grip_circumference"),
    ("grip_width", "mm", "36 mm", "[manual] r2"),
    ("grip_length", "mm", "80 mm", "[manual] Darren 2026-11-24: 5 mm of margin to the 140 mm line (chk_depth_grip)"),
    ("grip_angle_deg", "deg", "78 deg", "[manual] restyle: raked like current biathlon grips"),
    ("mag_holder_start", "mm", "222 mm", "[manual] r2 flush slots"),
    ("mag_holder_wall", "mm", "3.5 mm", "[manual] r2 web between slots"),
    ("mag_holder_top", "mm", "-19 mm", "[manual] restyle: 6 mm web under the barrel channel"),
    ("min_wall", "mm", "6 mm", "[demo] thinnest structural web allowed in PAHT-CF"),
    # ---- body section
    ("body_round", "mm", "6 mm", "[demo] edge round on the side faces of every rigid part"),
    ("belly_w", "mm", "12 mm", "[demo] belly facet under the forend: width taken off the bottom face"),
    ("belly_h", "mm", "8 mm", "[demo] belly facet: height taken off the side face"),
    ("chk_mark_round", "mm", "forend_depth - body_round - belly_h - 2 mm - marking_height",
     "[demo] MC 3.1.6.4 l: flat side of the forend stays >= 40 mm high after rounding and the belly facet"),
    ("tip_round", "mm", "8 mm", "[demo] forend nose and hook corner"),
    ("tip_rake", "mm", "6 mm", "[demo] forend nose leans back by this much"),
    ("tip_depth", "mm", "38 mm", "[demo] bore to the bottom of the forend nose"),
    ("comb_nose", "mm", "12 mm", "[demo] heel to comb, and comb to wrist ramps"),
    ("comb_front_r", "mm", "14 mm", "[demo] round where the comb turns down to the wrist"),
    ("hook_thickness", "mm", "30 mm", "[demo] butt face to the hook's underside corner"),
    ("hook_round", "mm", "6 mm", "[demo]"),
    ("butt_bot_y", "mm", "-buttplate_drop - buttplate_length / 2", "[demo] derived: bore to butt-plate toe"),
    ("hook_tip_y", "mm", "butt_bot_y - hook_drop", "[demo] derived"),
    # ---- wrist and grip
    ("wrist_ramp", "mm", "7 mm", "[demo]"),
    ("wrist_heel_x", "mm", "-130 mm", "[demo]"),
    ("wrist_heel_y", "mm", "-52 mm", "[demo]"),
    ("wrist_heel_r", "mm", "40 mm", "[demo] sweep from the wrist into the butt underside"),
    ("grip_top_y", "mm", "-55 mm", "[demo] derived: the grip hangs from the wrist underside"),
    ("grip_lean", "", "tan(90 deg - grip_angle_deg)", "[demo] grip lean per mm of height"),
    ("grip_front_x", "mm", "-trigger_reach + grip_depth / 2", "[demo] derived: grip front at its top"),
    ("grip_offset", "mm", "0 mm", "[demo] grip centre offset toward the away (palm) side"),
    ("wrist_facet_w", "mm", "(body_width - grip_width) / 2 - 1 mm", "[demo] derived: facet that narrows the wrist underside to the grip width"),
    ("wrist_facet_h", "mm", "12 mm", "[demo] wrist facet height up the side"),
    ("grip_z0", "mm", "-face_side * (grip_offset + grip_width / 2)", "[demo] derived: away-side skin of the grip"),
    ("grip_round", "mm", "(2 * (grip_depth + grip_width) - grip_circumference) / (8 - 2 * PI)",
     "[demo] derived: corner round that makes the grip girth equal grip_circumference (PI * M)"),
    ("grip_back_r", "mm", "160 mm", "[demo] palm swell: arc of the grip's back"),
    ("chk_grip_round", "mm", "grip_width / 2 - grip_round - 1 mm", "[demo] the girth round fits the grip width"),
    ("chk_depth_grip", "mm", "ibu_depth_max + grip_top_y - grip_length",
     "[demo] MC 3.1.6.4 a read strictly: grip bottom within 140 mm of the bore"),
    # ---- trigger guard and standing block (Darren 2026-11-24: the block is an extension of the guard base)
    ("guard_bottom", "mm", "83 mm", "[manual] rework: guard raised tight under the body so the hand wraps the grip; IBU MC 3.1.6.4 a"),
    ("guard_front_x", "mm", "34 mm", "[demo] front of the guard's front leg, behind the mag well"),
    ("guard_bar", "mm", "10 mm", "[demo] trigger-guard rail thickness (carries the block mount insert)"),
    ("guard_rake", "mm", "10 mm", "[demo] guard front leg thickness over the bar"),
    ("guard_width", "mm", "18 mm", "[demo] trigger-guard width"),
    ("guard_round", "mm", "3 mm", "[demo] edge round on the guard"),
    ("rel_front_x", "mm", "guard_front_x - guard_rake - guard_bar", "[demo] derived: front of the trigger opening"),
    ("finger_hole_x1", "mm", "rel_front_x", "[manual] trigger opening front"),
    ("finger_clear", "mm", "28 mm", "[demo] room for the gloved fingers between the grip front and the default block"),
    ("blk_rear_x", "mm", "grip_front_x - grip_lean * (grip_top_y + guard_bottom) + finger_clear",
     "[demo] derived: rear face of the standing block"),
    ("blk_rake", "mm", "10 mm", "[demo] block rear face is undercut by this much, for the fingers"),
    ("blk_front_rake", "mm", "2 mm", "[demo] block and front-leg face lean (near vertical)"),
    ("block_slot_r", "mm", "10 mm", "[demo] end radius of the oblong slot through the block"),
    ("block_width", "mm", "40 mm", "[demo] standing block width"),
    ("block_round", "mm", "8 mm", "[demo] edge round on the block"),
    ("block_corner_r", "mm", "14 mm", "[demo] round of the block's bottom corners"),
    ("blk_win_web", "mm", "9 mm", "[demo] material round the block window"),
    ("block_length", "mm", "guard_front_x - blk_rear_x",
     "[manual] restyle: derived, the block spans from the finger clearance to the guard front"),
    ("block_position", "mm", "(guard_front_x + blk_rear_x) / 2",
     "[manual] restyle: derived, the block sits under the trigger guard (m_AJ is kept for reference only)"),
    ("saddle_h", "mm", "4 mm", "[demo] the block's saddle wraps this far up the guard rail (locates it and stops it turning)"),
    ("block_bolt_x", "mm", "block_position", "[demo] derived: the single M5 block bolt, into a heat-set insert in the rail"),
    ("block_insert_depth", "mm", "guard_bar - 2 mm", "[demo] derived: insert hole depth in the rail"),
    ("chk_block_mag", "mm", "mag_well_x0 - fit_slide - guard_front_x - 2 mm",
     "[demo] the block and guard stay behind the magazine well, so the magazine drops free"),
    # ---- hand stop
    ("hs_rake", "mm", "14 mm", "[demo] hand-stop front face leans by this much"),
    ("sling_tab_w", "mm", "40 mm", "[demo] Biatar sling end tab width (Darren, measured 2026-11-24)"),
    ("sling_hole_d", "mm", "5.5 mm", "[demo] Biatar sling eyelet (Darren, measured): M5 thumb screw"),
    ("sling_hole_inset", "mm", "17 mm", "[demo] PLACEHOLDER (estimated from a photo): tab tip to eyelet centre"),
    ("sling_seat_d", "mm", "2 mm", "[demo] depth of the sling seat"),
    ("sling_seat_r", "mm", "(sling_tab_w + 1 mm) / 2", "[demo] derived: the seat's semicircular end, matching the tab's round tip"),
    ("sling_tip_x", "mm", "handstop_position + handstop_length - tip_round - 2 mm", "[demo] derived: where the tab's tip sits"),
    ("sling_hole_x", "mm", "sling_tip_x - sling_hole_inset", "[demo] derived: sling screw insert"),
    ("hs_width", "mm", "sling_tab_w + 8 mm", "[demo] derived: hand-stop width, 4 mm of shoulder each side of the sling seat"),
    ("chk_hs_width", "mm", "body_width - hs_width", "[demo] the hand stop is no wider than the forend"),
    ("hs_round", "mm", "4 mm", "[demo]"),
    ("tip_sweep_x", "mm", "handstop_position + handstop_length + hs_rake + 14 mm", "[demo] derived: where the forend underside turns up to the nose"),
    # ---- spare-mag slots
    ("mag_slot_len", "mm", "spare_mag_h + 2 * fit_snug", "[demo] slot along X (mags lie horizontally)"),
    ("mag_slot_h", "mm", "spare_mag_t + 2 * fit_snug", "[demo] slot height"),
    ("mag_slot_depth", "mm", "spare_mag_l + fit_snug", "[demo] lateral insertion depth"),
    ("chk_slot_channel", "mm", "-(barrel_d / 2 + barrel_float) - mag_holder_top - min_wall",
     "[demo] web between the barrel channel and the mag slots >= min_wall"),
    # ---- skeleton butt: full-width comb beam and plate post, slim frame between, truss windows
    ("plate_thickness", "mm", "14 mm", "[demo] butt-plate post, measured from the deepest point of the concave face"),
    ("comb_beam_h", "mm", "28 mm", "[demo] top beam that carries the cheek (full comb_width)"),
    ("frame_web", "mm", "12 mm", "[demo] lower strut and window margins"),
    ("frame_rib", "mm", "10 mm", "[demo] rib width between the windows (measured along X)"),
    ("frame_width", "mm", "24 mm", "[demo] thickness of the slim frame between the comb beam and the plate post"),
    ("rib_lean", "", "0.5", "[demo] ribs lean back by this much per mm of height (near square to the lower strut)"),
    ("win_round", "mm", "5 mm", "[demo] corner round of the geometric windows"),
    ("slim_cove", "mm", "5 mm", "[demo] cove where the slim frame meets the comb beam"),
    ("butt_sagitta", "mm", "buttplate_curve_radius - sqrt(buttplate_curve_radius * buttplate_curve_radius - buttplate_length * buttplate_length / 4)",
     "[demo] derived: depth of the concave butt face"),
    ("rs_low_slope", "", "(wrist_heel_y - (hook_tip_y - tip_round)) / (wrist_heel_x - (-lop + hook_thickness))",
     "[demo] derived: slope of the butt underside"),
    ("rs_web_v", "mm", "frame_web * sqrt(1 + rs_low_slope * rs_low_slope)", "[demo] derived: strut width measured vertically"),
    ("rs_strut_c", "mm", "wrist_heel_y + rs_web_v - rs_low_slope * wrist_heel_x", "[demo] derived: strut upper edge at x = 0"),
    ("rs_win_top", "mm", "comb_top - comb_beam_h", "[demo] derived: top of the windows"),
    ("rs_win_rear_x", "mm", "-lop + butt_sagitta + plate_thickness", "[demo] derived: front face of the plate post"),
    ("rs_win_front_x", "mm", "-lop + comb_length - frame_web", "[demo] derived: front of the front window"),
    ("rs_rib1_x", "mm", "rs_win_rear_x + 0.26 * (rs_win_front_x - rs_win_rear_x)", "[demo] derived: rear rib centre at the window top"),
    ("rs_rib2_x", "mm", "rs_win_rear_x + 0.58 * (rs_win_front_x - rs_win_rear_x)", "[demo] derived: front rib centre at the window top"),
    ("rs_win_low_y", "mm", "butt_bot_y + frame_web", "[demo] derived: lowest window edge, above the toe"),
    ("rs_win_low_x", "mm", "wrist_heel_x + (rs_win_low_y - wrist_heel_y - rs_web_v) / rs_low_slope",
     "[demo] derived: where the window bottom meets the strut"),
    # ---- bolted tongue joints (Darren 2026-11-23): two fasteners per joint along X, hex nuts in the main body
    ("joint_head_d", "mm", "10 mm", "[demo] M6 socket-head diameter"),
    ("joint_head_clear", "mm", "1 mm", "[demo] clearance round the head in its cavity"),
    ("nut_af", "mm", "10 mm", "[demo] M6 nut across flats"),
    ("nut_m", "mm", "5 mm", "[demo] M6 nut thickness"),
    ("nut_slot_af", "mm", "nut_af + 2 * fit_snug", "[demo] slot across flats: snug, so the nut cannot turn"),
    ("nut_slot_len", "mm", "nut_m + 2 * fit_snug", "[demo] slot length along the bolt"),
    ("bolt_tail", "mm", "8 mm", "[demo] bolt end past the nut slot"),
    ("rear_tongue_height", "mm", "24 mm", "[manual] bolted joint"),
    ("rear_tongue_width", "mm", "34 mm", "[manual] bolted joint: both bolts inside the tongue"),
    ("rear_tongue_y", "mm", "-36 mm", "[manual] bolted joint: below the action inlet floor"),
    ("rj_bolt_z", "mm", "9 mm", "[demo] rear bolts at +/- this"),
    ("rj_engage", "mm", "6 mm", "[demo] main-body material between the tongue tip and the nuts"),
    ("rj_nut_x0", "mm", "rear_split + rear_tongue_length + rj_engage", "[demo] derived"),
    ("rj_bolt_len", "mm", "rj_nut_x0 + nut_slot_len + bolt_tail - rs_win_front_x", "[demo] derived: rear fastener length under the head"),
    ("front_tongue_height", "mm", "20 mm", "[manual] restyle: bolted joint"),
    ("front_tongue_y", "mm", "-46 mm", "[manual] restyle: head pocket leaves min_wall under the mag slots"),
    ("fj_bolt_z", "mm", "8 mm", "[demo] front bolts at +/- this"),
    ("fj_engage", "mm", "6 mm", "[demo] main-body material between the tongue tip and the nuts"),
    ("fj_head_wall", "mm", "8 mm", "[demo] forestock material between the tongue root and the head pocket"),
    ("fj_pocket_len", "mm", "40 mm", "[demo] head pocket length (socket room)"),
    ("fj_nut_x0", "mm", "front_split - front_tongue_length - fj_engage - nut_slot_len", "[demo] derived"),
    ("fj_head_x", "mm", "front_split + fj_head_wall", "[demo] derived: head seat face"),
    ("fj_bolt_len", "mm", "fj_head_x - (fj_nut_x0 - bolt_tail)", "[demo] derived: front fastener length under the head"),
    ("chk_fj_pocket_slots", "mm", "(mag_holder_top - mag_slot_h) - (front_tongue_y + joint_head_d / 2 + joint_head_clear) - min_wall",
     "[demo] head pocket keeps >= min_wall under the mag slots"),
    ("chk_fj_tongue_floor", "mm", "forend_depth + front_tongue_y - front_tongue_height / 2 - min_wall",
     "[demo] socket floor under the front tongue >= min_wall"),
    ("chk_fj_pocket_hand", "mm", "handstop_position - (fj_head_x + fj_pocket_len)", "[demo] head pocket behind the hand stop"),
    ("chk_rj_head_window", "mm", "(rs_win_top - (rear_tongue_y + joint_head_d / 2)) ", "[demo] rear heads fit under the window top"),
    # ---- TPU inserts (Darren 2026-11-24): surfaces shaped purely by the athlete's body are separate TPU parts
    ("tpu_wall", "mm", "4 mm", "[demo] thinnest TPU over the rigid grip core"),
    ("cap_t", "mm", "5 mm", "[demo] rigid cap under the grip that locks the TPU sleeve"),
    ("cap_screw_d", "mm", "5.5 mm", "[demo] M5 clearance hole in the cap"),
    ("cradle_w", "mm", "action_width + 2 * cradle_wall", "[demo] derived: width of the action cradle and of its pocket in the main body"),
    ("cradle_y", "mm", "-(bore_above_inlet_floor + cradle_floor)", "[demo] derived: underside of the action cradle"),
    ("act_bed_r", "mm", "act_receiver_d / 2 + fit_loose", "[demo] derived: bed radius, with room for bedding compound"),
    ("chk_cradle_side", "mm", "(body_width - cradle_w) / 2 - 3 mm", "[demo] main-body wall beside the cradle"),
    ("chk_pillar_mag", "mm", "act_screw_front_x - act_pillar_d / 2 - (mag_well_x1 + fit_slide) - 4 mm", "[demo] front pillar clear of the magazine well"),
    ("chk_pillar_front", "mm", "action_front - (act_screw_front_x + act_pillar_d / 2)", "[demo] front pillar inside the cradle"),
    ("pad_t", "mm", "3 mm", "[demo] prone hand pad thickness"),
    ("pad_wrap", "mm", "14 mm", "[demo] the pad wraps this far up each side of the forend"),
    ("pad_x0", "mm", "handstop_position - prone_hand_length", "[demo] derived: the pad covers the prone hand (J) behind the hand stop"),
    ("keel_w", "mm", "8 mm", "[demo] pad keel width at its neck"),
    ("keel_flare", "mm", "2 mm", "[demo] dovetail undercut per side"),
    ("keel_h", "mm", "5 mm", "[demo] pad keel height"),
    ("forend_fore_depth", "mm", "50 mm", "[demo] bore to the forend underside ahead of the drop belly (the hand's forend)"),
    ("belly_x0", "mm", "fj_head_x + 2 mm", "[demo] derived: the drop belly starts to rise just ahead of the joint's head seat"),
    ("belly_x1", "mm", "fj_head_x + fj_pocket_len", "[demo] derived: the underside reaches forend_fore_depth at the end of the head pocket"),
    ("belly_sweep_r", "mm", "30 mm", "[demo] sweep radius at both ends of the drop-belly ramp"),
    ("wrist_under_y", "mm", "rear_tongue_y - rear_tongue_height / 2 - min_wall - 1 mm", "[demo] derived: wrist underside, min_wall below the rear joint socket"),
    ("grip_top_y", "mm", "wrist_under_y", "[demo] derived: the grip hangs from the wrist underside"),
    ("spine_d", "mm", "10 mm", "[demo] rigid front strip of the grip above the guard bar, so the TPU edge there is full thickness"),
    ("chk_pad_pocket", "mm", "pad_x0 - (fj_head_x + fj_pocket_len) - 4 mm", "[demo] the pad starts ahead of the joint's head pocket"),
    ("chk_pad_slots", "mm", "(mag_holder_top - mag_slot_h) - (-forend_fore_depth + pad_wrap) - 2 mm", "[demo] the pad stays below the mag slots"),
]


def strut_y(x):
    """Upper edge of the butt's lower strut at x (the underside line moved up by frame_web)."""
    return f"rs_low_slope * ({x}) + rs_strut_c"


def rib_hit(xt):
    """Where a rib edge that starts at (xt, rs_win_top) and leans by rib_lean meets the strut."""
    x = f"(({xt}) + rib_lean * (rs_win_top - rs_strut_c)) / (1 + rib_lean * rs_low_slope)"
    return x, strut_y(x)


def gf(y):
    """Grip front X at height y."""
    return f"grip_front_x - grip_lean * (grip_top_y - ({y}))"


def gb(y):
    """Grip back X at height y (chord of the palm-swell arc)."""
    return f"{gf(y)} - grip_depth"


def lf(y):
    """Front face of the guard leg and standing block at height y (one straight line)."""
    return f"guard_front_x - blk_front_rake * (-forend_depth - ({y})) / (block_height - forend_depth)"


class Builder:
    def __init__(self, design):
        self.d = design
        self.root = design.rootComponent
        self.um = design.unitsManager
        self.problems = []

    # ---------------------------------------------------------------- helpers
    def ev(self, expr):
        v = self.um.evaluateExpression(expr, "mm")
        if v == -1 and not self.um.isValidExpression(expr, "mm"):
            raise ValueError(f"bad expression: {expr}")
        return v  # cm

    def vi(self, expr):
        return adsk.core.ValueInput.createByString(expr)

    def sketch(self, name, plane=None):
        sk = self.root.sketches.add(plane or self.root.xYConstructionPlane)
        sk.name = name
        sk.isComputeDeferred = True
        a = sk.sketchPoints.add(adsk.core.Point3D.create(-DATUM / 10, -DATUM / 10, 0))
        a.isFixed = True
        sk._datum = a
        return sk

    def pt(self, sk, ex, ey):
        try:
            return self._pt(sk, ex, ey)
        except Exception as e:
            raise RuntimeError(f"sketch {sk.name}: point ({ex}, {ey}): {e}") from None

    def _pt(self, sk, ex, ey):
        x, y = self.ev(ex), self.ev(ey)
        # Place each point slightly off its target (the dimensions then pull it exact), so
        # Fusion infers no alignment constraints with earlier points at the same X or Y.
        self._n = getattr(self, "_n", 0) + 1
        j = 0.0007 * (self._n % 7 + 1)
        p = sk.sketchPoints.add(adsk.core.Point3D.create(x + j, y - j, 0))
        dims = sk.sketchDimensions
        O = adsk.fusion.DimensionOrientations
        dh = dims.addDistanceDimension(sk._datum, p, O.HorizontalDimensionOrientation,
                                       adsk.core.Point3D.create((x - DATUM / 10) / 2, -DATUM / 10 - 2, 0))
        dh.parameter.expression = f"({ex}) + {DATUM:g} mm"
        dv = dims.addDistanceDimension(sk._datum, p, O.VerticalDimensionOrientation,
                                       adsk.core.Point3D.create(-DATUM / 10 - 2, (y - DATUM / 10) / 2, 0))
        dv.parameter.expression = f"({ey}) + {DATUM:g} mm"
        return p

    def poly(self, sk, pts, closed=True, arcs=None):
        """pts: list of (x_expr, y_expr). arcs: {i: radius_expr} makes segment i -> i+1 an arc
        bulging toward +normal of the chord (as part.py's _arc_mid with inward=1)."""
        arcs = arcs or {}
        sps = [self.pt(sk, *p) for p in pts]
        n = len(sps)
        lines = sk.sketchCurves.sketchLines
        for i in range(n if closed else n - 1):
            a, b = sps[i], sps[(i + 1) % n]
            if i in arcs:
                r = self.ev(arcs[i])
                ax, ay, bx, by = a.geometry.x, a.geometry.y, b.geometry.x, b.geometry.y
                cx, cy = (ax + bx) / 2, (ay + by) / 2
                ch = math.hypot(bx - ax, by - ay)
                s = r - math.sqrt(max(r * r - (ch / 2) ** 2, 0))
                nx, ny = (by - ay) / ch, -(bx - ax) / ch
                mid = adsk.core.Point3D.create(cx + s * nx, cy + s * ny, 0)
                arc = sk.sketchCurves.sketchArcs.addByThreePoints(a, mid, b)
                d = sk.sketchDimensions.addRadialDimension(arc, mid)
                d.parameter.expression = arcs[i]
            else:
                lines.addByTwoPoints(a, b)
        return sps

    def rect(self, sk, x0, x1, y0, y1):
        return self.poly(sk, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def circle(self, sk, cx, cy, d_expr):
        c = self.pt(sk, cx, cy)
        circ = sk.sketchCurves.sketchCircles.addByCenterRadius(c, self.ev(d_expr) / 2)
        dd = sk.sketchDimensions.addDiameterDimension(
            circ, adsk.core.Point3D.create(c.geometry.x + 1, c.geometry.y + 1, 0))
        dd.parameter.expression = d_expr
        return circ

    def done(self, sk):
        sk.isComputeDeferred = False
        return sk

    def profiles(self, sk):
        return [sk.profiles.item(i) for i in range(sk.profiles.count)]

    def offset_plane(self, name, expr, base=None):
        inp = self.root.constructionPlanes.createInput()
        inp.setByOffset(base or self.root.xYConstructionPlane, self.vi(expr))
        pl = self.root.constructionPlanes.add(inp)
        pl.name = name
        return pl

    def yz_sketch(self, name, x_expr):
        pl = self.offset_plane(f"{name}_plane", x_expr, self.root.yZConstructionPlane)
        return self.sketch(name, pl)          # sketch x = -Z, sketch y = Y, normal +X

    def extrude(self, occ, profiles, op, *, sym=None, dist=None, start=None, name=None, bodies=None, taper=None):
        comp = occ.component
        ext = comp.features.extrudeFeatures
        if isinstance(profiles, list):
            col = adsk.core.ObjectCollection.create()
            for p in profiles:
                col.add(p)
            profiles = col
        inp = ext.createInput(profiles, op)
        inp.creationOccurrence = occ
        if op != adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
            # Name the target explicitly: target detection from a root-sketch profile is not
            # reliable for every component.
            inp.participantBodies = [b.createForAssemblyContext(occ) for b in (bodies or comp.bRepBodies)]
        if sym:
            inp.setSymmetricExtent(self.vi(sym), True)
        else:
            if start:
                inp.startExtent = adsk.fusion.OffsetStartDefinition.create(self.vi(start))
            ext_def = adsk.fusion.DistanceExtentDefinition.create(self.vi(dist))
            if taper:
                inp.setOneSideExtent(ext_def, adsk.fusion.ExtentDirections.PositiveExtentDirection, self.vi(taper))
            else:
                inp.setOneSideExtent(ext_def, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        try:
            f = ext.add(inp)
        except Exception as e:
            bb = [(b.name, [round(v * 10) for v in (b.boundingBox.minPoint.x, b.boundingBox.maxPoint.x,
                                                     b.boundingBox.minPoint.y, b.boundingBox.maxPoint.y)])
                  for b in comp.bRepBodies]
            raise RuntimeError(f"{name} in {comp.name} failed: {e}; bodies {bb}") from None
        if name:
            f.name = name
        return f

    def combine(self, target, tools, op, name, keep=True):
        """target, tools: (occurrence, body) pairs. The feature lives in the root component."""
        col = adsk.core.ObjectCollection.create()
        for occ, b in tools:
            col.add(b.createForAssemblyContext(occ))
        feats = self.root.features.combineFeatures
        inp = feats.createInput(target[1].createForAssemblyContext(target[0]), col)
        inp.operation = op
        inp.isKeepToolBodies = keep
        f = feats.add(inp)
        f.name = name
        return f

    # ---- edge finders and rounding
    @staticmethod
    def sharp(e):
        if e.faces.count != 2:
            return False
        ok, t0, t1 = e.evaluator.getParameterExtents()
        ok, p = e.evaluator.getPointAtParameter((t0 + t1) / 2)
        ok1, n1 = e.faces.item(0).evaluator.getNormalAtPoint(p)
        ok2, n2 = e.faces.item(1).evaluator.getNormalAtPoint(p)
        return ok1 and ok2 and n1.angleTo(n2) > 0.08

    @staticmethod
    def z_edge(e):
        g = e.geometry
        if g.curveType != adsk.core.Curve3DTypes.Line3DCurveType:
            return None
        a, b = g.startPoint, g.endPoint
        if abs(a.x - b.x) < 1e-4 and abs(a.y - b.y) < 1e-4 and abs(a.z - b.z) > 0.05:
            return a.x, a.y
        return None

    def fillet(self, comp, sets, name):
        """sets: list of (edges, radius_expr). A failure is reported, not raised, so one bad
        round does not hide the rest of the model."""
        fil = comp.features.filletFeatures
        inp = fil.createInput()
        n = 0
        for edges, r in sets:
            col = adsk.core.ObjectCollection.create()
            for e in edges:
                col.add(e)
            n += col.count
            if col.count:
                try:
                    inp.edgeSetInputs.addConstantRadiusEdgeSet(col, self.vi(r), False)
                except AttributeError:
                    inp.addConstantRadiusEdgeSet(col, self.vi(r), False)
        if not n:
            self.problems.append(f"{name}: no edges found")
            return None
        try:
            f = fil.add(inp)
            f.name = name
            return f
        except Exception as e:
            self.problems.append(f"{name}: {str(e).splitlines()[0][:120]}")
            return None

    def corners(self, occ, pts, label, body=None):
        """Round profile corners: the edge along Z at each (x, y) gets its own radius parameter."""
        comp = occ.component
        for i, (x, y, r) in enumerate(pts):
            b = body or comp.bRepBodies.item(0)
            cx, cy = self.ev(x), self.ev(y)
            edges = []
            for e in b.edges:
                xy = self.z_edge(e)
                if xy and abs(xy[0] - cx) < 0.03 and abs(xy[1] - cy) < 0.03:
                    edges.append(e)
            self.fillet(comp, [(edges, r)], f"{label}_corner_{i}")

    def round_faces(self, occ, half, r, name, zc="0 mm", facets=False, skip_x=(), skip_y=(), body=None):
        """Round the sharp edges of the side faces (normal along Z) that sit `half` from the
        centre plane zc. facets=True also takes the inclined belly-facet faces."""
        comp = occ.component
        b = body or comp.bRepBodies.item(0)
        zc_v, half_v = self.ev(zc), self.ev(half)
        skips = [self.ev(s) for s in skip_x]
        skips_y = [self.ev(s) for s in skip_y]
        picked = {}
        for f in b.faces:
            g = f.geometry
            if g.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
                ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
                if not (facets and ok and 0.2 < abs(n.z) < 0.95):
                    continue
            elif facets and 0.2 < abs(g.normal.z) < 0.95:
                pass
            elif not (abs(g.normal.z) > 0.99 and abs(abs(f.pointOnFace.z - zc_v) - half_v) < 0.01):
                continue
            for e in f.edges:
                if e.tempId in picked or not self.sharp(e):
                    continue
                ys = (e.startVertex.geometry.y, e.endVertex.geometry.y)
                if any(abs(ys[0] - s) < 0.01 and abs(ys[1] - s) < 0.01 for s in skips_y):
                    continue          # the junction with the body underside stays square
                xs = (e.startVertex.geometry.x, e.endVertex.geometry.x)
                if any(abs(xs[0] - s) < 0.06 and abs(xs[1] - s) < 0.06 for s in skips):
                    continue          # an edge lying in a joint face: leave the seam square
                picked[e.tempId] = e
        mids = [self.mid(e) for e in picked.values()]
        n_before = len(self.problems)
        f = self.fillet(comp, [(list(picked.values()), r)], name)
        if f is None and len(mids) > 1:
            # The set would not round as one feature: round the edges one at a time, so a single
            # awkward edge does not leave the whole part square, and report the ones that fail.
            del self.problems[n_before:]
            bad = []
            for i, m in enumerate(mids):
                near = [e for e in (body or comp.bRepBodies.item(0)).edges
                        if self.mid(e).distanceTo(m) < 0.005 and self.sharp(e)]
                k = len(self.problems)
                if not near or self.fillet(comp, [(near[:1], r)], f"{name}_{i}") is None:
                    del self.problems[k:]
                    bad.append("(%.0f, %.0f, %.0f)" % (m.x * 10, m.y * 10, m.z * 10))
            if bad:
                self.problems.append(f"{name}: {len(bad)} of {len(mids)} edges left square at " + " ".join(bad))
        return f

    @staticmethod
    def mid(e):
        ok, t0, t1 = e.evaluator.getParameterExtents()
        ok, p = e.evaluator.getPointAtParameter((t0 + t1) / 2)
        return p

    def fillet_z_edges(self, occ, feature, r, name):
        """Round the corners (edges along Z) that a cut feature made: geometric windows with soft corners."""
        picked = {}
        for f in feature.faces:
            for e in f.edges:
                if self.z_edge(e) and self.sharp(e):
                    picked[e.tempId] = e
        return self.fillet(occ.component, [(list(picked.values()), r)], name)

    def belly(self, occ, label, ys=("-forend_depth", "-forend_fore_depth"), w="belly_w", h="belly_h"):
        """Facet the two bottom edges at height ys (w off the bottom face, h off the side face)."""
        comp = occ.component
        cf = comp.features.chamferFeatures
        ys, zh = [self.ev(y) for y in ys], self.ev("body_width / 2")
        for sign in (1, -1):
            for flipped in (False, True):
                edge = None       # the longest straight underside edge; the chamfer follows its tangent chain
                for e in comp.bRepBodies.item(0).edges:
                    g = e.geometry
                    if g.curveType != adsk.core.Curve3DTypes.Line3DCurveType or e.length < 2:
                        continue
                    a, b = g.startPoint, g.endPoint
                    if any(all(abs(p.y - y) < 1e-3 and abs(p.z - sign * zh) < 1e-3 for p in (a, b)) for y in ys):
                        if edge is None or e.length > edge.length:
                            edge = e
                if edge is None:
                    self.problems.append(f"{label}_belly: bottom edge not found (side {sign})")
                    break
                col = adsk.core.ObjectCollection.create()
                col.add(edge)
                inp = cf.createInput2()
                inp.chamferEdgeSets.addTwoDistancesChamferEdgeSet(col, self.vi(w), self.vi(h), flipped, True)
                try:
                    f = cf.add(inp)
                except Exception as e:
                    self.problems.append(f"{label}_belly: {str(e).splitlines()[0][:120]}")
                    break
                n = next(fc.geometry.normal for fc in f.faces
                         if fc.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType)
                if abs(n.y) > abs(n.z):       # belly_w lies on the bottom face: correct way round
                    f.name = f"{label}_belly_{'p' if sign > 0 else 'n'}"
                    break
                f.deleteMe()

    # ---------------------------------------------------------------- build
    def params(self):
        up = self.d.userParameters
        # action parameters normally come from the loader; add any that an older load did not create
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import importlib
        import stock_params
        stock_params = importlib.reload(stock_params)   # Fusion keeps modules loaded between runs
        for row in stock_params.REGISTRY:
            if row.group == "action" and up.itemByName(row.name) is None:
                up.add(row.name, self.vi(row.default), row.unit, f"[fit] {row.note} (placeholder)")
        # apply the preset of the selected action, so a preset edit shows without re-running the loader
        code = round(up.itemByName("action_type").value)
        for a in stock_params.ACTIONS.values():
            if a["code"] == code:
                for name, expr in a["values"].items():
                    q = up.itemByName(name)
                    if q is not None and not q.comment.startswith("[manual]"):
                        q.expression = expr
        for name, unit, expr, comment in DEMO_PARAMS:
            p = up.itemByName(name)
            if p is None:
                up.add(name, self.vi(expr), unit, comment)
            elif not p.comment.startswith("[manual]") or comment.startswith("[manual]") or p.comment.startswith(comment[:8]):
                p.expression, p.comment = expr, comment

    def clear(self):
        tl = self.d.timeline
        for i in range(tl.count - 1, -1, -1):
            e = tl.item(i).entity
            if e is not None:
                e.deleteMe()
        for i in range(self.root.occurrences.count - 1, -1, -1):
            self.root.occurrences.item(i).deleteMe()

    def build(self):
        NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
        INTERSECT = adsk.fusion.FeatureOperations.IntersectFeatureOperation
        self.clear()
        self.params()
        root = self.root

        occs = {}
        for key, label in (("rear", "rear_stock"), ("main", "main_body"), ("fore", "forestock"),
                           ("action", "action_cradle"), ("block", "standing_block"), ("grip", "tpu_grip"), ("pad", "tpu_prone_pad"), ("cap", "grip_cap")):
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = label
            occs[key] = occ
        rear, main, fore = occs["rear"], occs["main"], occs["fore"]

        def body(key, i=0):
            return occs[key].component.bRepBodies.item(i)

        # ---- skeleton: side outline + split lines (one sketch, three regions)
        fd, ffd = "-forend_depth", "-forend_fore_depth"
        sk = self.sketch("skeleton_outline")
        P = [
            ("-lop", "-buttplate_drop + buttplate_length / 2"),                  # 0 heel
            ("-lop + comb_nose", "comb_top"),                                     # 1
            ("-lop + comb_length", "comb_top"),                                   # 2 comb front
            ("action_rear - comb_nose", "wrist_top"),                             # 3 wrist low point
            ("rear_split", "0 mm"),                                               # 4 ramp ends on the joint line
            ("forend_tip", "0 mm"),                                               # 5 nose top
            ("forend_tip - tip_rake", "-tip_depth"),                              # 6 nose bottom
            ("tip_sweep_x", ffd),                                                 # 7 underside turns up
            ("belly_x1", ffd),                                                    # 8 drop-belly ramp, front
            ("belly_x0", fd),                                                     # 9 drop-belly ramp, rear
            ("rel_front_x", fd),                                                  # 10 step behind the mag well
            ("rel_front_x", "finger_hole_y1"),                                    # 11 release window, top front
            (gf("finger_hole_y1"), "finger_hole_y1"),                             # 12 guard opening, top rear
            ("grip_front_x", "wrist_under_y"),                                    # 13 grip front, top
            (f"{gb('wrist_under_y')} - wrist_ramp", "wrist_under_y"),             # 14 behind the grip
            ("wrist_heel_x", "wrist_heel_y"),                                     # 15
            ("-lop + hook_thickness", "hook_tip_y - tip_round"),                  # 16
            ("-lop - hook_reach + hook_round", "hook_tip_y - hook_round"),        # 17
            ("-lop - hook_reach", "hook_tip_y"),                                  # 18 hook tip
            ("-lop", "butt_bot_y"),                                               # 19 toe
        ]
        self.poly(sk, P, arcs={18: "hook_radius", 19: "buttplate_curve_radius"})
        for xs in ("rear_split", "front_split"):
            self.poly(sk, [(xs, "sight_line_above_bore + 50 mm"), (xs, "-ibu_depth_max - 60 mm")], closed=False)
        self.done(sk)
        regions = sorted(self.profiles(sk), key=lambda pr: pr.boundingBox.minPoint.x)
        assert len(regions) == 3, f"expected 3 outline regions, got {len(regions)}"
        rear_pr, main_pr, fore_pr = regions

        self.extrude(rear, rear_pr, NEW, start="cast_z - comb_width / 2", dist="comb_width", name="rear_blank")
        self.extrude(main, main_pr, NEW, sym="body_width", name="main_blank")
        self.extrude(fore, fore_pr, NEW, sym="body_width", name="fore_blank")

        # ---- flowing profile: each outline corner gets its own radius (convex ones >= body_round)
        self.corners(rear, [(*P[1], "comb_nose"), (*P[2], "comb_front_r"), (*P[3], "body_round"),
                            (*P[15], "wrist_heel_r"), (*P[16], "hook_round + body_round"), (*P[19], "hook_round")], "rear")
        self.corners(fore, [(*P[5], "tip_round"), (*P[6], "tip_round + body_round"),
                            (*P[8], "belly_sweep_r"), (*P[9], "belly_sweep_r")], "fore")

        # ---- faceted belly under the forend, then the hand stop, then the side rounds
        self.belly(main, "main")
        self.belly(main, "wrist", ys=("wrist_under_y",), w="wrist_facet_w", h="wrist_facet_h")   # blends the body into the grip
        self.belly(fore, "fore")

        self.round_faces(rear, "comb_width / 2", "body_round", "rear_round", zc="cast_z", skip_x=("rear_split",))
        self.round_faces(main, "body_width / 2", "body_round", "main_round", facets=True, skip_x=("rear_split", "front_split"))
        self.round_faces(fore, "body_width / 2", "body_round", "fore_round", facets=True, skip_x=("front_split",))
        hp = "handstop_position"
        sk = self.sketch("hand_stop")
        hs_top, hs_bot = f"{ffd} + belly_h + 2 mm", f"{ffd} - handstop_height"
        self.poly(sk, [(hp, hs_top), (f"{hp} + handstop_length + hs_rake", hs_top), (f"{hp} + handstop_length + hs_rake", ffd),
                       (f"{hp} + handstop_length", hs_bot), (hp, hs_bot)])
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), JOIN, sym="hs_width", name="hand_stop")
        self.corners(fore, [(f"{hp} + handstop_length", hs_bot, "tip_round"), (hp, hs_bot, "hook_round")], "hand_stop")

        self.round_faces(fore, "hs_width / 2", "hs_round", "hand_stop_round", skip_y=(hs_top,))

        # ---- main body: trigger guard, and the standing block as an extension of the guard base
        sk = self.sketch("trigger_guard")
        gbm, fh0 = "-guard_bottom", "finger_hole_y0"
        self.poly(sk, [("rel_front_x", f"{fd} + 6 mm"), ("guard_front_x", f"{fd} + 6 mm"), (lf(gbm), gbm),
                       (f"{gf(gbm)} - 6 mm", gbm), (f"{gf(fh0)} - 6 mm", fh0), ("rel_front_x", fh0)])
        self.done(sk)
        # rounded as a body of its own (clean edges), then joined; its ends are buried in the body and the grip spine
        self.extrude(main, sk.profiles.item(0), NEW, sym="guard_width", name="trigger_guard")
        self.corners(main, [("rel_front_x", fh0, "guard_round + guard_round")], "guard", body=body("main", 1))
        self.round_faces(main, "guard_width / 2", "guard_round", "guard_round", body=body("main", 1))
        self.combine((main, body("main")), [(main, body("main", 1))], JOIN, "trigger_guard_join", keep=False)

        # ---- standing block: the stock only carries a mount point (the flat underside of the guard rail
        # with one M5 heat-set insert). The block is a separate printed part the athlete can swap: its
        # saddle straddles the rail, so it cannot turn or slide sideways, and one bolt holds it.
        blk = occs["block"]
        bh, btop = "-block_height", f"{gbm} + saddle_h"
        sk = self.sketch("standing_block")
        self.poly(sk, [("blk_rear_x", btop), (lf(btop), btop), ("guard_front_x - blk_front_rake", bh), ("blk_rear_x + blk_rake", bh)])
        self.done(sk)
        self.extrude(blk, sk.profiles.item(0), NEW, sym="block_width", name="standing_block")
        self.corners(blk, [("guard_front_x - blk_front_rake", bh, "block_corner_r"), ("blk_rear_x + blk_rake", bh, "block_corner_r")], "block")
        self.round_faces(blk, "block_width / 2", "block_round", "block_round")
        self.combine((blk, body("block")), [(main, body("main"))], CUT, "block_saddle")
        sk = self.sketch("block_window")
        self.rect(sk, "blk_rear_x + blk_rake + blk_win_web", "guard_front_x - blk_front_rake - blk_win_web",
                  f"{bh} + blk_win_web", f"{gbm} - blk_win_web")
        self.done(sk)
        f = self.extrude(blk, sk.profiles.item(0), CUT, sym="2 * body_width", name="block_window")
        self.fillet_z_edges(blk, f, "block_slot_r", "block_window_round")

        # ---- action cradle: everything that depends on the action type lives in this one component.
        # The main body only has a pocket of fixed section (cradle_w wide, down to cradle_y).
        act = occs["action"]
        both = (main, act)
        sk = self.sketch("cradle_pocket")
        self.rect(sk, "action_rear", "action_front", "cradle_y", "sight_line_above_bore")
        self.done(sk)
        self.extrude(main, sk.profiles.item(0), CUT, sym="cradle_w", name="cradle_pocket")
        sk = self.sketch("cradle_block")
        self.rect(sk, "action_rear", "action_front", "cradle_y", "0 mm")
        self.done(sk)
        self.extrude(act, sk.profiles.item(0), NEW, sym="cradle_w", name="cradle_block")

        sk = self.yz_sketch("receiver_bed", "action_rear")      # half-round bed with straight walls above the bore
        self.poly(sk, [("-act_bed_r", "5 mm"), ("-act_bed_r", "0 mm"), ("act_bed_r", "0 mm"), ("act_bed_r", "5 mm")],
                  arcs={1: "act_bed_r"})
        self.done(sk)
        self.extrude(act, sk.profiles.item(0), CUT, dist="action_front - action_rear", name="receiver_bed")

        def through(name, x0, x1, y0, y1, width, dist=None):
            sk = self.sketch(name)
            self.rect(sk, x0, x1, y0, y1)
            self.done(sk)
            for occ in both:
                if dist:
                    self.extrude(occ, sk.profiles.item(0), CUT, dist=dist, name=name)
                else:
                    self.extrude(occ, sk.profiles.item(0), CUT, sym=width, name=name)

        through("trigger_slot", "trigger_slot_x0", "trigger_slot_x1", "finger_hole_y1 - 1 mm", "0 mm", "trigger_slot_width")
        through("mag_well", "mag_well_x0 - fit_slide", "mag_well_x1 + fit_slide", f"{fd} - 1 mm", "0 mm",
                "mag_well_width + 2 * fit_slide")
        through("bolt_notch", "bolt_notch_x - bolt_notch_length / 2", "bolt_notch_x + bolt_notch_length / 2",
                "-bolt_notch_depth", "sight_line_above_bore", None, dist="bolt_dir * body_width")

        # bedding screws: vertical pillar bores from the bed to the underside, counterbored for the heads
        def xz_sketch(name, y_expr):
            y = self.ev(y_expr)
            pl = self.offset_plane(f"{name}_plane", y_expr, root.xZConstructionPlane)
            if abs(pl.geometry.origin.y - y) > 0.01:
                pl.deleteMe()
                pl = self.offset_plane(f"{name}_plane", f"-({y_expr})", root.xZConstructionPlane)
            sk = self.sketch(name, pl)
            q = sk.modelToSketchSpace(adsk.core.Point3D.create(1, y, 1))
            down = -1 if sk.xDirection.crossProduct(sk.yDirection).y > 0 else 1
            return sk, (lambda x: x if q.x > 0 else f"-({x})"), down

        def drill(name, y_expr, x_expr, d_expr, depth, comps):
            sk, fx, down = xz_sketch(name, y_expr)
            self.circle(sk, fx(x_expr), "0 mm", d_expr)
            self.done(sk)
            for occ in comps:
                self.extrude(occ, sk.profiles.item(0), CUT, dist=depth if down > 0 else f"-({depth})", name=name)

        for nm, x, under in (("front", "act_screw_front_x", fd), ("rear", "act_screw_rear_x", "finger_hole_y1")):
            drill(f"{nm}_pillar_bore", "0 mm", x, "act_pillar_d", "ibu_depth_max", both)
            drill(f"{nm}_screw_counterbore", f"{under} + act_cbore", x, "act_head_d + 3 mm", "act_cbore + 2 mm", (main,))

        # sling seat (Biatar / Larsen type sling): the flat end tab nests in a pocket under the hand stop that
        # is as wide as the tab, with a semicircular end for its round tip. It is open to the rear, where the
        # sling leaves toward the arm, and a thumb screw goes through the eyelet into a heat-set insert.
        sk, fx, down = xz_sketch("sling_seat", hs_bot)
        xr, xc, r = f"{hp} - 1 mm", "sling_tip_x - sling_seat_r", "sling_seat_r"
        ring = [(fx(xr), f"-{r}"), (fx(xc), f"-{r}"), (fx(xc), r), (fx(xr), r)]
        if fx("1") != "1":
            ring = [(x, z[1:] if z.startswith("-") else f"-{z}") for x, z in ring]   # keep the arc bulging forward
        self.poly(sk, ring, arcs={1: r})
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), CUT, dist="-(sling_seat_d)" if down > 0 else "sling_seat_d", name="sling_seat")
        drill("sling_insert", f"{hs_bot} + insert_depth + sling_seat_d", "sling_hole_x", "insert_hole_d", "insert_depth + sling_seat_d + 1 mm", (fore,))

        # block bolt: the head sits inside the block's slot and is tightened through the hole in the slot floor
        drill("block_bolt_hole", gbm, "block_bolt_x", "cap_screw_d", "block_height", (blk,))
        drill("block_mount_insert", f"{gbm} + block_insert_depth", "block_bolt_x", "insert_hole_d", "block_insert_depth + 1 mm", (main,))

        sk = self.sketch("barrel_channel")
        self.rect(sk, "action_front", "forend_tip + tip_round", "-(barrel_d / 2 + barrel_float)", "sight_line_above_bore")
        self.done(sk)
        for occ in (main, fore):
            self.extrude(occ, sk.profiles.item(0), CUT, sym="barrel_d + 2 * barrel_float", name="barrel_channel")

        # ---- joints (Darren 2026-11-23): each joint is a tongue that overlaps into a socket, locked
        # by two fasteners running along the stock (X). Hex nuts sit in printed slots in the main body
        # that match the nut's flats, so a nut cannot turn. Both nut slots open upward into the action
        # inlet or barrel channel, so they are hidden under the action and barrel and need no cover.
        def tongue_socket(carrier, x0, x1, y, h, w, sx0, sx1, label):
            sk = self.sketch(f"{label}_tongue")
            self.rect(sk, x0, x1, f"{y} - {h} / 2", f"{y} + {h} / 2")
            self.done(sk)
            self.extrude(carrier, sk.profiles.item(0), JOIN, sym=w, name=f"{label}_tongue")
            sk = self.sketch(f"{label}_socket")
            self.rect(sk, sx0, sx1, f"{y} - {h} / 2 - fit_snug", f"{y} + {h} / 2 + fit_snug")
            self.done(sk)
            self.extrude(main, sk.profiles.item(0), CUT, sym=f"{w} + 2 * fit_snug", name=f"{label}_socket")

        def nut_slots(label, x0, y, zs, top, comps=None):
            """Hex pocket matched to the nut (flats vertical, so it cannot turn), opening up to `top`."""
            sk = self.yz_sketch(f"{label}_nut_slots", x0)
            h, c2 = "nut_slot_af / 2", "nut_slot_af / 2 / (2 * cos(30 deg))"
            for z in zs:
                pts = [(z, f"{y} - 2 * {c2}"), (f"{z} + {h}", f"{y} - {c2}"), (f"{z} + {h}", top),
                       (f"{z} - {h}", top), (f"{z} - {h}", f"{y} - {c2}")]
                self.poly(sk, [(f"-({zz})", yy) for zz, yy in pts])
            self.done(sk)
            for occ in comps or (main,):
                self.extrude(occ, self.profiles(sk), CUT, dist="nut_slot_len", name=f"{label}_nut_slots")

        def bolt_holes(label, x0, length, y, zs, comps):
            sk = self.yz_sketch(f"{label}_bolts", x0)
            for z in zs:
                self.circle(sk, f"-({z})", y, "hole_d_bolt")
            self.done(sk)
            for occ in comps:
                self.extrude(occ, self.profiles(sk), CUT, dist=length, name=f"{label}_bolt_holes")

        # rear: butt-stock tongue into the main body; heads in the butt's front window
        tongue_socket(rear, "rear_split - fit_loose", "rear_split + rear_tongue_length", "rear_tongue_y",
                      "rear_tongue_height", "rear_tongue_width",
                      "rear_split - fit_loose", "rear_split + rear_tongue_length + fit_snug", "rear")
        rz = ("rj_bolt_z", "-rj_bolt_z")
        nut_slots("rear", "rj_nut_x0", "rear_tongue_y", rz, "-act_bed_r + 3 mm", both)
        bolt_holes("rear", "rs_win_front_x - 1 mm", "rj_bolt_len + 1 mm", "rear_tongue_y", rz, (rear, main))

        # front: forestock tongue into the main body; heads in a pocket under the forestock,
        # open at the bottom, min_wall below the mag slots and outside the marking surface
        tongue_socket(fore, "front_split - front_tongue_length", "front_split + fit_loose", "front_tongue_y",
                      "front_tongue_height", "front_tongue_width",
                      "front_split - front_tongue_length - fit_snug", "front_split + fit_loose", "front")
        fz = ("fj_bolt_z", "-fj_bolt_z")
        nut_slots("front", "fj_nut_x0", "front_tongue_y", fz, "-(barrel_d / 2 + barrel_float) + 1 mm")
        bolt_holes("front", "fj_nut_x0 - bolt_tail", "fj_bolt_len", "front_tongue_y", fz, (main, fore))

        # hardware bodies so the joints read in the model; not printed
        hw = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        hw.component.name = "hardware_M6"
        occs["hw"] = hw

        def bolt(label, seat, direction, length, y, zs):
            head_x0 = f"{seat} - 6 mm" if direction > 0 else seat
            sk = self.yz_sketch(f"{label}_bolt_heads", head_x0)
            for z in zs:
                self.circle(sk, f"-({z})", y, "joint_head_d")
            self.done(sk)
            self.extrude(hw, self.profiles(sk), NEW, dist="6 mm", name=f"{label}_heads")
            shank_x0 = seat if direction > 0 else f"{seat} - {length}"
            sk = self.yz_sketch(f"{label}_bolt_shanks", shank_x0)
            for z in zs:
                self.circle(sk, f"-({z})", y, "bolt_d")
            self.done(sk)
            self.extrude(hw, self.profiles(sk), NEW, dist=length, name=f"{label}_shanks")

        def nuts(label, x0, y, zs):
            sk = self.yz_sketch(f"{label}_nuts", f"{x0} + fit_snug")
            h, c2 = "nut_af / 2", "nut_af / 2 / (2 * cos(30 deg))"
            for z in zs:
                pts = [(z, f"{y} - 2 * {c2}"), (f"{z} + {h}", f"{y} - {c2}"), (f"{z} + {h}", f"{y} + {c2}"),
                       (z, f"{y} + 2 * {c2}"), (f"{z} - {h}", f"{y} + {c2}"), (f"{z} - {h}", f"{y} - {c2}")]
                self.poly(sk, [(f"-({zz})", yy) for zz, yy in pts])
            self.done(sk)
            self.extrude(hw, self.profiles(sk), NEW, dist="nut_m", name=f"{label}_nuts")

        bolt("rear", "rs_win_front_x", 1, "rj_bolt_len", "rear_tongue_y", rz)
        nuts("rear", "rj_nut_x0", "rear_tongue_y", rz)
        bolt("front", "fj_head_x", -1, "fj_bolt_len", "front_tongue_y", fz)
        nuts("front", "fj_nut_x0", "front_tongue_y", fz)

        sk = self.sketch("front_head_pocket")
        self.rect(sk, "fj_head_x", "fj_head_x + fj_pocket_len", f"{fd} - 1 mm",
                  "front_tongue_y + joint_head_d / 2 + joint_head_clear")
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), CUT, sym="2 * (fj_bolt_z + joint_head_d / 2 + joint_head_clear)",
                     name="front_head_pocket")

        # ---- rear stock: comb beam and plate post stay at full width; the frame between them is
        # slimmed with coved pockets and opened by three straight-edged truss windows
        top = "rs_win_top"
        far = "-ibu_depth_max - 60 mm"
        sk = self.sketch("butt_slim")
        self.poly(sk, [("rs_win_rear_x", top), ("rs_rib2_x", top),
                       (f"rs_rib2_x + rib_lean * ({top} - ({far}))", far), ("rs_win_rear_x", far)])
        self.done(sk)
        side = "(comb_width - frame_width) / 2"
        for nm, start in (("face", "cast_z + frame_width / 2"), ("away", "cast_z - comb_width / 2")):
            f = self.extrude(rear, sk.profiles.item(0), CUT, start=start, dist=side, name=f"butt_slim_{nm}")
            ids = {fc.tempId for fc in f.faces}
            cove = [e for fc in f.faces for e in fc.edges
                    if self.sharp(e) and all(e.faces.item(i).tempId in ids for i in range(2))]
            self.fillet(rear.component, [(list({e.tempId: e for e in cove}.values()), "slim_cove")], f"butt_cove_{nm}")

        sk = self.sketch("butt_windows")
        r1a, r1b = "rs_rib1_x - frame_rib / 2", "rs_rib1_x + frame_rib / 2"
        r2a, r2b = "rs_rib2_x - frame_rib / 2", "rs_rib2_x + frame_rib / 2"
        self.poly(sk, [("rs_win_rear_x", top), (r1a, top), rib_hit(r1a),
                       ("rs_win_low_x", "rs_win_low_y"), ("rs_win_rear_x", "rs_win_low_y")])
        self.poly(sk, [(r1b, top), (r2a, top), rib_hit(r2a), rib_hit(r1b)])
        self.poly(sk, [(r2b, top), ("rs_win_front_x", top), ("rs_win_front_x", strut_y("rs_win_front_x")), rib_hit(r2b)])
        self.done(sk)
        f = self.extrude(rear, self.profiles(sk), CUT, sym="2 * comb_width", name="butt_windows")
        self.fillet_z_edges(rear, f, "win_round", "butt_windows_round")

        # ---- forestock: flush horizontal spare-mag slots on the away side, patterned by count
        away = self.offset_plane("away_side", "away_z")
        sk = self.sketch("mag_slot", away)
        self.rect(sk, "mag_holder_start", "mag_holder_start + mag_slot_len",
                  "mag_holder_top - mag_slot_h", "mag_holder_top")
        self.done(sk)
        slot = self.extrude(fore, sk.profiles.item(0), CUT, dist="face_side * mag_slot_depth", name="mag_slot")
        forec = fore.component
        ents = adsk.core.ObjectCollection.create()
        ents.add(slot)
        pin = forec.features.rectangularPatternFeatures.createInput(
            ents, forec.xConstructionAxis, self.vi("mag_holder_count"), self.vi("mag_slot_len + mag_holder_wall"),
            adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
        forec.features.rectangularPatternFeatures.add(pin).name = "mag_slots"

        # harness rail on the face side: two heat-set inserts, opposite the mag slots
        face = self.offset_plane("face_side_plane", "face_z")
        sk = self.sketch("harness_rail_inserts", face)
        for h in ("harness_rail_hole_1", "harness_rail_hole_2"):
            self.circle(sk, h, "harness_rail_y", "insert_hole_d")
        self.done(sk)
        self.extrude(fore, self.profiles(sk), CUT, dist="-face_side * insert_depth", name="harness_rail_inserts")

        # ---- TPU prone hand pad: a 3 mm skin over the belly behind the hand stop. It sits in a
        # recess (so no edge can peel), wraps up both sides and snaps in with a dovetail keel.
        pad = occs["pad"]
        ptop = f"{ffd} + pad_wrap"
        sk = self.sketch("pad_zone")
        self.rect(sk, "pad_x0", hp, f"{fd} - 1 mm", ptop)
        self.done(sk)
        self.extrude(pad, sk.profiles.item(0), NEW, sym="2 * body_width", name="pad_zone")
        self.combine((pad, body("pad")), [(fore, body("fore"))], INTERSECT, "pad_outer")
        self.extrude(fore, sk.profiles.item(0), CUT, sym="2 * body_width", name="pad_recess")
        sk = self.yz_sketch("pad_core", "pad_x0")
        hw_, lo = "body_width / 2 - pad_t", f"{ffd} + pad_t"
        self.poly(sk, [(f"-({hw_})", ptop), (hw_, ptop), (hw_, f"{lo} + belly_h"), (f"{hw_} - belly_w", lo),
                       (f"-({hw_} - belly_w)", lo), (f"-({hw_})", f"{lo} + belly_h")])
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), JOIN, dist=f"{hp} - pad_x0", name="pad_core")
        self.combine((pad, body("pad")), [(fore, body("fore"))], CUT, "pad_skin")
        kx0 = "pad_x0 + pad_t"
        sk = self.yz_sketch("pad_keel", kx0)
        kn, kw = "keel_w / 2", "keel_w / 2 + keel_flare"
        self.poly(sk, [(f"-({kn})", lo), (kn, lo), (kw, f"{lo} + keel_h"), (f"-({kw})", f"{lo} + keel_h")])
        self.done(sk)
        klen = f"{hp} - pad_t - ({kx0})"
        self.extrude(fore, sk.profiles.item(0), CUT, dist=klen, name="pad_keel_groove")
        self.extrude(pad, sk.profiles.item(0), JOIN, dist=klen, name="pad_keel")

        # ---- TPU grip: the whole hand surface is a TPU sleeve over a rigid core. The sleeve slides on
        # from below along the grip axis, is keyed by the core's section and the front spine (which also
        # carries the trigger-guard bar), and is locked by a rigid cap screwed into the core.
        grip, cap = occs["grip"], occs["cap"]
        gtop, gbot = "grip_top_y", "grip_top_y - grip_length"
        gb2 = f"{gbot} + cap_t"

        def grip_solid(occ, name, y_hi, y_lo):
            sk = self.sketch(name)
            self.poly(sk, [(gf(y_hi), y_hi), (gb(y_hi), y_hi), (gb(y_lo), y_lo), (gf(y_lo), y_lo)], arcs={1: "grip_back_r"})
            self.done(sk)
            self.extrude(occ, sk.profiles.item(0), NEW, start="grip_z0", dist="face_side * grip_width", name=name)
            b = occ.component.bRepBodies.item(0)
            long_edges = {}
            for f in b.faces:
                g = f.geometry
                if g.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType and abs(g.normal.z) > 0.99:
                    for e in f.edges:
                        if abs(e.startVertex.geometry.y - e.endVertex.geometry.y) > 0.1:
                            long_edges[e.tempId] = e
            self.fillet(occ.component, [(list(long_edges.values()), "grip_round")], f"{name}_girth")

        grip_solid(grip, "grip_outer", gtop, gb2)
        grip_solid(cap, "grip_cap", gb2, gbot)

        # no thumb shelf: Darren chose a clean grip (2026-11-24)

        # rigid core and front spine, trimmed to the grip's outer shape and joined to the main body
        sk = self.sketch("grip_core")
        ov = f"{gtop} + 3 mm"
        self.poly(sk, [(f"{gf(ov)} - tpu_wall", ov), (f"{gf(gb2)} - tpu_wall", gb2),
                       (f"{gb(gb2)} + tpu_wall", gb2), (f"{gb(ov)} + tpu_wall", ov)])
        self.done(sk)
        self.extrude(main, sk.profiles.item(0), NEW, start="grip_z0 + face_side * tpu_wall",
                     dist="face_side * (grip_width - 2 * tpu_wall)", name="grip_core")
        core = body("main", 1)
        long_edges = {}
        for f in core.faces:
            g = f.geometry
            if g.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType and abs(g.normal.z) > 0.99:
                for e in f.edges:
                    if abs(e.startVertex.geometry.y - e.endVertex.geometry.y) > 0.1:
                        long_edges[e.tempId] = e
        self.fillet(main.component, [(list(long_edges.values()), "grip_round - tpu_wall")], "grip_core_girth")
        sk = self.sketch("grip_spine")
        self.poly(sk, [(gf(ov), ov), (gf(gbm), gbm), (f"{gf(gbm)} - spine_d", gbm), (f"{gf(ov)} - spine_d", ov)])
        self.done(sk)
        self.extrude(main, sk.profiles.item(0), JOIN, start="grip_z0", dist="face_side * grip_width",
                     name="grip_spine", bodies=[body("main", 1)])
        self.combine((main, body("main", 1)), [(grip, body("grip"))], INTERSECT, "grip_core_trim")
        self.combine((main, body("main")), [(main, body("main", 1))], JOIN, "grip_core_join", keep=False)
        self.combine((grip, body("grip")), [(main, body("main"))], CUT, "grip_sleeve")

        # cap screw: M5 through the cap into a heat-set insert in the core
        ybot = self.ev(gbot)
        pl = self.offset_plane("cap_plane", gbot, root.xZConstructionPlane)
        if abs(pl.geometry.origin.y - ybot) > 0.01:
            pl.deleteMe()
            pl = self.offset_plane("cap_plane", f"-({gbot})", root.xZConstructionPlane)
        sk = self.sketch("cap_screw", pl)
        q = sk.modelToSketchSpace(adsk.core.Point3D.create(1, ybot, 1))
        cx = f"({gf(gbot)} - grip_depth / 2)"
        cz = "(-face_side * grip_offset)"
        ex = cx if q.x > 0 else f"-{cx}"
        ez = cz if q.y > 0 else f"-{cz}"
        self.circle(sk, ex, ez, "cap_screw_d")
        self.circle(sk, ex, ez, "insert_hole_d")
        self.done(sk)
        prs = sorted(self.profiles(sk), key=lambda pr: pr.areaProperties().area)
        self.extrude(cap, prs[-1], CUT, sym="2 * cap_t + 2 mm", name="cap_screw_hole")
        self.extrude(main, prs, CUT, sym="2 * (cap_t + insert_depth)", name="cap_insert_hole")

        if FUSE_ACTION:
            self.combine((main, body("main")), [(act, body("action"))], JOIN, "action_cradle_fused", keep=False)
        self.colour(occs)
        return occs

    def colour(self, occs):
        app = adsk.core.Application.get()
        lib = app.materialLibraries.itemByName("Fusion Appearance Library")
        names = {"rear": "Plastic - Matte (White)", "main": "Plastic - Matte (Gray)", "fore": "Plastic - Matte (White)",
                 "action": "Plastic - Matte (Blue)", "block": "Plastic - Matte (Black)", "grip": "Plastic - Matte (Yellow)", "pad": "Plastic - Matte (Yellow)", "cap": "Plastic - Matte (Black)"}
        for key, name in names.items():
            a = lib.appearances.itemByName(name) if lib else None
            if a:
                occs[key].appearance = self.d.appearances.itemByName(a.name) or self.d.appearances.addByCopy(a, a.name)
        self.root.isSketchFolderLightBulbOn = False
        self.root.isConstructionFolderLightBulbOn = False


def report(design, occs, problems=(), log=print):
    up = design.userParameters
    for key, occ in occs.items():
        if key == "hw":
            continue
        for b in occ.component.bRepBodies:
            bb = b.boundingBox
            size = [round((getattr(bb.maxPoint, a) - getattr(bb.minPoint, a)) * 10, 1) for a in "xyz"]
            log(f"{occ.component.name}: {b.name} valid={b.isValid} lumps={b.lumps.count} size_mm={size} "
                f"vol_cm3={b.volume:.0f} faces={b.faces.count}")
    for key in ("rear", "main", "fore", "block", "pad", "grip", "cap"):
        occ = occs[key]
        if not occ.component.bRepBodies.count:
            continue
        low = -min(b.boundingBox.minPoint.y for b in occ.component.bRepBodies) * 10
        log(f"{occ.component.name}: lowest point {low:.1f} mm below the bore")
    log(f"(MC 3.1.6.4 a: forestock depth incl. shelf, mag and guard <= {up.itemByName('ibu_depth_max').value * 10:.0f} mm; "
        "the standing block is part of the guard and counts; the butt hook does not)")
    bad = [up.item(i).name for i in range(up.count)
           if up.item(i).name.startswith("chk_") and up.item(i).value < -1e-7]
    log("chk_* below zero: " + (", ".join(bad) if bad else "none"))
    for n in ("action_type", "act_receiver_d", "act_screw_front_x", "act_screw_rear_x", "cradle_w",
              "rj_bolt_len", "fj_bolt_len", "block_length", "block_position", "grip_round"):
        log(f"{n} = {up.itemByName(n).value * 10:.1f} mm")
    tl = design.timeline
    errs = [f"{tl.item(i).name}: {tl.item(i).errorOrWarningMessage}" for i in range(tl.count)
            if tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState]
    log("timeline problems: " + ("; ".join(errs) if errs else "none"))
    log("skipped rounds: " + ("; ".join(problems) if problems else "none"))


def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design.userParameters.itemByName("lop") is None:
        raise RuntimeError("Run fusion_load_params.py first.")
    b = Builder(design)
    occs = b.build()
    report(design, occs, b.problems)
