# print-designs

Design 3D-printed parts with Claude and build123d, print them on a Bambu Lab H2S,
and feed what comes off the bed back into the next revision.

```
 ideate ──► design ──► slice ──► print ──► refine ─┐
 brief.md   part.py    Bambu     H2S       log.yaml │
    ▲       + checks   Studio CLI                   │
    └───────────────────────────────────────────────┘
```

| Stage | What happens | Where it runs | Command |
|---|---|---|---|
| Ideate | Turn an idea into `brief.md`: purpose, measured dimensions, fits, loads, acceptance criteria | anywhere | `printloop new <name>` |
| Design | Write `part.py` in build123d, build, read the printability report and preview | anywhere (cloud or local) | `printloop build <name>` |
| Slice | Slice the STLs with your H2S presets; get print time and grams | your machine | `printloop slice <name>` |
| Print | Open the sliced file in Bambu Studio and press **Print plate** | your machine | `printloop print <name>` |
| Refine | Log the result and measurements, then change params, geometry, fits or slicer settings and bump the revision | anywhere | `printloop log <name> ...` |

## First-time setup on your machine

1. Install [uv](https://github.com/astral-sh/uv) and Python 3.11+.
2. Clone this repo and install the CLI:
   ```
   git clone https://github.com/KomplexMojo/print-designs.git
   cd print-designs
   uv venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
   uv pip install -e .
   ```
3. Re-flatten the slicer presets from your installed Bambu Studio (this picks up your version and any user presets):
   ```
   printloop profiles
   ```
   The committed `printer/profiles/` were generated from Bambu Studio's public H2S system presets, so slicing works without this step, but your local copy is the most accurate. To use your own presets, put their names in `printer/slicer.yaml` first.
4. Check slicing works:
   ```
   printloop build fit-gauge
   printloop slice fit-gauge
   ```
   If Bambu Studio isn't found, set `bambu_studio:` in `printer/slicer.yaml`.
5. Optional: Claude Code picks up `.mcp.json`, which starts [build123d-mcp](https://github.com/pzfreo/build123d-mcp) so Claude can render, measure and repair models while designing.

## Your first loop: calibrate fits

`designs/fit-gauge` is a plate with seven holes (0.05 to 0.40 mm clearance per side)
and a 10 mm pin. Print it, then log what you find, for example:

```
printloop log fit-gauge --result success \
  --measure pin_d=10.0:9.94 --measure hole_005=10.10:9.92 \
  --notes "press .05, snug .10, slide .20, loose .30"
```

The refine step copies those into `printer/h2s.yaml`, and every design that sizes
holes with `printloop.fits` picks them up on its next build.

## Fusion 360 fallback

Every build exports STEP next to the STL (`designs/<name>/out/<name>-r<N>.step`).
Open it in Fusion 360 to finish a part by hand; note in the brief that the design
left the parametric loop at that revision.

## Sending to the printer

Printing stays a deliberate, manual step: open the sliced `.gcode.3mf` in Bambu
Studio (`printloop print <name>`), check the plate preview, and press Print plate.
Sending directly over LAN would need LAN-only mode with the printer's access code
and is not set up.
