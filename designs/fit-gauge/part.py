"""fit-gauge: a calibration plate and pin that measure real fits on the H2S.

Print this first. Try the pin in each hole, then record which clearance gave a
press, snug, slide and loose fit with `printloop log fit-gauge`. The refine step
copies those numbers into printer/h2s.yaml so every later design uses them.
"""

from build123d import *

REVISION = 1
MATERIAL = "PLA"
SLICE_PROFILE = None

PARAMS = {
    "pin_d": 10.0,
    "clearances": [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40],  # per side, mm
    "pitch": 16.0,
    "plate_t": 5.0,
    "pin_h": 12.0,
    "label_size": 5.0,
    "foot_chamfer": 0.4,  # counters elephant's foot on the first layer
}


def plate(p: dict) -> Part:
    n = len(p["clearances"])
    length = n * p["pitch"] + 4
    width = p["pin_d"] + 14
    hole_y = 2.5
    with BuildPart() as part:
        Box(length, width, p["plate_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
        fillet(part.edges().filter_by(Axis.Z), radius=2)
        xs = [(i - (n - 1) / 2) * p["pitch"] for i in range(n)]
        for x, c in zip(xs, p["clearances"]):
            with Locations((x, hole_y, p["plate_t"])):
                Hole(radius=p["pin_d"] / 2 + c)
        # Chamfer the bottom edge of every hole so the squished first layer doesn't close it up.
        bottom_circles = part.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[0]
        chamfer(bottom_circles, length=p["foot_chamfer"])
        # Engraved rather than embossed: raised text strokes are thinner than two perimeters.
        with BuildSketch(Plane.XY.offset(p["plate_t"])):
            for x, c in zip(xs, p["clearances"]):
                with Locations((x, -width / 2 + 3.2)):
                    Text(f"{c:.2f}".lstrip("0"), font_size=p["label_size"])
        extrude(amount=-0.6, mode=Mode.SUBTRACT)
    return part.part


def pin(p: dict) -> Part:
    with BuildPart() as part:
        Cylinder(p["pin_d"] / 2, p["pin_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
        edges = part.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)
        chamfer(edges[0], length=p["foot_chamfer"])
        chamfer(edges[-1], length=0.8)
    return part.part


def build(p: dict = PARAMS):
    return {"plate": plate(p), "pin": pin(p)}
