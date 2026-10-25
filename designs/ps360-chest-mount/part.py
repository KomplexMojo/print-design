"""ps360-chest-mount: see brief.md for requirements.

Model the part in its print orientation: Z is up, the flat face that goes on the
bed is the lowest face. `printloop build ps360-chest-mount` drops it to z=0, exports STEP and
STL, and runs the printability checks.
"""

from build123d import *

from printloop import fits

# Bump on every change that gets printed, and add a row to brief.md's history.
REVISION = 1
MATERIAL = "PLA"
SLICE_PROFILE = None  # or a variant from printer/slicer.yaml, e.g. "strong"

# Every dimension a print might prove wrong belongs here, in mm.
PARAMS = {
    "length": 40.0,
    "width": 20.0,
    "height": 10.0,
    "hole_d": 5.0,
    "fillet": 1.0,
}


def build(p: dict = PARAMS):
    """Return one Part, or a dict of {name: Part} for multi-piece designs."""
    hole_d = fits.hole(p["hole_d"], "slide")  # a 5 mm rod slides through
    with BuildPart() as part:
        Box(p["length"], p["width"], p["height"], align=(Align.CENTER, Align.CENTER, Align.MIN))
        fillet(part.edges().filter_by(Axis.Z), radius=p["fillet"])
        with Locations(part.faces().sort_by(Axis.Z)[-1]):
            Hole(radius=hole_d / 2)
    return part.part


if __name__ == "__main__":
    # Live preview in the OCP CAD Viewer (VS Code) if it is installed.
    try:
        from ocp_vscode import show
        show(build())
    except ImportError:
        print(build().bounding_box())
