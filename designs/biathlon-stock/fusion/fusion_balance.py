"""Fusion 360 script (read-only): where does the assembled rifle balance?

Darren's goal (2026-11-24): in the standing position the standing block is the pivot, so the assembled
rifle should balance where the centre of the support-hand thumb sits on the block.

The script takes each printed body's volume and centroid from the model, turns volume into mass with a
density and a solid fraction (walls plus infill), adds the non-printed masses below, and reports the
centre of gravity along the bore (X, mm ahead of the trigger blade) against the balance point.

Everything in PRINTED and HARDWARE is a placeholder until weighed. Run it after fusion_build_demo.py.
"""

import adsk.core
import adsk.fusion

# component name: (density g/cm3, solid fraction of the modelled volume)
PRINTED = {
    "rear_stock": (1.06, 0.60),        # PAHT-CF; 0.60 = walls plus sparse infill, to be replaced by sliced weights
    "main_body": (1.06, 0.70),
    "forestock": (1.06, 0.60),
    "action_cradle": (1.06, 0.90),
    "standing_block": (1.06, 0.70),
    "sling_clamp": (1.05, 0.90),       # ASA
    "grip_cap": (1.05, 0.90),
    "tpu_grip": (1.22, 0.80),          # TPU
    "tpu_prone_pad": (1.22, 1.00),
    "tpu_block_cover": (1.22, 0.90),
}

# name: (mass g, X of its centre of gravity as a User Parameter expression in mm)
HARDWARE = {
    # Anschütz biathlon brochure 2024: barrelled action about 1880 g, 730 mm long. Its own balance point is a guess
    # (35 % of its length from the rear of the receiver) until Darren balances it on a finger.
    "barrelled action 1827 F": (1880, "action_rear + 0.35 * 730 mm"),
    "rear sight (diopter)": (150, "action_rear + 40 mm"),
    "front sight with snow cover": (90, "action_rear + 700 mm"),
    "magazine in the well, loaded": (45, "(mag_well_x0 + mag_well_x1) / 2"),
    "spare magazines, loaded (x4)": (180, "mag_holder_start + 2 * (mag_slot_len + mag_holder_wall)"),
    "joint and action fasteners": (90, "(rear_split + front_split) / 2"),
    "butt hook and plate hardware": (0, "-lop"),
    "ballast": (0, "block_position"),
}

BALANCE_POINT = "block_position"       # where the support-hand thumb sits; the middle of the block until measured


def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    um = design.unitsManager
    rows = []
    for occ in design.rootComponent.occurrences:
        name = occ.component.name
        if name not in PRINTED:
            continue
        rho, fill = PRINTED[name]
        for b in occ.component.bRepBodies:
            c = b.physicalProperties.centerOfMass
            rows.append((name, b.volume * rho * fill, c.x * 10))
    for name, (mass, expr) in HARDWARE.items():
        rows.append((name, float(mass), um.evaluateExpression(expr, "mm") * 10))
    total = sum(m for _, m, _ in rows)
    cog = sum(m * x for _, m, x in rows) / total
    target = um.evaluateExpression(BALANCE_POINT, "mm") * 10
    lo = um.evaluateExpression("blk_rear_x", "mm") * 10
    hi = um.evaluateExpression("blk_front_x", "mm") * 10
    print(f"{'item':<34}{'mass g':>8}{'x mm':>8}")
    for name, m, x in rows:
        print(f"{name:<34}{m:>8.0f}{x:>8.0f}")
    printed = sum(m for n, m, _ in rows if n in PRINTED)
    print(f"printed parts {printed:.0f} g, total {total:.0f} g (IBU minimum 3500 g without magazines)")
    print(f"centre of gravity: {cog:.0f} mm ahead of the trigger")
    print(f"standing block: {lo:.0f} to {hi:.0f} mm, balance point {target:.0f} mm")
    off = cog - target
    print(f"the rifle balances {abs(off):.0f} mm {'ahead of' if off > 0 else 'behind'} the balance point"
          + (" (on the block)" if lo <= cog <= hi else " (off the block)"))
    # mass needed at the butt plate, or at the forend tip, to bring the centre of gravity onto the balance point
    for label, expr in (("at the butt plate", "-lop + 20 mm"), ("at the forend tip", "forend_tip - 20 mm")):
        x = um.evaluateExpression(expr, "mm") * 10
        if (x - target) * off < 0:
            print(f"ballast to balance: {total * off / (target - x):.0f} g {label}")
