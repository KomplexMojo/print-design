---
name: print-slice-refine
description: Slice a print-design part for the Bambu H2S, hand it off to print, log how it came out, and turn the result into the next revision. Use after a design passes its checks, or when Darren reports a print result.
---

# Slice, print, log, refine

## Slice (needs Bambu Studio, so Darren's machine)
- On Darren's machine (local Claude Code or a Remote Control session in Darren's clone):
  `git pull`, then `printloop build <name>` and `printloop slice <name> [--profile <variant>]`.
  Report plate time and grams from the output.
- In a cloud session there is no Bambu Studio. Commit and push the design, then either start
  a Remote Control session on Darren's machine with those commands, or give Darren the two
  commands to run.
- If slicing fails, read `designs/<name>/out/slice.log`. Preset errors usually mean
  `printer/profiles/` is stale: run `printloop profiles`. Unknown preset names: check
  `printer/slicer.yaml` against the names Bambu Studio shows.
- Commit the `*.slice.json` summary so later sessions can see time and weight.

## Print (Darren's step)
- `printloop print <name>` opens the newest sliced file in Bambu Studio. Darren checks the
  plate preview and presses Print plate. Never send to the printer without being asked.
- Remind Darren of the brief's acceptance criteria so Darren knows what to measure.

## Log the result
When Darren reports back, record it even if Darren only gives a sentence:
```
printloop log <name> --result success|partial|fail \
  --measure <feature>=<expected>:<measured> \
  --issue "<what went wrong>" --next "<change for next revision>" \
  --photo designs/<name>/photos/print/<file> --notes "..."
```
Ask for the measurement behind any fit or size complaint ("too tight": which feature, by how much?).
Add photos of the print first with `printloop photo <name> <file> --kind print --caption "..."`,
then pass the stored path to `--photo`. Look at each one for defects Darren didn't mention
(stringing, layer shift, warped corners, sagging overhangs) and ask about them. Commit `<name> r<N>: print log`.

## Refine
Read the whole `log.yaml` and the brief, then sort each issue into one of four fixes:

| Symptom | Fix |
|---|---|
| A specific dimension is off on this part only | change that `PARAMS` value |
| Fits are off across parts (holes tight, pins fat) | update `fits` or `hole_shrink_mm` in `printer/h2s.yaml`; note it in the fit-gauge log |
| Shape problem: sagging overhang, weak layer line, warped corner | change geometry (chamfer, rib, orientation, split) |
| Surface quality, stringing, strength from infill | change the slicer variant in `printer/slicer.yaml`, then `printloop profiles` |

Then bump `REVISION`, add a revision-history row in the brief that cites the log entry,
rebuild with print-design's checks, and commit `<name> r<N+1>: <change>`.
A design is done when every acceptance criterion is ticked in the brief; say so and stop iterating.
For a fit-gauge result, update `printer/h2s.yaml` fits from the clearances that gave each fit.
