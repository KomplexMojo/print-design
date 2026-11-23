"""Fusion 360 script: build the demo 3-part stock from the User Parameters.

Run after fusion_load_params.py in the same design. Every sketch point is pinned by two
driving dimensions whose expressions are User Parameter expressions, so changing a
parameter (or re-running the loader with a new fit record) moves the geometry. Features
take their depths from parameter expressions too. Nothing is typed as a number except the
sketch datum (a fixed point 1000 mm below and behind the trigger, so every dimension stays
positive whatever sign a coordinate has).

Layout (see README.md §5):
  root      = skeleton: user parameters, the side-outline sketch with the two split lines,
              signed side planes (away_z, thumb plane)
  rear_stock / main_body / forestock = components; each extrudes its own region of the
              shared outline (creationOccurrence) and adds its own features.

Handedness: every lateral feature uses face_side / bolt_dir signed planes and distances.
Nothing is mirrored.

Demo shortcuts (flag in the doc, not in the print model): no edge chamfers or grip
rounding, no teardrop holes, no tie rods, no harness inserts, no mag window or finger scallops.
"""

import math

import adsk.core
import adsk.fusion

DATUM = 1000.0  # mm

# r2 values (PR 3) that differ from the r1 registry defaults: written as [manual] so the
# loader leaves them alone on the next run. New demo-only shape parameters are [demo].
DEMO_PARAMS = [
    ("sight_line_above_bore", "mm", "50 mm", "[manual] r2: AB + P puts the comb at the current 20 mm"),
    ("forend_tip", "mm", "455 mm", "[manual] r2: room for four flush slots"),
    ("block_ramp", "mm", "5 mm", "[manual] r2: block front stays inside the main body"),
    ("grip_depth", "mm", "40 mm", "[manual] r2: from grip_circumference"),
    ("grip_width", "mm", "36 mm", "[manual] r2"),
    ("mag_holder_start", "mm", "222 mm", "[manual] r2 flush slots"),
    ("mag_holder_wall", "mm", "3.5 mm", "[manual] r2 web between slots"),
    ("mag_holder_top", "mm", "-17 mm", "[manual] r2 bore to top of the slots"),
    ("front_tongue_height", "mm", "22 mm", "[manual] r2"),
    ("front_tongue_y", "mm", "-40 mm", "[manual] r2: joint below the slots"),
    ("finger_hole_x1", "mm", "40 mm", "[manual] r2 guard opening front"),
    ("finger_hole_y0", "mm", "-110 mm", "[manual] r2 guard opening bottom"),
    ("hook_thickness", "mm", "30 mm", "[demo] butt face to the hook's underside corner"),
    ("grip_top_y", "mm", "-50 mm", "[demo] bore to grip top"),
    ("grip_toe", "mm", "5 mm", "[demo] grip bottom corner cut"),
    ("grip_lean", "", "tan(90 deg - grip_angle_deg)", "[demo] grip lean per mm of height"),
    ("wrist_under_y", "mm", "-55 mm", "[demo] bore to wrist underside"),
    ("wrist_ramp", "mm", "7 mm", "[demo]"),
    ("wrist_heel_x", "mm", "-130 mm", "[demo]"),
    ("wrist_heel_y", "mm", "-52 mm", "[demo]"),
    ("comb_nose", "mm", "12 mm", "[demo] heel to comb, and comb to wrist ramps"),
    ("tip_round", "mm", "8 mm", "[demo] forend tip and hook corner cut"),
    ("hook_round", "mm", "6 mm", "[demo]"),
    ("butt_bot_y", "mm", "-buttplate_drop - buttplate_length / 2", "[demo] derived: bore to butt-plate toe"),
    ("hook_tip_y", "mm", "butt_bot_y - hook_drop", "[demo] derived"),
    ("grip_front_x", "mm", "-trigger_reach + grip_depth / 2", "[demo] derived: grip front at its top"),
    ("mag_slot_len", "mm", "spare_mag_h + 2 * fit_snug", "[demo] slot along X (mags lie horizontally)"),
    ("mag_slot_h", "mm", "spare_mag_t + 2 * fit_snug", "[demo] slot height"),
    ("mag_slot_depth", "mm", "spare_mag_l + fit_snug", "[demo] lateral insertion depth"),
]


def gf(y):
    """Grip front X at height y (y at or below the grip top)."""
    return f"grip_front_x - grip_lean * (grip_top_y - ({y}))"


class Builder:
    def __init__(self, design):
        self.d = design
        self.root = design.rootComponent
        self.um = design.unitsManager

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

    def offset_plane(self, name, expr):
        inp = self.root.constructionPlanes.createInput()
        inp.setByOffset(self.root.xYConstructionPlane, self.vi(expr))
        pl = self.root.constructionPlanes.add(inp)
        pl.name = name
        return pl

    def extrude(self, occ, profiles, op, *, sym=None, dist=None, start=None, name=None):
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
            inp.participantBodies = [b.createForAssemblyContext(occ) for b in comp.bRepBodies]
        if sym:
            inp.setSymmetricExtent(self.vi(sym), True)
        else:
            if start:
                inp.startExtent = adsk.fusion.OffsetStartDefinition.create(self.vi(start))
            inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(self.vi(dist)),
                                 adsk.fusion.ExtentDirections.PositiveExtentDirection)
        try:
            f = ext.add(inp)
        except Exception as e:
            bodies = [(b.name, [round(v * 10) for v in (b.boundingBox.minPoint.x, b.boundingBox.maxPoint.x,
                                                         b.boundingBox.minPoint.y, b.boundingBox.maxPoint.y)])
                      for b in comp.bRepBodies]
            raise RuntimeError(f"{name} in {comp.name} failed: {e}; bodies {bodies}") from None
        if name:
            f.name = name
        return f

    # ---------------------------------------------------------------- build
    def params(self):
        up = self.d.userParameters
        for name, unit, expr, comment in DEMO_PARAMS:
            p = up.itemByName(name)
            if p is None:
                up.add(name, self.vi(expr), unit, comment)
            elif not p.comment.startswith("[manual]") or p.comment.startswith(comment[:8]):
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
        self.params()
        self.clear()
        root = self.root

        occs = {}
        for key, label in (("rear", "rear_stock"), ("main", "main_body"), ("fore", "forestock")):
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = label
            occs[key] = occ

        # ---- skeleton: side outline + split lines (one sketch, three regions)
        sk = self.sketch("skeleton_outline")
        P = [
            ("-lop", "-buttplate_drop + buttplate_length / 2"),                  # 0 heel
            ("-lop + comb_nose", "comb_top"),
            ("-lop + comb_length", "comb_top"),
            ("action_rear - comb_nose", "wrist_top"),
            ("action_rear", "0 mm"),
            ("forend_tip - tip_round", "0 mm"),
            ("forend_tip", "-tip_round"),
            ("forend_tip", "-forend_depth + tip_round"),
            ("forend_tip - tip_round", "-forend_depth"),
            ("block_position + block_length / 2 + block_ramp", "-forend_depth"),  # shelf front
            ("block_position + block_length / 2", "-block_height"),
            (gf("-block_height"), "-block_height"),                               # guard bar to grip
            ("grip_front_x", "wrist_under_y"),
            ("-trigger_reach - grip_depth / 2 - wrist_ramp", "wrist_under_y"),
            ("wrist_heel_x", "wrist_heel_y"),
            ("-lop + hook_thickness", "hook_tip_y - tip_round"),
            ("-lop - hook_reach + hook_round", "hook_tip_y - hook_round"),
            ("-lop - hook_reach", "hook_tip_y"),                                  # 17 hook tip
            ("-lop", "butt_bot_y"),                                               # 18 toe
        ]
        self.poly(sk, P, arcs={17: "hook_radius", 18: "buttplate_curve_radius"})
        for xs in ("rear_split", "front_split"):
            self.poly(sk, [(xs, "sight_line_above_bore + 50 mm"), (xs, "-ibu_depth_max - 60 mm")], closed=False)
        self.done(sk)
        regions = sorted((sk.profiles.item(i) for i in range(sk.profiles.count)),
                         key=lambda pr: pr.boundingBox.minPoint.x)
        assert len(regions) == 3, f"expected 3 outline regions, got {len(regions)}"
        rear_pr, main_pr, fore_pr = regions

        self.extrude(occs["rear"], rear_pr, NEW, start="cast_z - comb_width / 2", dist="comb_width", name="rear_blank")
        self.extrude(occs["main"], main_pr, NEW, sym="body_width", name="main_blank")
        self.extrude(occs["fore"], fore_pr, NEW, sym="body_width", name="fore_blank")

        # ---- main body: grip (away skin, grip_width toward the face)
        sk = self.sketch("grip")
        lean = "grip_lean * grip_length"
        bot = "grip_top_y - grip_length"
        back = "grip_front_x - grip_depth"
        self.poly(sk, [("grip_front_x", "grip_top_y"), (back, "grip_top_y"),
                       (f"{back} - {lean}", f"{bot} + grip_toe"), (f"{back} - {lean} + grip_toe", bot),
                       (f"grip_front_x - {lean} - grip_toe", bot), (f"grip_front_x - {lean}", f"{bot} + grip_toe")])
        self.done(sk)
        self.extrude(occs["main"], sk.profiles.item(0), JOIN, start="away_z", dist="face_side * grip_width", name="grip")

        # thumb rest on the grip's face-side skin
        thumb = self.offset_plane("thumb_plane", "away_z + face_side * grip_width")
        sk = self.sketch("thumb_rest", thumb)
        self.rect(sk, f"{back} + grip_toe", "grip_front_x - grip_toe",
                  "-thumb_rest_height - 6 mm", "-thumb_rest_height + 6 mm")
        self.done(sk)
        self.extrude(occs["main"], sk.profiles.item(0), JOIN, dist="face_side * thumb_rest_depth", name="thumb_rest")

        # trigger guard opening (printed guard; rear edge is the grip front)
        sk = self.sketch("guard_opening")
        self.poly(sk, [("grip_front_x", "finger_hole_y1"), ("finger_hole_x1", "finger_hole_y1"),
                       ("finger_hole_x1", "finger_hole_y0"), (gf("finger_hole_y0"), "finger_hole_y0"),
                       ("grip_front_x", "grip_top_y")])
        self.done(sk)
        self.extrude(occs["main"], sk.profiles.item(0), CUT, sym="2 * body_width", name="guard_opening")

        # action inlet, mag well, bolt notch (hardware side), barrel channel
        sk = self.sketch("action_inlet")
        self.rect(sk, "action_rear", "action_front", "-bore_above_inlet_floor", "sight_line_above_bore")
        self.done(sk)
        self.extrude(occs["main"], sk.profiles.item(0), CUT, sym="action_width + 2 * fit_loose", name="action_inlet")

        sk = self.sketch("mag_well")
        self.rect(sk, "mag_well_x0 - fit_slide", "mag_well_x1 + fit_slide", "-forend_depth", "-bore_above_inlet_floor")
        self.done(sk)
        self.extrude(occs["main"], sk.profiles.item(0), CUT, sym="mag_well_width + 2 * fit_slide", name="mag_well")

        sk = self.sketch("bolt_notch")
        self.rect(sk, "bolt_notch_x - bolt_notch_length / 2", "bolt_notch_x + bolt_notch_length / 2",
                  "-bolt_notch_depth", "sight_line_above_bore")
        self.done(sk)
        self.extrude(occs["main"], sk.profiles.item(0), CUT, dist="bolt_dir * body_width", name="bolt_notch")

        sk = self.sketch("barrel_channel")
        self.rect(sk, "action_front", "forend_tip + tip_round", "-(barrel_d / 2 + barrel_float)", "sight_line_above_bore")
        self.done(sk)
        for k in ("main", "fore"):
            self.extrude(occs[k], sk.profiles.item(0), CUT, sym="barrel_d + 2 * barrel_float", name="barrel_channel")

        # ---- joints: tongues on rear stock and forestock, sockets in the main body
        sk = self.sketch("rear_joint")
        ry, rh = "rear_tongue_y", "rear_tongue_height"
        self.rect(sk, "rear_split - fit_loose", "rear_split + rear_tongue_length", f"{ry} - {rh} / 2", f"{ry} + {rh} / 2")
        self.done(sk)
        self.extrude(occs["rear"], sk.profiles.item(0), JOIN, sym="rear_tongue_width", name="rear_tongue")
        sk = self.sketch("rear_socket")
        self.rect(sk, "rear_split - fit_loose", "rear_split + rear_tongue_length + fit_snug",
                  f"{ry} - {rh} / 2 - fit_snug", f"{ry} + {rh} / 2 + fit_snug")
        self.done(sk)
        self.extrude(occs["main"], sk.profiles.item(0), CUT, sym="rear_tongue_width + 2 * fit_snug", name="rear_socket")
        sk = self.sketch("rear_bolts")
        for bx in ("rear_split + rear_tongue_length / 4", "rear_split + 3 * rear_tongue_length / 4"):
            self.circle(sk, bx, ry, "hole_d_bolt")
        self.done(sk)
        prs = [sk.profiles.item(i) for i in range(sk.profiles.count)]
        for k in ("rear", "main"):
            self.extrude(occs[k], prs, CUT, sym="2 * body_width", name="rear_bolt_holes")

        sk = self.sketch("front_joint")
        fy, fh = "front_tongue_y", "front_tongue_height"
        self.rect(sk, "front_split - front_tongue_length", "front_split + fit_loose", f"{fy} - {fh} / 2", f"{fy} + {fh} / 2")
        self.done(sk)
        self.extrude(occs["fore"], sk.profiles.item(0), JOIN, sym="front_tongue_width", name="front_tongue")
        sk = self.sketch("front_socket")
        self.rect(sk, "front_split - front_tongue_length - fit_snug", "front_split + fit_loose",
                  f"{fy} - {fh} / 2 - fit_snug", f"{fy} + {fh} / 2 + fit_snug")
        self.done(sk)
        self.extrude(occs["main"], sk.profiles.item(0), CUT, sym="front_tongue_width + 2 * fit_snug", name="front_socket")
        sk = self.sketch("cross_dowel")
        self.circle(sk, "cross_dowel_x", fy, "hole_d_dowel")
        self.done(sk)
        self.extrude(occs["fore"], sk.profiles.item(0), CUT, sym="2 * body_width", name="cross_dowel")

        # ---- forestock: hand stop with sling slot
        sk = self.sketch("hand_stop")
        self.rect(sk, "handstop_position", "handstop_position + handstop_length",
                  "-forend_depth - handstop_height", "-forend_depth + tip_round")
        self.done(sk)
        self.extrude(occs["fore"], sk.profiles.item(0), JOIN, sym="body_width", name="hand_stop")
        sk = self.sketch("sling_slot")
        sx0 = "handstop_position + (handstop_length - sling_slot_width) / 2"
        sy = "-forend_depth - handstop_height / 2"
        self.rect(sk, sx0, f"{sx0} + sling_slot_width", f"{sy} - sling_slot_height / 2", f"{sy} + sling_slot_height / 2")
        self.done(sk)
        self.extrude(occs["fore"], sk.profiles.item(0), CUT, sym="2 * body_width", name="sling_slot")

        # ---- forestock: flush horizontal spare-mag slots on the away side, patterned by count
        away = self.offset_plane("away_side", "away_z")
        sk = self.sketch("mag_slot", away)
        self.rect(sk, "mag_holder_start", "mag_holder_start + mag_slot_len",
                  "mag_holder_top - mag_slot_h", "mag_holder_top")
        self.done(sk)
        slot = self.extrude(occs["fore"], sk.profiles.item(0), CUT, dist="face_side * mag_slot_depth", name="mag_slot")
        fore = occs["fore"].component
        ents = adsk.core.ObjectCollection.create()
        ents.add(slot)
        pin = fore.features.rectangularPatternFeatures.createInput(
            ents, fore.xConstructionAxis, self.vi("mag_holder_count"), self.vi("mag_slot_len + mag_holder_wall"),
            adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
        pat = fore.features.rectangularPatternFeatures.add(pin)
        pat.name = "mag_slots"

        return occs


def report(design, occs, log=print):
    up = design.userParameters
    for key, occ in occs.items():
        for b in occ.component.bRepBodies:
            bb = b.boundingBox
            size = [round((getattr(bb.maxPoint, a) - getattr(bb.minPoint, a)) * 10, 1) for a in "xyz"]
            log(f"{occ.component.name}: {b.name} valid={b.isValid} size_mm={size} "
                f"vol_cm3={b.volume:.0f} faces={b.faces.count}")
    for key, occ in occs.items():
        low = -min(b.boundingBox.minPoint.y for b in occ.component.bRepBodies) * 10
        log(f"{occ.component.name}: lowest point {low:.1f} mm below the bore")
    log(f"(MC 3.1.6.4 a: forestock depth incl. shelf, mag and guard <= {up.itemByName('ibu_depth_max').value * 10:.0f} mm; "
        "the butt hook and pistol grip are not forestock)")
    bad = [up.item(i).name for i in range(up.count)
           if up.item(i).name.startswith("chk_") and up.item(i).value < -1e-7]
    log("chk_* below zero: " + (", ".join(bad) if bad else "none"))
    tl = design.timeline
    errs = [f"{tl.item(i).name}: {tl.item(i).errorOrWarningMessage}" for i in range(tl.count)
            if tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState]
    log("timeline problems: " + ("; ".join(errs) if errs else "none"))


def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design.userParameters.itemByName("lop") is None:
        raise RuntimeError("Run fusion_load_params.py first.")
    occs = Builder(design).build()
    report(design, occs)
