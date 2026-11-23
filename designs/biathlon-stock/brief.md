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
| Main body | wrist, pistol grip, trigger guard, action inlet, mag well, standing shooting block (integral), IBU marking faces | ~380–435 mm | diagonal on its side (≤ ~440 mm) |
| Forestock | printed fixed hand stop with sling attachment, front harness connector, spare-mag holders | ~380 mm | diagonal on its side |

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
| `block_position` (trigger blade to centre of the standing shooting block) | 150 | estimate; from sheet Z and proposed AJ |
| `block_height` (bore to block bottom, where the support hand bears) | 130 | estimate; from sheet Z (support hand height) and Y; capped at 140 |
| `block_length` / `block_width` / `block_palm_angle_deg` | 90 / 55 / 10 | estimate; from F, G, J (support hand) |

### Split position (computed)
The standing block and the IBU marking surface both sit on the main body, so the front
joint goes forward of both. Checks:
- `front_split` ≥ max(block front edge, marking surface end) + 15 mm joint margin
- `rear_split` (behind trigger) + `front_split` ≤ ~435 mm so the main body fits diagonally
- If `block_position` forces the main body past the plate, flag it; fallback is moving the
  rear split forward of the comb (more length on the rear stock).

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

Parameters that can break a rule: `block_height` (the shooting block is usually the lowest point of the forend, so it sets the 140 mm depth directly), `handstop_height` (if they hang below the forend they count toward the 140 mm depth), hand stop or harness connector placed inside the marking surface, `sling_slot_width`, `grip_length`, forend depth,
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
4b. ~~Standing hand rest?~~ Decided 2026-11-23: a shooting block printed as part of the
   main body, position and shape from Darren's measurements. Proposed sheet addition:
   AJ current trigger blade to centre of the support hand in standing. If sheet Z asks for
   more than 140 mm below the bore, the block is capped and flagged.
5. Target total weight and balance point.
6. Is TC / national federation approval for a printed stock being pursued (deadline 1 May)?
7. Sub-zero behaviour of PAHT-CF prints: test coupons before the final print.

8. ~~Scan or trace?~~ Decided 2026-11-23: phone scan of grip and cheek (about 1 mm accuracy), calipers for the inlet and screw positions.
9. ~~Action screws?~~ Decided 2026-11-23: reuse current screws. Darren measures thread and length; pillars and inlet floor sized to them.
10. ~~Barrel?~~ Decided 2026-11-23: Darren measures with calipers (diameter every 50 mm from the action, total length); channel gets 2 mm free-float clearance. Snow cover or tube still to confirm.
11. ~~Trigger guard?~~ Decided 2026-11-23: reuse the metal guard, inletted into the main body (already closed and rigid per IBU). Its outline goes into the 140 mm check.
12. ~~Glove?~~ Decided 2026-11-23: thin race gloves. `glove_thickness` parameter, default 2 mm (estimate), added to grip and guard clearance; Darren confirms with calipers.
13. ~~Clothing?~~ Decided 2026-11-23: measure in race suit plus base layer. `clothing_allowance` parameter for colder days.
14. ~~Grip style?~~ Decided 2026-11-23: vertical grip, thumb rest along the left side, palm swell on the right (`palm_swell` parameter).
15. ~~Joint hardware?~~ Decided 2026-11-23: M6 stainless bolts and cross-dowels; bought aluminium pillars (or tube cut to length).
16. ~~Ballast?~~ Decided 2026-11-23: sealed ballast pockets in butt and forend now; fill with steel or tungsten after weighing the printed rifle.
17. ~~Model output?~~ Decided 2026-11-23: each revision exports STL for printing and STEP for Fusion.
18. ~~First print?~~ Decided 2026-11-23: PLA fit test of grip and comb shells on the current rifle first.

## r1 rough prototype (2026-11-23)
Built before measurements, for a left-handed male, 178 cm. Every fit value is an estimate
and every hardware value is a placeholder (generic 32 mm action, 22 mm barrel, 22 × 50 mm mag).
Purpose: check overall proportions and the 3-part split, not fit to the rifle.

What r1 changed from the layout above, and why:
- **Main body is straight on the plate (323 mm), not diagonal.** With the grip and the standing
  block hanging 130–140 mm below the bore, the main body's outline is as tall as it is long at
  both ends, so it no longer fits diagonally. Splits are at -108 (just behind the grip) and +215
  mm from the trigger, and the joint tongues are on the rear stock and forestock so the main body
  stays under 330 mm.
- **Front joint is pulled together by two M6 tie rods** whose heads sit in the mag well's front
  wall and whose nuts are steel cross-dowels in the forestock (+250 mm). That keeps every bolt
  head out of the marking surface (150–200 mm, measured from the trigger).
- **Rear joint is a 40 mm tongue with two lateral M6 bolts** through the wrist. Only ~50 mm of wrist
  depth at the split; watch it on the first flex test.
- Handedness only labels the sides: LH and RH stocks are mirror images, so the cheek side and
  thumb rest always print on top and the palm side lies on the bed. `palm_swell` is not modelled
  yet (it would sit on the bed face).
- Trigger guard is a printed loop as a placeholder for the metal guard (Q11).
- Butt-plate radius default raised to 150 mm (60 mm over a 120 mm plate is a half circle);
  hook is set by `hook_drop`, `hook_reach`, `hook_radius`.

Check notes:
- Main body ⚠️ overhangs (6 %): ceilings of the action inlet, trigger slot, mag well and joint
  sockets. These are bedding and fit surfaces, so print with tree supports painted only there.
- IBU computed checks pass: depth below bore 130 mm (block), comb 40 mm, marking surface 50 mm
  flat both sides, no joint or bolt head in it, sling slot 41 mm.
- Grip bottom is 135 mm below the bore. It is not forestock under MC 3.1.6.4 a, but kept under 140 anyway.

## Revision history
| Rev | Change | Why |
|---|---|---|
| 1 | Brief, then r1 rough 3-part model from 178 cm LH estimates | proportions and split check before measurements; see r1 notes above |
