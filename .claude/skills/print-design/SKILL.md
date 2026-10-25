---
name: print-design
description: Model a 3D-printable part in build123d from its brief and get it through the H2S printability checks. Use when designing or changing designs/<name>/part.py in the print-designs repo.
---

# Design: parametric build123d model plus printability checks

Read `CLAUDE.md`, the design's `brief.md`, and its `log.yaml` (if this is a revision) first.

## Model
- Edit `designs/<name>/part.py`. Keep the template's shape: `REVISION`, `MATERIAL`, `SLICE_PROFILE`, `PARAMS`, `build(p)`.
- Use BuildPart (builder mode). Model in print orientation: Z up, the bed face is the lowest face.
- Every dimension from the brief, and every open question, is a `PARAMS` entry in mm. Name them after what they mean (`tube_od`, not `d2`).
- Size mating features with `from printloop import fits`: `fits.hole(10, "slide")`, `fits.shaft(8, "snug")`. Never hard-code clearances.
- For multi-piece designs return `{"base": ..., "lid": ...}`; each piece is exported, checked and sliced together.
- If the build123d-mcp tools are available, build up the part step by step there (render, measure, check) and then copy the final code into part.py. Its b123d-modeling and b123d-repair guidance applies.

## Design for the H2S (0.4 mm nozzle, 0.2 mm layers)
- Walls at least 1.2 mm (3 perimeters); 0.8 mm is the absolute minimum.
- Overhangs no steeper than 45° from vertical. Use chamfers, not fillets, on downward-facing edges. Fillets are fine on vertical edges and top faces.
- Horizontal holes: teardrop or flat-topped, or rotate so they print vertically.
- Chamfer the bottom edge 0.4 mm (elephant's foot), including holes that touch the bed.
- Text: engrave rather than emboss below 6 mm font size.
- Strength runs along layers. Put snap-fit arms and clips parallel to the bed.
- Bridges under about 20 mm are fine; longer ones need a rethink.
- Bed is 340 x 320 x 340 mm; split larger parts with alignment pins.

## Check
1. `printloop build <name>`; for a quick what-if use `--set key=value`.
2. Read `designs/<name>/out/report.md`. Fix every ❌. For each ⚠️ either fix it or add a sentence in the brief explaining why it is acceptable.
3. Look at `out/<name>-r<N>-preview.png` (Read the image) and compare it with the brief. Check that features face the right way and that nothing is floating.
4. Measure key features against the brief (bounding box in the report, or build123d-mcp measure tools).

## Finish
- If this revision will be printed and changed since the last print, bump `REVISION` and add a row to the brief's revision history (what changed and why, citing the log entry).
- Commit `<name> r<N>: <what changed>` and push.
- Tell Darren the size, the check status, the preview, and anything to watch on the print.

Next stage: print-slice-refine.
