# fit-gauge

## Purpose
Measure how this H2S, nozzle and filament actually print mating parts, so the
fit clearances in `printer/h2s.yaml` come from real prints instead of guesses.
Print it first, and again whenever the nozzle, filament type or slice profile changes.

## Requirements
| Requirement | Value | Source |
|---|---|---|
| Pin diameter | 10.00 mm nominal | design choice |
| Hole clearances per side | 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40 mm | covers press to loose |
| Labels readable | engraved 0.6 mm, 5 mm text | |

## Mating parts and fits
The pin against each hole. Holes are modeled at exact clearance with no shrink
compensation, because measuring that shrink is the point.

## Loads and environment
None.

## Material and print setup
PLA, default profile (0.20mm Standard @BBL H2S), both parts flat on the bed as modeled.

## Acceptance criteria
- [ ] Pin diameter measured with calipers (record as `pin_d=10.0:<measured>`)
- [ ] Smallest hole diameter measured (record as `hole_005=10.10:<measured>`)
- [ ] For each fit type, note the smallest clearance that achieves it:
  press (needs force), snug (holds, removable by hand), slide (moves freely, no wobble), loose (drops in)

## Open questions
None.

## Revision history
| Rev | Change | Why |
|---|---|---|
| 1 | First version | |
