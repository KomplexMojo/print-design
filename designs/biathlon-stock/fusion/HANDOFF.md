# Biathlon stock: handoff notes for whoever changes the design next

Read this before touching `fusion_build_demo.py`. The longer history is in `README.md` §10 and §11.

## Where things are
- `fusion_build_demo.py`: the whole Fusion model. `DEMO_PARAMS` (name, unit, expression, comment) at the top,
  then `Builder.build()`, which builds every component in order. `OBSOLETE_PARAMS` lists names to delete.
- `stock_params.py`: the parameter registry and the action presets (`ACTIONS`). `PARAMETERS.md` is generated from it.
- `fusion_render_views.py`: saves the standard views. `fusion_balance.py`: centre of gravity estimate.
- `../PARTS.md`: every bought part. `../brief.md`: requirements. `../part.py`: the older build123d model (not current).

## How to change and check
1. Edit `DEMO_PARAMS` and `build()`. Never edit the live Fusion timeline or user parameters by hand: recorded
   rounds break. Always rebuild from the script.
2. Rebuild in Fusion through the Fusion MCP `script` call: load `fusion_build_demo.py` with importlib and call
   `run('')`, then the same for `fusion_render_views.py` (set `STOCK_VIEWS_DIR`). A full run takes about five
   minutes and can outlast the MCP timeout; it still finishes. Write stdout to a log file and wait for it.
3. A build is good only if the report shows every body `valid=True lumps=1`, `chk_* below zero: none`,
   `timeline problems: none` and `skipped rounds: none`. Then look at the rendered views.
4. `python3 make_param_table.py`, run `pytest` here, update `README.md` and `PARTS.md`, commit.

## Rules that bite
- A new parameter must be defined above every parameter that uses it. A unitless parameter cannot be evaluated
  as millimetres (`mag_side * 1 mm`).
- A convex profile corner needs a radius of 0 or at least the edge round. A round needs a face taller than itself.
- Frame: X forward along the bore, 0 at the trigger. Y up, 0 on the bore. Z to the shooter's right.
- Rebuilds cost credits. Batch changes, one rebuild per request where possible.

## Decided. Do not revert
- Only stock length, cheek height, hand stop, harness positions and spare-mag side follow the athlete. Everything
  else is a fixed dimension, above all whatever meets the action and barrel.
- Standing block: rigid heel plus a plain rectangular tongue; the TPU is a sock over front, top, bottom and sides.
- Lower unit and action cradle are separate components, joined to the main body for printing. No fasteners.
- Harness: a raised boss on the forestock side opposite the mags, with a T-slot, mouth toward the butt, stop toward
  the muzzle, at the measured position. No rail, no through-hole, no added part.
- Behind the action the stock stays below the bolt for its 45 mm travel plus thumb room.
- Butt: one thickness, two rounded windows, rounded struts, plate post follows the butt plate curve.
- Spare-mag slots: 36 x 9.5 x 42 mm deep with rounded mouths, on the side away from the face. No indents opposite.
- No snag: every fastener head or nut is recessed. Every bought part is a real catalogue size, listed in PARTS.md.
- Every TPU part mounts on a rigid feature. No thumb shelf on the grip. Action bolt positions are explicit.
- IBU: 140 mm depth below the bore (block, guard and magazine count), cheek 40 mm, marking surface from 150 mm.

## Still open (waiting on Darren)
Harness block sizes and thread, rear harness attachment, bore-to-sight height, thumb room, action measurements and
3D scan, exact action bolt positions, release-lever zone, magazine slot corner radius.
