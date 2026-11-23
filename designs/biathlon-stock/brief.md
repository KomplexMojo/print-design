# biathlon-stock

## Purpose
A parametric, 3D-printed biathlon rifle stock fitted to one athlete. Body measurements
(arm segments, hand, finger reach, cheek-to-eye height and so on) drive the CAD parameters,
so the same model can be re-fitted for another athlete by changing one parameter set.
It must stay legal under the IBU Material Catalogue and survive racing at -30 °C to +30 °C.

Research behind this brief (project files):
- `research/ibu-stock-rules.md`: IBU limits and equipment-control rules
- `research/biometric-parameters.md`: measurements B1 to B20 and the parameter list
- `research/h2s-materials-and-3-part-split.md`: materials, joints, 3-part layouts

## Reference photos
No photos from Darren yet. Web reference images of commercial stocks are in the project
files under `reference-images/biathlon-stocks/` (see its INDEX.md). They are not copied
into this public repo, and no dimensions are taken from them (no scale in frame).

| Photo | Shows | Dimensions taken from it |
|---|---|---|
| (needed) action out of stock, side and bottom, ruler in frame | inlet outline, screw positions, mag well | inlet profile, bedding points |
| (needed) current stock, side and top, ruler in frame | baseline fit to copy or improve | LOP, comb, grip, forend depth |
| (needed) athlete prone and standing, side view, tape in frame | posture | B17, B18, B19 |

## Layout (chosen 2026-11-23)
Three parts, all printed on their side (Example 2 in the materials research):

| Part | Holds | Approx. length | On the plate |
|---|---|---|---|
| Rear stock | butt plate, printed butt hook, rear harness connector, comb / cheek piece (one piece, no adjusters) | ~220 mm | flat on its side |
| Main body | wrist, pistol grip, trigger guard, action inlet, mag well | ~380 mm | diagonal on its side (≤ ~440 mm) |
| Forestock | printed fixed hand stop with sling attachment, front harness connector, standing raiser, spare-mag holders, IBU marking faces | ~380 mm | diagonal on its side |

Joints: tapered tongue (rear) and dovetail (front), each with steel bolts into steel
cross-dowels, disc-spring washers and a sealed joint line. Tool-only, no quick release.

## Requirements

### Fixed by hardware (all unknown until the action is chosen)
| Requirement | Value | Source |
|---|---|---|
| Action model | ? | Darren |
| Inlet profile, length, bedding screw positions | ? | calipers / drawing |
| Barrel channel diameter and free-float clearance | ? | calipers |
| Trigger unit outline and trigger blade position | ? | calipers |
| Magazine well position and mag outline | ? | calipers |
| Bore height above inlet floor | ? | calipers |
| Sight line height above bore (diopter + front globe) | ? | calipers |
| Sling clip type and width (≤ 40 mm) | ? | Darren / calipers |
| Harness clip type that the printed connectors must accept | ? | Darren / calipers |
| Spare magazine holders (count, location) | ? | Darren |

### Fit (from the athlete; defaults are estimates until measured)
| Parameter | Default | Source |
|---|---|---|
| `lop` (single value for prone and standing) | 335 | estimate, from B2/B3/B11; check against current butt setting |
| `comb_height_above_bore` | per sights | B14, B19 |
| `comb_cast` | 0–10 | B15, B16 |
| `buttplate_length` / `curve_radius` / `cant_deg` / `drop` | 120 / 60 / 0 / 70 | estimate, B12/B13 |
| `hook_length` / `hook_drop` / `hook_radius` (printed butt hook, under the armpit) | 90 / 60 / 25 | estimate, B13/B17; check against current hook |
| `grip_angle_deg` | 85 | estimate |
| `grip_circumference` / `grip_length` | 140 / 95 | estimate, B8/B9, B4/B5 |
| `trigger_reach` | 70 | estimate, B6 |
| `thumb_rest_height` / `depth` | 45 / 12 | estimate, B10 |
| `handedness` | right | assumed, B16 |
| `handstop_position` (trigger blade to hand-stop face, fixed, printed in place) | 380 | estimate; from sheet V with B, C, D; check against AG |
| `handstop_height` / `sling_slot_width` | 25 / 41 | estimate; slot sized for a ≤ 40 mm sling |
| `harness_front_position` / `harness_rear_position` (from trigger blade) | ? / ? | from AH, AI (current rifle) until a body-based rule is agreed |
| `standing_raiser_height` | 40 | estimate, B18 |

### IBU compliance (computed checks in the model, flag on failure)
| Check | Limit | Rule |
|---|---|---|
| Forestock depth below bore incl. mag and trigger guard | ≤ 140 mm | MC 3.1.6.4 a |
| Cheek piece thickness | ≤ 40 mm | 3.1.6.4 b |
| Folding stock | none; joints tool-only and rigid | 3.1.6.4 c |
| Trigger guard | closed and rigid | 3.1.6.4 g |
| Rifle weight excl. mags and ammo | ≥ 3.5 kg (ballast pockets if short) | 3.1.6.4 i |
| Marking surface | flat, ≥ 40 mm high, both sides, starts 150 mm in front of trigger; no joint or bolt heads in it | 3.1.6.4 l |
| Electronics / batteries | none | MC 1.3 b |

Parameters that can break a rule: `handstop_height` and `standing_raiser_height` (if they hang below the forend they count toward the 140 mm depth), hand stop or harness connector placed inside the marking surface, `sling_slot_width`, `grip_length`, forend depth,
mag-well position (all feed the 140 mm check), comb cast/thickness, forestock joint
position (marking surface), and infill/ballast (weight).

## Mating parts and fits
- Action to inlet: epoxy skim-bedded on aluminium pillars; printed inlet gets a loose fit
  (0.40) to leave room for bedding compound.
- Barrel: free-floated, ≥ 2 mm clearance in the channel.
- Joint tongues and dovetails: tapered, snug (0.15) at full engagement.
- Cross-dowels and pillars: press (0.10) into printed bores, bonded.
- Magazine in well and spare holders: slide (0.25), with a positive retention catch.
- Hand stop: printed in place on the forestock, no rail. Sling swivel or strap slot through it.
- Harness connectors: printed in place on rear stock and forestock; mating clip fit (slide or snug) set once the clip is measured.
- Butt plate and butt hook: printed as part of the rear stock, no adjustment hardware. TPU pad bolted on with heat-set inserts.

## Loads and environment
- Recoil (.22 LR) is negligible. Real loads: prone sling tension through the hand stop,
  body weight on butt and grip, harness loads while skiing, drops on snow and ice.
- Stiffness and creep under the action matter most; the zero must not wander with
  temperature or moisture.
- -30 °C to +30 °C, snow, meltwater, UV. Joints sealed against water ingress.
- PLA prototypes are for indoor fitting only. PETG for outdoor dry-fire.

## Material and print setup
- Prototype: PLA (fit), PETG (outdoors), 0.4 mm nozzle, AMS 2 Pro. Same joint geometry and
  metal hardware as the final.
- Final structural parts: PAHT-CF, 0.6 mm hardened nozzle, dried 80 °C right before printing,
  external spool, chamber 60–65 °C, annealed. ASA accessories, TPU butt pad.
- Orientation: every part on its side, so the stock profile lies in the layer plane and
  the vertical bending loads (sling, butt, grip) run along layers, not across them. The
  side face is the largest flat face; the action inlet and barrel channel then run
  horizontally and need teardrop or flat-topped sections to avoid support.
- 100 % infill (or 6+ walls) within ~20 mm of every bolt, dowel and pillar.

## Acceptance criteria
- [ ] Each part fits the H2S plate (340 × 320 mm, diagonal ≤ 440 mm) with 5 mm margin
- [ ] Action drops into the bedded inlet and torques down without rocking (feeler gauge 0.05 mm)
- [ ] Barrel free-float: a sheet of paper slides the full channel length
- [ ] Joints assemble with tools only and show no play when the stock is flexed by hand
- [ ] Depth below bore incl. mag and guard measures ≤ 140 mm with calipers
- [ ] Marking surface ≥ 40 mm high on both sides, flat, starting 150 mm ahead of trigger
- [ ] Cheek piece thickness ≤ 40 mm
- [ ] Assembled rifle weighs ≥ 3.5 kg without mags
- [ ] Trigger finger pad lands on the blade with the grip held naturally (athlete check)
- [ ] Eye lines up with the diopter in prone without lifting or pressing the head
- [ ] Joints hold torque after a night at -30 °C (freezer) and a 1 m drop on the butt

## Open questions
Each will be a `PARAMS` entry so a print can settle it.
1. Which action and sights? Everything in "Fixed by hardware" depends on it.
2. The athlete is Darren. Need B1–B20 plus side photos in prone and standing.
3. ~~One butt or two?~~ Decided 2026-11-23: one fixed butt for both positions, all
   dimensions derived from Darren's measurements, with a printed hook. Darren's current
   adjustable modular butt settings are the best check for the derived values.
4. ~~Hand stop and harness?~~ Decided 2026-11-23: both printed in place at fixed positions
   set from Darren's measurements; the hand stop keeps a sling/strap attachment.
   Still open: spare-mag holders, and which clips the sling and harness use.
   Measurement sheet (project files `reference/measurement-diagram/`) letters used:
   V elbow to hand stop (prone), B/C/D arm segments. Proposed additions to the sheet:
   AG current trigger to hand-stop distance, AH and AI current trigger to front and rear
   harness connector distances.
5. Target total weight and balance point.
6. Is TC / national federation approval for a printed stock being pursued (deadline 1 May)?
7. Sub-zero behaviour of PAHT-CF prints: test coupons before the final print.

## Revision history
| Rev | Change | Why |
|---|---|---|
| 1 | Brief | |
