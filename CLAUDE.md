# print-design

Parametric 3D-printed parts for a Bambu Lab H2S, designed with build123d and
run through one loop: **ideate → design → slice → print → refine**.

## Layout
- `designs/<name>/brief.md`: requirements and acceptance criteria. Source of truth for intent.
- `designs/<name>/part.py`: build123d model. Defines `REVISION`, `MATERIAL`, `SLICE_PROFILE`, `PARAMS`, and `build(p)`.
- `designs/<name>/photos/`: `ref/` photos Darren supplies while ideating, `print/` photos of results, captions in `index.yaml`. Always add them with `printloop photo` (resizes, strips GPS/EXIF).
- `designs/<name>/log.yaml`: one entry per print (result, measurements, issues, next changes).
- `designs/<name>/out/`: generated STEP, STL, preview PNG, check report, sliced `.gcode.3mf`. Only `report.md` and `*.slice.json` are tracked.
- `printer/h2s.yaml`: build volume, fit clearances, design rules. Fit values are calibrated from `designs/fit-gauge`.
- `printer/slicer.yaml` + `printer/profiles/`: Bambu Studio presets and their flattened CLI configs.
- `printloop/`: the CLI (`printloop --help`).

## Rules for working here
- Model every part in its print orientation: Z up, flat face on z=0. Prefer 45° chamfers over steep overhangs, teardrop horizontal holes, and chamfer bottom edges 0.4 mm for elephant's foot.
- Put every dimension a print could prove wrong in `PARAMS`. No magic numbers in `build()`.
- Size mating features with `printloop.fits` (`fits.hole(d, "slide")`, `fits.shaft(d, "snug")`), never hard-coded clearances, so recalibration flows into every design.
- Run `printloop build <name>` after every change and read `out/report.md`. Look at `out/*-preview.png`. Fix fails; fix warns or explain them in the brief.
- When the build123d-mcp server is available, use it for stepwise modeling, rendering and measuring, then save the final code into `part.py`.
- Bump `REVISION` and add a row to the brief's revision history whenever a changed design will be printed. Never edit an old log entry except to fill in its results.
- Slicing needs Bambu Studio, which lives on Darren's machine, not in cloud sessions. In the cloud, build and check, commit, and hand off slicing.
- Commit design changes with the revision in the message, e.g. `fit-gauge r2: widen pitch`.

## Commands
```
pip install -e .                 # once per environment
printloop new <name>             # copy designs/_template
printloop photo <name> FILE... [--kind ref|print] --caption "..."
printloop build <name> [--set key=value]
printloop slice <name> [--profile strong]   # Darren's machine only
printloop print <name>           # opens the sliced file in Bambu Studio
printloop log <name> --result success|partial|fail --measure feat=exp:meas --issue ... --next ...
printloop status
printloop profiles               # re-flatten presets after a Bambu Studio update
```
