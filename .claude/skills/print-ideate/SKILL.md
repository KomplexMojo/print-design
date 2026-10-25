---
name: print-ideate
description: Turn an idea for a 3D-printed part into a design brief in the print-designs repo. Use when Darren describes something new to print or asks to start a design.
---

# Ideate: capture requirements for a printed part

Goal: a `designs/<name>/brief.md` that is specific enough to model without guessing.

1. Pick a short kebab-case name and run `printloop new <name>` from the repo root
   (`pip install -e .` first if `printloop` is missing).
2. Fill in brief.md from what Darren said. For each section that is thin, ask, in one
   message, only the questions whose answers change the geometry:
   - Functional dimensions: what it mounts to or holds, measured with calipers where possible. Record the source of every number (measured, datasheet, estimate).
   - Mating parts and the fit each needs: press, snug, slide or loose (values in `printer/h2s.yaml`).
   - Loads and environment: force direction, heat (PLA softens near 55 °C; suggest PETG or ASA for cars, outdoors, dishwashers), UV, water, food contact, flexing or snap fits.
   - Size limits and how it will be installed or assembled.
   - Material and look, if Darren cares.
3. Propose a print orientation and say why (strength runs along layers, not across them; flat face down; avoid supports). Note it in "Material and print setup".
4. Write acceptance criteria that can be checked with calipers or a quick hand test.
5. List unknowns under "Open questions" and plan to expose each as a `PARAMS` entry so a print can settle it.
6. If an existing design is close, say so and suggest deriving from it instead.
7. Commit: `<name>: brief`.

Do not start modeling until the critical dimensions have a source. A best guess is fine
when Darren says so; mark it "estimate" so the first print checks it.

Next stage: print-design.
