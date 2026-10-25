# ps360-chest-mount

## Purpose
Replacement for the broken camera mount on an Insta360 chest strap ("PS360" in the
request). The original is a round, keyed disc that sits on the strap's chest plate,
clamped by the strap's connector screw through its centre, with a 3-prong
GoPro-style hinge (clevis) on its rim that takes the camera arm. **One of the three
prongs has snapped off at the root (the outer one on the broken side), which is why a
new part is needed.** The replacement is the whole part with all three prongs. It must
fit this exact chest plate and connector screw, and accept the same camera arm.

Schematic of the original: [schematic.png](schematic.png) ([svg](schematic.svg)).
Product page: https://store.insta360.com/ca/product/chest_strap (lists compatible
cameras only; no dimensions, materials or mount details).

## Reference photos
The calliper's digital display was off in every photo, so each value below was read
off the beam's millimetre scale at the slider edge and cross-checked against the inch
scale. Treat them as about ±0.5 mm. None is good enough to model a fit from without a
re-measure.

| Photo | Shows | Dimensions taken from it |
|---|---|---|
| front-face-outside-jaws-across-the-disc | Front face, outside jaws across the disc | Disc OD ≈ 30.7 mm |
| disc-edge-on-jaws-across-disc-thickness | Disc edge-on, clevis above | Disc thickness ≈ 5.8 mm |
| inside-jaws-in-the-centre-screw-hole | Inside jaws in the centre hole | Screw hole Ø ≈ 11.8 mm |
| inside-jaws-in-the-keyed-back-recess | Inside jaws in the back recess | Keyed recess Ø ≈ 22.4 mm |
| outside-jaws-across-the-neck-block-below | Outside jaws across the block under the prongs | Neck width ≈ 16.5 mm (includes the snapped prong's stub) |
| knife-jaws-on-one-clevis-prong | Knife jaws on one prong; stub of the snapped third prong on the right | Prong thickness ≈ 3.4 mm |
| knife-jaws-near-the-clevis-root-feature | Knife jaws near the clevis root | Reads ≈ 5.0 mm, but which feature is measured is unclear: not used (possibly the pivot hole) |
| back-face-knife-jaws-straddling-a-featur | Back face, jaws straddling something behind the centre hole | Reads ≈ 4.4 mm, feature unclear: not used |
| back-face-jaws-in-the-keyed-recess-beam- | Jaws in the keyed recess; clevis edge-on showing a prong gap | Keyed recess Ø ≈ 22.5 mm (agrees with 22.4); prong gap ≈ 3.0 mm scaled from pixels, no jaws on it |
| back-face-close-up-outer-rim-lip-1-mm-ke | Back face close-up | None (shows the rim lip, recess step and notch steps) |
| back-face-outer-rim-keyed-recess-with-tw | Back face: outer rim step, keyed recess, two notches 180° apart | None (no scale) |
| insta360-chest-strap-the-part-sits-on-th | Product photo of the chest strap | None (shows how the part sits on the chest plate) |
| side-profile-clevis-arm-curves-from-the- | Side profile of the clevis arm and disc | Calliper scale too blurred to read. Arm shape and plate/hub split scaled from the 30.7 mm disc in frame, ±2 mm |
| side-profile-jaws-from-the-disc-back-fac | Side profile, jaws from the disc's back face to the far tip of the pivot lobe | **Back face to lobe tip ≈ 28.7 mm** (beam scale, ±0.5). Pivot position and lobe radius scaled from this photo, ±1 mm |
| clean-side-profile-of-the-arm-and-pivot- | Clean side profile of the arm, no scale | Outer edge fits one circle (2 px residual): R ≈ 22.8 mm, centre ≈ 15.9 mm from the pivot toward the axis and level with it (scaled by the 13.9 mm lobe, ±1) |
| inside-jaws-in-the-pivot-hole-of-a-survi | Inside jaws in the pivot hole of a surviving prong | Pivot hole Ø ≈ 5.1 mm (beam scale, mm and inch agree). Pivot position not measurable from this view |
| side-profile-jaws-across-the-pivot-lobe- | Jaws across the pivot lobe through the hole centre, perpendicular to the disc axis | Lobe width ≈ 13.9 mm (beam scale; mm reads 13.7, inch reads 14.1). Hole sits midway between the jaws, so lobe R ≈ 6.95 |
| inside-jaws-in-the-gap-between-the-two-s | Inside jaws in the gap between the two surviving prongs | Prong gap ≈ 3.4 mm (beam scale; mm reads 3.3, inch 3.5). The jaw tips touch both inner faces near the top of the prongs |

## Requirements

| Requirement | Value | Source |
|---|---|---|
| Disc outside diameter | 30.7 mm | calliper beam scale, ±0.5 |
| Disc overall thickness | 5.8 mm | calliper beam scale, ±0.5 |
| Centre hole for the connector screw | Ø 11.8 mm | calliper beam scale, ±0.5 |
| Back keyed recess (engages chest plate) | Ø 22.4 mm | calliper beam scale, ±0.5 |
| Recess depth | ≈ 1.0 mm | Darren, rough |
| Recess keys: two notches at 180° | width, depth unknown | photo, count only |
| Angle of the notches relative to the clevis | unknown | |
| Outer rim step on the back face | width, height unknown | photo, shape only |
| Disc plate thickness / raised front hub | plate ≈ 3.6 mm + hub Ø ≈ 15.5 × ≈ 2.2 mm (sums to the 5.8 total) | scaled from side-profile photo, ±2 |
| Width across the 3-prong root | 16.5 mm (measured across the broken prong's stub) | calliper beam scale, ±0.5 |
| Clevis: **3 prongs** (one missing), pivot axis parallel to the disc face | count | Darren |
| Prong thickness (each of the 3) | 3.4 mm | calliper beam scale on a surviving prong, ±0.5 |
| Gap between prongs (2 gaps) | 3.4 mm; 3 × 3.4 + 2 × 3.4 = 17.0 against the 16.5 root reading, within the ±0.5 tolerance of each | calliper beam scale, ±0.5 |
| Pivot hole Ø | 5.1 mm (GoPro-standard M5 thumbscrew clearance is ≈ 5.2) | calliper beam scale, ±0.5 |
| Arm profile | leaves the disc rim, curves outward past the rim, then down to the pivot lobe, with a large inside fillet to the front hub (see schematic side view) | side-profile photo |
| Arm outer edge shape | one circular arc centred on the disc/hub axis, level with the pivot, tangent to the lobe's outer side: R = 15 + 6.95 = 21.95 | Darren (circle on the hub centre) + fit to the clean profile photo (R ≈ 22.8, centre within 0.3 mm of pivot level, ±1) |
| Where that arc leaves the rim | ≈ 6.1 mm from the back face (follows from the arc) | derived; Darren chose this fit over the earlier 2 mm |
| Overall depth: disc back face to the far tip of the pivot lobe | 28.7 mm | calliper beam scale, ±0.5 |
| Prong lobe outer radius | 6.95 mm (13.9 mm across) | calliper beam scale, ±0.25 on the radius |
| Pivot centre from the back face | 21.75 mm (28.7 − 6.95) | derived from two calliper readings, ±0.6 |
| Pivot centre from the disc axis | 15 mm (just inside the rim) | Darren, measured |
| Front index mark (small slot on the rim opposite the clevis) | cosmetic, size not needed | photo |

## Mating parts and fits
- **Chest plate keyed boss → back recess:** slide (`fits.hole(22.4, "slide")`), so it
  seats by hand and the notches index it without rocking.
- **Connector screw → centre hole:** loose clearance (`fits.hole(d, "loose")`); the
  screw clamps the disc, it does not locate it.
- **Camera arm (2-prong) → clevis (3-prong):** the arm's two prongs drop into the two
  gaps with a slide fit, so it swings when the thumbscrew is loose and holds when it is
  tight; pivot hole `fits.hole(d, "slide")` for the thumbscrew shank.

## Loads and environment
Worn outdoors on the body while moving: the camera's weight acts as a lever on the
clevis, plus impacts and vibration. The original lost a prong at its root, so each
prong root needs a fillet, not a sharp corner, and the outer prongs must not be thinned. Expect sun, sweat and
rain, and a hot car. Clamp load from the connector screw compresses the disc.

## Material and print setup
- **PETG** (`petg` slicer variant) with the `strong` wall and infill settings; a combined variant gets added when slicing. PLA softens near 55 °C, which a
  car dashboard in summer exceeds. ASA if UV becomes an issue.
- **Orientation (proposed):** print on its side, with the clevis plane flat on the bed,
  so layers run along the prongs and through their roots rather than across them.
  Printing disc-face-down would put layer lines exactly where the original prong snapped.
  The trade-off is that the disc and the keyed recess are then vertical, which costs
  roundness on the recess; check it in the first print and switch if the recess fit
  suffers. Decide once the clevis geometry is known.

## Acceptance criteria
- [ ] Back recess seats onto the chest plate by hand, both notches engage, and the disc
      does not rock.
- [ ] The connector screw passes through freely and clamps the disc so it does not turn
      under a firm hand twist.
- [ ] All three prongs are present and the camera arm's 2-prong end slides into the
      gaps without forcing; the thumbscrew passes through all five prongs.
- [ ] With the thumbscrew tight, the arm holds its angle under the camera's weight.
- [ ] Each prong survives a firm sideways hand bend with no cracking at its root.
- [ ] Measured with calipers: disc OD, thickness and hole within ±0.2 mm of the
      re-measured original.

## Open questions
Each becomes a `PARAMS` entry so a print can settle it.

1. Re-measure with the calliper display on: disc OD, thickness, centre hole, recess Ø
   (the photo values are ±0.5 mm).
2. Recess depth to ±0.1 (Darren estimates 1 mm), notch width and depth, and the notch
   angle relative to the clevis.
3. Outer rim step on the back: width and height.
4. Front hub: diameter and height with the calliper (photo gives Ø≈15.5 × 2.2).
5. Clevis: prong thickness and gap both read 3.4 but sum 0.5 over the root width; a display
   reading on one prong, one gap and the root would settle which is off.
6. The camera arm's 2-prong end: its gap and prong thickness, so the replacement's
   gaps are sized to the arm rather than to the worn original.
7. A photo of the chest plate with the part removed, and of the connector screw (head Ø
   and thread), so the mating side is known rather than inferred from the broken part.

## Revision history
| Rev | Change | Why |
|---|---|---|
| 0 | Schematic and requirements from photos | Start of redesign; nothing printed yet |
