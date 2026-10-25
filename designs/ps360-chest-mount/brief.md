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
| IMG_5447 (Darren, 2026-10-25) | Back face at an angle: rim lip, keyed ring with two tabs, sunken centre | Ring stands about 1 mm proud (Darren). Sunken surface Ø ≈ 15 scaled from the disc, ±1. Supersedes the "recess" and "notch" readings above |
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
| Back keyed ring (engages chest plate) | Ø 22.4 mm, standing about 1 mm proud of the back face (not a recess) | calliper beam scale, ±0.5; direction from Darren and photo IMG_5447, 2026-10-25 |
| Sunken surface inside the ring, around the screw hole | Ø ≈ 15, depth unknown | photo IMG_5447 scaled from the 30.7 disc, ±1; Darren |
| Ring height below the back face | ≈ 1.0 mm | Darren, rough |
| Ring keys: two tabs at 180°, one toward the clevis | width, length unknown | photo IMG_5447, shape only |
| Angle of the tabs relative to the clevis | ≈ 0° (one tab faces the clevis) | photo IMG_5447 |
| Outer rim step on the back face | width, height unknown | photo, shape only |
| Front face | one sloped plane, no hub: 5.8 thick at the rim under the clevis, about 3.6 opposite it | Darren, STL vs photo, 2026-10-25; the 3.6 is a guess |
| Width across the 3-prong root | 16.5 mm (measured across the broken prong's stub) | calliper beam scale, ±0.5 |
| Clevis: **3 prongs** (one missing), pivot axis parallel to the disc face | count | Darren |
| Prong thickness (each of the 3) | 3.4 mm | calliper beam scale on a surviving prong, ±0.5 |
| Gap between prongs (2 gaps) | 3.4 mm; 3 × 3.4 + 2 × 3.4 = 17.0 against the 16.5 root reading, within the ±0.5 tolerance of each | calliper beam scale, ±0.5 |
| Pivot hole Ø | 5.1 mm (GoPro-standard M5 thumbscrew clearance is ≈ 5.2) | calliper beam scale, ±0.5 |
| Arm profile | rises from the front face just inside the rim and curves out to the pivot lobe; the inner edge narrows to a neck under the lobe, then sweeps onto the front face | Darren, STL vs photo, 2026-10-25 |
| Arm outer edge shape | one smooth curve from the front face (13.8 from the axis, leaving at about 60°) to the lobe's outer side | traced from the side photo, scaled by the pivot hole, ±1 |
| Where the curve starts | on the front face, not partway up the rim (the first draft started it 6.1 up the rim) | Darren |
| Overall depth: disc back face (around the ring) to the far tip of the pivot lobe | 28.7 mm | calliper beam scale, ±0.5 |
| Prong lobe outer radius | 6.95 mm (13.9 mm across) | calliper beam scale, ±0.25 on the radius |
| Pivot centre from the back face | 21.75 mm (28.7 − 6.95) | derived from two calliper readings, ±0.6 |
| Pivot centre from the disc axis | 15 mm (just inside the rim) | Darren, measured |
| Front index mark (small slot on the rim opposite the clevis) | cosmetic, size not needed | photo |

## Mating parts and fits
- **Back keyed ring → chest plate recess:** slide (`fits.shaft(22.4, "slide")`), so it
  seats by hand and the tabs index it without rocking.
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
- **PETG** with the `strong` wall and infill settings: the `petg-strong` slicer variant (added in r1; its flattened profiles are copies of `filament-petg` and `process-strong`, so re-run `printloop profiles` after a Bambu Studio update). PLA softens near 55 °C, which a
  car dashboard in summer exceeds. ASA if UV becomes an issue.
- **Orientation (proposed):** print on its side, with the clevis plane flat on the bed,
  so layers run along the prongs and through their roots rather than across them.
  Printing disc-face-down would put layer lines exactly where the original prong snapped.
  The trade-off is that the disc and the keyed ring are then vertical, which costs
  roundness on the ring; check it in the first print and switch if the ring fit
  suffers. Decide once the clevis geometry is known.

## Acceptance criteria
- [ ] Back ring seats into the chest plate by hand, both tabs engage, and the disc
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

1. Re-measure with the calliper display on: disc OD, thickness, centre hole, ring Ø
   (the photo values are ±0.5 mm).
2. Ring height to ±0.1 (Darren estimates 1 mm), its inner Ø, the sunken surface's depth,
   and tab width and length.
3. Outer rim step on the back: width and height.
4. Front face: thickness at the rim opposite the clevis (3.6 is a guess).
5. Clevis: prong thickness and gap both read 3.4 but sum 0.5 over the root width; a display
   reading on one prong, one gap and the root would settle which is off.
6. The camera arm's 2-prong end: its gap and prong thickness, so the replacement's
   gaps are sized to the arm rather than to the worn original.
7. A photo of the chest plate with the part removed, and of the connector screw (head Ø
   and thread), so the mating side is known rather than inferred from the broken part.

## Design notes (r1)
How `part.py` turns the requirements above into geometry, and what was assumed where
the brief has no number. Every value below is a `PARAMS` entry.

- **Back face (from Darren's photo IMG_5447).** The keyed ring stands 1 mm proud of the
  back face, into the chest plate, rather than being cut 1 mm into it as the first draft had
  it. The ring is `fits.shaft(22.4, "slide")` = 21.9 across, with two tabs
  `fits.shaft(3.0, "slide")` = 2.5 wide sticking 1.0 past it, one toward the clevis. Inside the
  ring, a Ø15 surface around the screw hole is sunk 1.5 below the ring's face, which is 0.5 into
  the back face. That depth is a guess, so measure it. The 5.8 thickness and the 21.75 pivot
  are still measured from the back face around the ring, so the part is 6.8 thick at the ring
  and 29.7 to the lobe tip. If the 28.7 reading was taken from the ring instead, set
  `pivot_from_back` to 20.75.
- **Fits.** Centre hole
  `fits.hole(11.0, "loose")` = 11.9, assuming an 11.0 connector screw so the hole matches
  the original 11.8. Pivot hole `fits.hole(5.0, "slide")` = 5.6 for an M5 thumbscrew.
- **Clevis.** Prongs 3.4. Gaps 3.4 = `arm_prong_t` 2.9 (assumed, open question 6) plus a
  slide fit, so the width across the prongs is 17.0. The gaps are cut to a flat floor 8.55
  below the pivot (arm lobe 6.95 + loose 0.4 + root fillet 1.2), across the whole neck, with a
  1.2 mm fillet at every prong root. A round-bottomed gap left thin webs where it grazed the
  narrower neck.
- **Front face and arm (from Darren's STL vs photo comparison).** The front face is one
  plane sloping from 5.8 thick under the clevis to 3.6 opposite it. There is no hub. The arm
  stands on that face. Its outer edge is a spline that leaves the face 13.8 from the axis at
  60° and meets the lobe's outer side vertically. Its inner edge runs down from the lobe's
  inner side through a neck at 12.2 from the axis and 10.5 from the back, then sweeps onto
  the face at 7.5 from the axis. All of this is traced from the side photo, scaled by the
  pivot hole, ±1. The lobe (R6.95) and prongs (3.4) were checked against the photo and are
  unchanged.
- **Guesses for unknowns.** Tab size and sunken-surface depth above. Outer rim step 1.0 wide × 0.5 high, cut as a relief, so a wrong
  guess cannot stop the disc seating. Index mark: 0.8 × 4 × 0.4 slot on the front face
  opposite the clevis.
- **Orientation.** `orientation: side` (the default) prints with the clevis plane on the
  bed, as proposed above, so layers run along the prongs. It adds a 0.6 mm flat on the disc
  rim at 90° to the clevis as a bed face, which makes the disc 30.1 across that one
  direction (measure the OD across the flat's perpendicular). `--set orientation=flat`
  prints ring down instead, with a teardrop pivot hole and a 0.4 elephant's-foot chamfer on
  the ring; use it if the side print's ring comes out too far from round.

### Accepted check warnings
- **Side (default): bed contact and overhangs.** The disc stands on its rim with 36 mm² on
  the bed at 5.0× height-to-base, and the outer prong's underside sits about 6 mm above
  the bed (16.8 % overhang area). Slice with tree supports and a brim. Strength across the
  prong roots is worth the support scars, since that is where the original broke.
- **Flat: overhangs.** The back face around the ring, 1 mm above the bed, overhangs 4 mm
  all round, and the sunken surface is a short bridge (z 1.0 to 1.5). Use supports on the
  bed face, or accept a rougher back face.

## Revision history
| Rev | Change | Why |
|---|---|---|
| 0 | Schematic and requirements from photos | Start of redesign; nothing printed yet |
| 1 | First model: disc with a sloped front face, raised keyed back ring with a sunken centre, photo-traced arm, 3-prong clevis with root fillets, printed on its side in PETG (strong) | Build out the brief; nothing printed yet |
