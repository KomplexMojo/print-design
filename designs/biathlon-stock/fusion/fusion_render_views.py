"""Fusion 360 script: save review images of the stock (sides, top, bottom, isos, exploded).

Set OUT_DIR (module global or environment variable STOCK_VIEWS_DIR) before calling run().
The exploded views move the occurrences apart for the picture and put them back afterwards.
"""

import os

import adsk.core
import adsk.fusion

OUT_DIR = os.environ.get("STOCK_VIEWS_DIR", os.path.expanduser("~/stock-views"))
SIZE = (2000, 1000)

# name: (eye direction from the target, up vector)
VIEWS = {
    "01_left_side": ((0, 0, -1), (0, 1, 0)),
    "02_right_side": ((0, 0, 1), (0, 1, 0)),
    "03_top": ((0, 1, 0), (0, 0, -1)),
    "04_bottom": ((0, -1, 0), (0, 0, 1)),
    "05_iso_left_front": ((0.9, 0.45, -1), (0, 1, 0)),
    "06_iso_right_rear": ((-0.9, 0.45, 1), (0, 1, 0)),
    "07_iso_left_below": ((0.6, -0.55, -1), (0, 1, 0)),
    "07b_iso_right_above": ((0.5, 0.9, 1), (0, 1, 0)),
}
# exploded offsets in mm, by component name
EXPLODE = {
    "rear_stock": (-70, 0, 0), "forestock": (70, 0, 0), "tpu_grip": (-12, -55, 0), "grip_cap": (-22, -95, 0),
    "tpu_prone_pad": (70, -45, 0), "action_cradle": (0, 60, 0), "guard_block": (0, -40, 0), "tpu_block_cover": (0, -85, 0), "sling_clamp": (70, -30, 0),
}
EXPLODED_VIEWS = {"08_exploded_left": VIEWS["05_iso_left_front"], "09_exploded_right_below": ((-0.7, -0.4, 1), (0, 1, 0)),
                  "10_exploded_left_side": VIEWS["01_left_side"]}


def shoot(app, name, eye_dir, up, only=None):
    vp = app.activeViewport
    cam = vp.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.target = adsk.core.Point3D.create(5, -5, 0)
    cam.eye = adsk.core.Point3D.create(5 + eye_dir[0] * 300, -5 + eye_dir[1] * 300, eye_dir[2] * 300)
    cam.upVector = adsk.core.Vector3D.create(*up)
    cam.isFitView = True
    cam.isSmoothTransition = False
    vp.camera = cam
    vp.fit()
    adsk.doEvents()
    vp.refresh()
    path = os.path.join(OUT_DIR, name + ".png")
    vp.saveAsImageFile(path, *SIZE)
    return path


def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    os.makedirs(OUT_DIR, exist_ok=True)
    only = os.environ.get("STOCK_VIEWS_ONLY", "").split(",") if os.environ.get("STOCK_VIEWS_ONLY") else None
    for name, (eye, up) in VIEWS.items():
        if only is None or name[:2] in only:
            print(shoot(app, name, eye, up))
    moved = []
    for occ in root.occurrences:
        d = EXPLODE.get(occ.component.name)
        if d and any(d):
            t = occ.transform2
            keep = t.copy()
            t.translation = adsk.core.Vector3D.create(d[0] / 10, d[1] / 10, d[2] / 10)
            occ.transform2 = t
            moved.append((occ, keep))
    for name, (eye, up) in EXPLODED_VIEWS.items():
        if only is None or name[:2] in only:
            print(shoot(app, name, eye, up))
    for occ, keep in moved:
        occ.transform2 = keep
    adsk.doEvents()
