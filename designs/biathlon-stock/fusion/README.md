# biathlon-stock: fit record → Fusion 360 parametric model

Design doc for driving the stock's Fusion 360 model entirely from User Parameters that
are loaded from the fit app's JSON export. Status: proposal plus a working parameter
loader (tested outside Fusion; not yet run inside Fusion, see "Verified so far").

## Recommendation in one paragraph
Load parameters with a **Fusion Python script** (`fusion_load_params.py`) that imports a
stdlib-only core (`stock_params.py`). The same script runs from Fusion's Scripts and
Add-Ins dialog or through the **Autodesk Fusion MCP server** that is already configured in
`.mcp.json`, so the MCP is a way to run the loader, not a separate route. Raw measurements
become `m_*` parameters and the CAD parameters become **Fusion expressions** of them
(`lop = m_AA`, `hook_drop = m_AF - (m_AC + m_AD / 2)`), so a re-measure flows through the
model without re-running anything. Build **one design file** with a skeleton component and three
body components that all read the same design-wide User Parameters. Handle handedness with **signed
lateral offsets** (`face_side = ±1`) instead of a mirror feature. Enforce IBU limits with
**`chk_*` margin parameters plus a geometric check script**. Limits are **flagged, never clamped**, in both
models (Darren, 2026-11-23). **The build123d model and the Fusion model run in parallel**, and neither
replaces the other (Darren, 2026-11-23). Both read the same parameters: `stock_params.py` resolves the
fit JSON once, then hands Fusion its expressions and hands `part.py` the evaluated numbers.

```
biathlon-fit-pwa  ──export──▶  fit-<name>-<date>.json  (schema biathlon-stock-fit 1.x)
                                         │
                         stock_params.py │ validate, map, evaluate, pre-check IBU (flag only)
                                         ▼
                 ordered rows: name · unit · expression · value · comment
                    │                                              │
  fusion_load_params.py (Scripts dialog or MCP)        part_params() / params_from_fit()
                    ▼                                              ▼
  Fusion User Parameters (expressions)              part.py PARAMS overrides (numbers)
  skeleton ─▶ rear_stock · main_body · forestock    build(p) ─▶ rear · main · fore
  check script (geometry)                           ibu_checks(p) + printloop report
                    └──────────── compared by the parity check (§7) ───────────┘
```

## 1. Loading the parameters: options compared

| Option | What it is | Verdict |
|---|---|---|
| **A. Fusion script / add-in** | `fusion_load_params.py`: reads the JSON, creates the missing parameters, then sets every expression in dependency order. Idempotent, never deletes, and skips any parameter whose comment starts with `[manual]`. | **Recommended.** It has full control, validates the record, and can be re-run after every new measurement. Later it can become an add-in with a "Load fit record" button. |
| **B. Autodesk Fusion MCP** | Autodesk's own MCP server, running inside Fusion at `http://127.0.0.1:27182/mcp` (already in `.mcp.json`). Its tools run a Python script in the active design (`fusion_mcp_execute`, featureType `script`, with a `readOnly` mode), search the API docs, take screenshots, undo and redo, and open or save documents. | **Use it as the transport for A.** It has no dedicated parameter tool, so parameters still go through a script. It only works while Fusion is open: during this work the call first timed out and then reported the server as unavailable. It is new, so plan on verifying each step with screenshots and read-back. |
| **C. CSV import** | Fusion's Change Parameters dialog has no file import. Autodesk's *ParameterIO* sample add-in imports and exports `Name,Unit,Expression,Value,Comment` CSV. `python3 stock_params.py fit.json --csv` writes that format. | **Fallback only.** It has no validation, no `[manual]` protection and no ordering guarantee, and it is an extra manual step. |

## 2. Naming and units

| Prefix / form | Meaning | Example |
|---|---|---|
| `m_<letter>` | One raw measurement from the sheet, created only when it has a value | `m_AA`, `m_W` (deg) |
| `r_<field>` | Rifle-detail numbers | `r_barrel_d_action`, `r_spare_mag_count`, `r_weight` (kg) |
| part.py names | Fit, stock, hardware and joint parameters, **same names as `part.py` PARAMS** and the fit app's `cad_parameters`; tuples are split into named scalars | `lop`, `block_height`, `front_tongue_width` |
| `face_side`, `bolt_dir` | Numeric handedness switches (±1) | see §4 |
| `fit_*`, `hole_shrink` | Clearances read from `printer/h2s.yaml` at load time | `fit_snug = 0.15 mm` |
| `ibu_*` | IBU limits | `ibu_depth_max = 140 mm` |
| derived (no prefix) | Shared helper expressions | `face_z`, `cast_z`, `hole_d_bolt`, `mag_holder_end` |
| `chk_*` | Margins that must stay ≥ 0 | `chk_depth_block = ibu_depth_max - block_height` |

Rules:
- The design's default units are mm, and every parameter carries a unit (`mm`, `deg`, `kg`) or
  is unitless (`""`) for counts and switches. Literals always carry their unit (`15 mm`).
- Expressions use only `+ - * /`, parentheses and `PI`. Avoid `^`, `min()` and `max()`:
  the argument separator is locale-dependent, and this subset is also valid Python, so
  `stock_params.py` can evaluate every value and pre-check IBU without Fusion.
- Comments are tagged: `[fit] …` means the loader owns the parameter, and `[manual] …` means
  Darren changed it by hand and the loader leaves it alone. To give a parameter back to the
  loader, delete the `[manual]` tag.
- A measurement or rifle field without a value gets no `m_*` or `r_*` parameter. Its dependants fall back to the
  part.py estimate as a literal and print a warning. Once the value exists, re-running the loader
  switches them back to the expression.

The full mapping, with every JSON field, its Fusion name, unit, expression, sample value and
IBU link, is in **[PARAMETERS.md](PARAMETERS.md)**. It is generated by `make_param_table.py` from the
registry, so it cannot drift.

## 3. Derived and expression parameters
| Parameter | Expression | Source |
|---|---|---|
| `lop` | `m_AA` | current LOP; check against D |
| `buttplate_length`, `buttplate_drop` | `m_AD`, `m_AC` | |
| `buttplate_curve_radius` | `(m_AD / 2) * (m_AD / 2) / (2 * m_E) + m_E / 2` | circle through the plate ends with sagitta E (falls back to the estimate when E < 1 mm) |
| `hook_drop` | `m_AF - (m_AC + m_AD / 2)` | plate bottom to hook contact |
| `hook_reach`, `cheek_to_eye`, `prone_hand_length` | `m_AE`, `m_P`, `m_J` | |
| `grip_circumference` | `PI * m_M` | target girth for the grip section |
| `handstop_position`, `block_position` | `m_AG`, `m_AJ` | |
| `harness_front_position`, `harness_rear_position` | `m_AH`, `-m_AI` | |
| `barrel_d`, `mag_holder_count` | `r_barrel_d_action`, `r_spare_mag_count` | |
| `comb_top` | `sight_line_above_bore - cheek_to_eye` | |
| `mag_holder_end` | `mag_holder_start + count * (spare_mag_t + 2 * fit_snug) + (count + 1) * wall` | |

The values match the fit app's own `cad_parameters` to 0.1 mm (this is tested). Rows the fit app marks
`design_input` (`comb_cast`, `hook_radius`, `grip_length`, `trigger_reach`,
`thumb_rest_height`, `block_height`) stay as estimates until a rule is agreed. Adding a rule
means giving the row an `expr` in `stock_params.py`.

## 4. Handedness without mirroring
A mirror feature would also mirror the hardware: the bolt notch (a right-bolt action in a
left-handed stock), any engraved text (it would read backwards), and later the harness clip
geometry. It also leaves a hidden source body in the timeline. Instead:

- **Two switches.** `face_side` is +1 for a left-handed stock (cheek on +Z, the shooter's right) and -1
  for right-handed. `bolt_dir` is ±1 from the rifle and independent of `face_side`.
- **Side profile is hand-free.** Every XY (side-view) sketch is symmetric about the mid-plane
  and never references a side.
- **Lateral features hang off signed planes.** `face_z = face_side * body_width / 2` and
  `away_z = -face_side * body_width / 2` are offset construction planes. Thumb rest, cheek and
  harness rail sketch on `face_z`, while palm swell and spare-mag holder sketch on `away_z`. Bosses
  extrude `face_side * depth` (outward on the face side) and pockets extrude `-face_side * depth`.
- **Cast** offsets the rear stock's mid-plane by `cast_z = -face_side * comb_cast` and extrudes symmetrically
  by `comb_width`.
- **Hardware** uses `bolt_z = bolt_dir * body_width / 2` and never `face_side`.
- **Text** on a face is sketched on the signed plane with "flip" settings that the loader can drive in
  a later script, because a sketch's reading direction follows the plane normal.
- **Fusion Configurations** (a table with Left and Right rows that sets `face_side` and suppresses features) is the
  escape hatch for any feature that is chiral rather than a sign flip. Use it only if one turns up, and
  check licence availability first.

Must verify in Fusion: negative offset-plane distances and negative extrude distances both
flip direction parametrically. If either does not, use the "To object" extent onto the signed plane instead.

## 5. Components, joints and shared parameters
One design file, `biathlon-stock.f3d`. User Parameters are design-wide, so every component
reads the same set.

- **Origin = the part.py shooting frame.** X runs forward along the bore with 0 at the trigger blade, Y is up with 0 on the bore,
  and Z is the shooter's right. The XY plane is the side profile.
- **`skeleton` component.** It holds no bodies, only the reference geometry:
  - master side-outline sketch, fully dimensioned by parameters (LOP, comb, butt, hook, wrist,
    forend, block, guard), with the bore axis and the sight line
  - split planes `rear_split` and `front_split`, offset from the YZ plane
  - marking-surface rectangle (`marking_start`, `marking_length`, `marking_height`), used by the checks
  - joint profile sketches: the tongue at nominal size, and the socket at `+ 2 * fit_snug` per dimension
- **`rear_stock`, `main_body`, `forestock`.** Each extrudes the shared outline, limited by "From
  object / To object" to its split planes, then adds its own features. Each gets one body, built in shooting
  position. Print orientation is applied at export, not in the model.
- **Joints.** The tongue belongs to the part that carries it (rear tongue on `rear_stock`, front tongue
  on `forestock`, as in r1). The socket in `main_body` is cut from the skeleton's socket sketch, so the
  clearance comes from `fit_snug`, not from an offset of the mating body. Bolt and cross-dowel holes
  use `hole_d_bolt` and `hole_d_dowel` at `cross_dowel_x`.
- **Hardware components.** M6 bolts, cross-dowels, the trigger guard and a magazine placeholder
  are placed by parameter-driven joints, so interference checks and the depth check see them.
- **Assembly.** Rigid as-built joints at the split faces keep the three parts in place. Physical
  properties (with material densities) give part masses for the weight check.
- **Export.** A small script exports each component to STEP and 3MF in print orientation under
  `out/` (next step, not in this PR).

## 6. IBU enforcement
Decided 2026-11-23: **flag only, never clamp**, in both models. A broken limit is reported and
the geometry is still built as specified, so the cause stays visible and is fixed at its source.
Fusion has three layers:
1. **Pre-flight in the loader.** `stock_params.py` evaluates every `chk_*` before anything is
   written to Fusion and prints the broken ones. The CLI exits 1 when any are broken.
2. **Live margins in Fusion.** The `chk_*` parameters recompute on every edit and are visible in Change
   Parameters. After loading, the script reads them back from Fusion and reports any value below zero. Fusion
   cannot refuse a value, which is why layer 3 exists.
3. **Geometric check script**, like ammo-tray's `check_brick_box.py`. It measures the real bodies,
   including hardware components:
   - lowest point below the bore ≤ 140 mm (MC 3.1.6.4 a)
   - rear-stock thickness in the comb zone ≤ 40 mm (b)
   - a planar face ≥ 40 mm high on both sides from 150 mm ahead of the trigger, with no hole, joint line or bolt head in it (l)
   - each part's bounding box fits the plate with 5 mm margins
   - assembled mass, including the action and barrel components, ≥ 3.5 kg (i)

In build123d, `part.py`'s `ibu_checks(p)` and the loader's `chk_*` pre-flight print the same
flags, and `build()` keeps building. Neither model may add `min()` or `max()` caps on a limited parameter.

Parameters that can break a rule are tagged in the `IBU` column of PARAMETERS.md.

## 7. build123d and Fusion in parallel
Decided 2026-11-23: both models are kept, and neither replaces the other.

**One parameter source.** `stock_params.py` is the only place where a fit-JSON field becomes a
parameter, a formula or a default. Each model consumes it differently:
| | Fusion | build123d (`part.py`) |
|---|---|---|
| Entry point | `fusion_load_params.py` | `params_from_fit(path, PARAMS)` → overrides |
| Form | Expressions (`lop = m_AA`), live in Fusion | Evaluated numbers, with tuples rebuilt in part.py's shapes (`front_tongue = (30, 28, 30, -34)`) |
| Handedness | `face_side`, `bolt_dir` = ±1 | `"handedness"`, `"bolt_side"` = `"left"` / `"right"` |
| Fits | `fit_*` parameters from `printer/h2s.yaml` | `printloop.fits` (same file) |
| IBU | `chk_*`, plus the geometric check script | `ibu_checks(p)`, plus the printloop report |

**Wiring part.py** (next step, a few lines in part.py, not in this PR, because part.py belongs to PR 3):
```python
import os, sys
sys.path.insert(0, str(Path(__file__).parent / "fusion"))
from stock_params import params_from_fit
fit = os.environ.get("FIT_JSON")
P = {**PARAMS, **(params_from_fit(fit, PARAMS) if fit else {})}
```
Then `FIT_JSON=… printloop build biathlon-stock`. `printloop build --set` keeps working for one-off tweaks.

**Keeping the two in step:**
- *Defaults.* `test_defaults_match_part_py` fails if a registry estimate differs from part.py PARAMS.
  A change to a default is made in both places in the same commit, or part.py reads its defaults
  from the registry.
- *Coverage.* `test_part_params_feed_part_py` fails if part.py has a PARAMS key that the loader does
  not supply. A new part.py parameter therefore needs a registry row (and so a Fusion parameter).
- *Geometry parity.* Both models use the same frame. The rule they share is that the trigger blade is the
  origin, the bore is the X axis, and +Z is the shooter's right. A parity script (next step) builds both from
  the same fit JSON and compares each part's bounding box, volume and key points: the lowest point below
  the bore, the comb top, the split faces and the hole centres. It flags differences over 0.5 mm. Fusion's
  STEP export is read into build123d for the comparison.
- *Roles.* build123d stays the scripted, CI-checkable model that runs the printloop printability report.
  Fusion is the interactive model for shaping (grip and cheek surfaces, fillets) and visual review.
  Shape work done in Fusion that changes a dimension goes back into the registry as a parameter, never
  as a hand-typed number.

**Cost of the choice.** Every geometric feature is modelled twice. Expect drift on free-form
surfaces such as grip, cheek and butt curves, where Fusion will run ahead of build123d. The
parity check tolerates that only for parts that are fit-tested in Fusion first, and the brief says which.

## 8. Gaps found between the fit app and part.py
- `comb_height_above_bore` (from AB) is not a part.py parameter, because part.py derives the comb from
  `sight_line_above_bore - cheek_to_eye`. It is kept as `ref_comb_height_current` for comparison.
- `grip_circumference` (π·M) has no consumer in part.py, which uses depth, width and chamfer. The Fusion grip
  section should be driven by it.
- `harness_front_position` and `harness_rear_position` (AH, AI) are not used by part.py, which has rail-insert placeholders
  and no rear connector. They are loaded and will drive the connectors once the clip is known.
- The fit app's `document.cad_target.parameter_table` says `part.py PARAMS`. It should point at
  `designs/biathlon-stock/fusion/stock_params.py`, since that now feeds both models.
- With the sample record, `chk_holder_hand` is −0.2 mm. This is the same spare-mag-holder and prone-hand overlap that r1 already flagged.

## 9. Verified so far
- `stock_params.py` against `samples/fit-sample.json`: 164 parameters, all expressions evaluate,
  values match the fit app, and `part_params()` supplies all 71 part.py PARAMS keys.
  Tests: `uv run --with pytest --no-project python -m pytest designs/biathlon-stock/fusion -q` (10 pass).
- The sample is generated with the fit app's own `buildExport` from its test fixture. The values are
  typical-range midpoints, not Darren's.
- **Run inside Fusion (2706.1, through the Autodesk Fusion MCP) on 2026-11-23.** These were
  confirmed against Darren's sample record:
  - The loader created 162 parameters, and every expression resolves. A second run reports
    0 changed and skips the 12 `[manual]` r2 overrides.
  - `fusion_build_demo.py` built the skeleton and three components, each with one valid body and
    a healthy timeline. Every sketch point is placed by driving dimensions whose expressions are
    User Parameter expressions.
  - **§4 works as designed.** With `face_side = -1` and `m_AA = 345 mm`, the model rebuilt with no
    errors. The mag slots and thumb rest moved to the other side, the bolt notch stayed on the bolt side,
    and the rear stock grew by 25 mm. Negative offset-plane distances and negative extrude distances
    both flip direction.
  - In the demo, `chk_holder_hand` and `chk_holder_joint` still use r1's upright-holder rules. They
    need r2's flush-slot rules (from PR 3's part.py).
  - **Slim skeleton butt** (Darren 2026-11-23, composite of `reference-images/butt-section-designs/`,
    mainly the BIONIC frame (#01), the Bear single-window butt (#13) and the printed CZ457 and Patronus rear
    ends (#22, #24)). The comb beam (cheek, `comb_width`) and the butt-plate post (`plate_thickness`
    behind the concave face) keep their full width. Between them the frame thins to `frame_width` and
    is opened by two windows, split by a `frame_rib` and bounded by a lower strut `frame_web` wide that runs
    parallel to the underside. All of it is driven by derived parameters (`rs_*`, `butt_sagitta`). The rear
    stock went from 1000 to 502 cm³.
  - **Bolted tongue joints** (Darren 2026-11-23) replace the cross-dowels and lateral bolts. Each joint
    is a tongue that overlaps into a socket in the main body (`*_tongue_length` is the overlap), locked by two
    M6 bolts running along the stock. The nuts sit in the main body in hex slots sized to the flats
    (`nut_af + 2 * fit_snug`), so a nut cannot turn and needs no tool. The slots open upward into the action
    inlet (rear) or the barrel channel (front), so they are hidden under the action and barrel.
    - Rear joint: bolt heads seat on the front wall of the butt's front window, where they stay exposed for a
      hex key. The shank runs through the butt, then the tongue, then `rj_engage` of main-body material,
      then the nut. The bolt is 98 mm under the head (M6 × 100). The front half of the butt frame is kept
      full width so the bolt holes have walls.
    - Front joint: bolt heads sit in a pocket under the forestock that is open at the bottom. The
      pocket has ≥ 2 mm under the mag slots (`chk_fj_pocket_slots`), sits behind the hand stop, and is
      outside the marking surface (150–200 mm, on the main body). The bolt is 57 mm (M6 × 55 or 60).
    - Not yet done: teardrop roofs on the horizontal bolt holes, bolt-length rounding to stock sizes, and covers
      (not needed while the slots open under the action and barrel).
  - **Main body closer to the Anschütz BIONIC** (Darren 2026-11-24: too square, too much material at
    the magazine). The solid shelf under the action is gone. Now the forend is a constant `forend_depth` beam,
    the magazine well opens through its bottom, and a small trigger-guard loop (`guard_front_x`, `guard_bar`,
    `guard_rake`, `guard_bottom`) leaves open space in front of the grip. The standing block is a separate
    palm rest hanging under the forend (`block_position`, `block_top_len`, `block_length`, `block_height`)
    with a window through it. Side edges of every part are rounded (`body_round`; `chk_mark_round`
    keeps the marking surface ≥ 40 mm flat). Main body went from 1399 to 903 cm³.
  - Demo shortcuts: no chamfers or grip rounding, no tie rods, no harness inserts, no mag window or
    finger scallops, and no teardrop holes.

## 10. Hybrid restyle (2026-11-24)
Darren picked the "Hybrid" style: flowing rigid surfaces with straight-edged geometric windows. `fusion_build_demo.py`
now builds it, still entirely from User Parameters. Review images come from `fusion_render_views.py`.

- **Flowing surfaces.** Each outline corner is rounded by its own radius parameter (`comb_front_r`, `wrist_heel_r`,
  `tip_round`, `belly_sweep_r`). The forend has a faceted belly (`belly_w`, `belly_h`) and every side edge is rounded
  (`body_round`). Rounds that Fusion cannot build are reported under "skipped rounds", never hidden.
- **Drop belly.** The underside is `forend_depth` (62 mm) under the action and the front joint, then rises to
  `forend_fore_depth` (50 mm) along the joint's head pocket, so the hand's forend is slimmer.
- **Geometric windows.** The butt has three truss windows between ribs that lean by `rib_lean`, near square to the lower
  strut. The slim frame meets the comb beam in a cove (`slim_cove`).
- **Standing block.** It is now an extension of the trigger-guard base: it hangs under the guard bar, from `finger_clear`
  ahead of the grip to `guard_front_x`, which is behind the magazine well (`chk_block_mag`), so the magazine drops free.
  `block_position` and `block_length` are derived; `m_AJ` is reference only. `block_height` stays the IBU-limited input.
- **Webs.** `min_wall` (6 mm) is now held above the mag slots (`chk_slot_channel`), below them (`chk_fj_pocket_slots`,
  was 3.7 mm) and under the front tongue (`chk_fj_tongue_floor`).
- **TPU inserts.** Surfaces shaped only by the athlete's body are separate TPU parts on rigid cores:
  Rule (Darren, 2026-11-24): every TPU part mounts on a rigid feature of the structural part.
  - `tpu_grip`: a sleeve over a rounded rigid core. It slides on from below, is keyed by the core and by a rigid front
    strip above the guard bar (`spine_d`), and is locked by `grip_cap` with one M5 screw into a heat-set insert. Its girth
    comes from the measurement: `grip_round` is solved so the section's girth equals `grip_circumference` (PI * M).
  - `tpu_prone_pad`: a `pad_t` skin over the belly from `pad_x0` (hand-stop position minus J) to the hand stop. It sits in
    a recess, wraps `pad_wrap` up each side and snaps in with a dovetail keel.
- **IBU flags.** `block_height`, `guard_bottom`, `forend_depth` and `handstop_height` are limited by MC 3.1.6.4 a (140 mm);
  `chk_depth_grip` applies the same limit to the grip bottom in case a controller reads the rule strictly. `body_round`
  and `belly_h` reduce the flat marking surface (`chk_mark_round`). The block no longer sits in the marking zone.
- **Open points.** The joint fasteners cannot be inserted as bolts (the butt window and the head pocket are shorter than
  the bolts), so the plan is M6 studs threaded into the captive nuts with nuts on the outer ends. `chk_holder_joint`,
  `chk_holder_hand` and `chk_rail_handstop` still use r1's upright-holder rules.

### Lower unit: grip, trigger guard and standing block as one insert (Darren, 2026-11-24)
- **One component.** `lower_unit` holds the rigid grip core and front spine, the trigger guard and the standing block
  frame as a single body. Like the action cradle, it plugs into the stock: a plate (`plug_w` × `plug_h`, from `plug_x0`
  to the guard's front leg), the leg's top and the grip's top push up into a matching pocket that is cut from the main
  body (`lower_pocket`). It is joined to the main body before printing (`FUSE_BLOCK = True`). No fasteners.
- **Guard.** 32 mm wide (`guard_width`), the same as the block. The opening is 24 mm high (`guard_open_h`) with rounded
  corners (`guard_corner_r`) and a large radius into the grip front (`guard_rear_r`); its length (about 62 mm) cannot go
  below the measured 60 mm trigger opening above it. Toward the grip the rail narrows (`rail_taper_len`,
  `rail_taper_w`), so it runs into the grip's rounded front without shoulders.
- **One flowing outline (Darren, 2026-11-24).** Guard and block are one rigid profile and every transition in it is a
  true tangent arc: the guard's front leg sweeps forward into the top of the block (`guard_gusset_r`), the top rolls
  over the front corner (`block_top_r`, wrapped `nose_cap` round it), and the rail's underside rolls down into the
  block's vertical rear face (`guard_blend_r`; `blk_rake` is 0). The leg carries load into the block again.
  `chk_gusset_bolt` keeps the sweep clear of the rear mounting bolt.
- **Block frame.** Under that outline the rigid part is a 5 mm skin along the top of the block (`collar_h`, thicker
  than `guard_round` so its edges can be rounded), a heel at the rear (`heel_len`) and a dovetail rib under the skin
  (`core_neck` narrower per side at the top, `cover_t` inside the outer shape) with a cross groove (`detent_w`,
  `detent_d`). The hole for the rear mounting bolt goes through the rib.
- **Block cover.** `tpu_block_cover` is its own part, customised and printed per athlete. It fits whatever the rigid
  shape leaves: bottom, both sides and the front, up to the underside of the skin. It slides on from the front until
  it meets the heel, the dovetail stops it pulling off downward, and a rib inside it snaps into the groove (the TPU
  rule). It is closed at the front and underneath, so it hides the bolt hole. Heel and cover are cut from the same
  rounded shape (`block_round = guard_round`), so they are flush. This replaces the full top-and-bottom sleeve.
  The block is `block_drop` (28 mm) deep, starts `blk_tuck` behind the front of the trigger opening and stops 2 mm short
  of the magazine (`act_rel_zone` pending measurement), so the magazine drops free (`chk_block_mag`).
- **IBU.** The assembled block counts toward MC 3.1.6.4 a: `chk_depth_block` and the build report's lowest point of
  `standing_block` both check it. Any replacement block must keep `block_height` at or under 140 mm.

### Sling seat, wrist and guard rounds (2026-11-24)
- **Sling seat.** The hand stop's sling slot is replaced by a flat pocket under the stop for the sling's end tab
  (Darren's Biatar sling: 40 mm wide, 5.5 mm eyelet, flat, round tip). The pocket is `sling_tab_w + 1 mm` wide and
  `sling_seat_d` deep, ends in a semicircle (`sling_seat_r`) for the tip, and is open to the rear. A heat-set insert at
  `sling_hole_x` takes an M5 thumb screw through the eyelet. `sling_hole_inset` (tip to eyelet) is 17 mm, confirmed by Darren.
- **Wrist.** `wrist_under_y` is derived so the rear joint socket keeps `min_wall` below it (an earlier round let the socket
  break through the underside). A facet (`wrist_facet_w`, `wrist_facet_h`) narrows the underside to the grip width, and
  `grip_offset` is 0. The grip bottom now sits exactly on the 140 mm line (`chk_depth_grip` = 0).
- **Rounds.** The guard is rounded as its own body and then joined, and the forestock hull is rounded before the hand
  stop is joined. The build reports no skipped rounds.

### No-snag rule (Darren, 2026-11-24)
Nothing on the stock may catch clothing, so every fastener head is recessed and each has a margin that must stay >= 0:
| Fastener | How it is recessed | Check |
|---|---|---|
| Action bolts (2) | counterbores `act_cbore` deep in the underside | `chk_head_action` |
| Rear joint (2) | counterbores `joint_cbore` deep in the butt window's front wall | `chk_head_rear_joint` |
| Front joint (2) | counterbores `joint_cbore` deep in the wall of the pocket under the forestock | `chk_head_front_joint` |
| Grip cap screw | low-head M5 in a `cap_cbore` counterbore; the cap is 7 mm thick to take it | `chk_head_cap` |
| Sling bolt | low-head M5 in a `clamp_cbore` counterbore in the sling clamp plate | `chk_head_sling` |

**Sling clamp (Darren, 2026-11-24).** `sling_clamp` is a separate plate, `clamp_t` thick, under the hand stop. The tab
(3.5 mm thick, measured) lies in a seat exactly its thickness deep, and the plate closes flat on it. One M5 bolt goes up
through the plate and the tab's eyelet into a captive hex nut that slides into a slot in the side of the hand stop
(`sling_nut_y`, `m5_nut_af`, `m5_nut_m`). The plate carries the hand stop's shape on down, with rounded corners and edges.

Both joints' counterbores are `joint_cbore_d` (13.5 mm) wide, room for an M6 nut or head and a thin-wall socket.

**Hand stop rear.** The rear face of the hand stop and of the clamp plate is rounded in plan (`hs_rear_r`), because the
web between thumb and forefinger rests against it in prone. A flat remains in the middle for the sling tab to leave
through (`chk_hs_rear`).

**Joint nut slots.** They are open right up through the receiver bed (rear) and the barrel channel wall (front), so a
nut drops straight in; the action and barrel then cover them. Each slot is `nut_slot_af` (10.3 mm) across the flats, so the nut cannot turn, and `nut_slot_len`
(5.5 mm) along the bolt, a slide fit so an M6 nut (10 mm across flats, 5 mm thick) drops down it edge-on.

### Balance at the standing block (Darren, 2026-11-24)
Goal: standing, the block is the pivot, so the assembled rifle should balance where the centre of the support-hand thumb
sits on it. `fusion_balance.py` (read-only) takes each printed body's volume and centroid from the model, applies a
density and solid fraction per part, adds the non-printed masses (barrelled action, sights, magazines, fasteners,
ballast) and reports the centre of gravity against `BALANCE_POINT` (`block_position` until the thumb point is measured).
First run, all masses placeholders: 3.79 kg, centre of gravity 121 mm ahead of the trigger, 101 mm ahead of the block's
middle and 35 mm ahead of its front end. The barrelled action (1880 g, own balance point guessed) decides the result.

### Spare-magazine slots (Darren, 2026-11-24)
- **Lead-in.** The mouth of every slot is rounded (`mag_lead_r`, 2.5 mm) so a magazine seats easily.
Each of the four holder slots is 36 × 9.5 mm (`mag_slot_len`, `mag_slot_h`, measured) with rounded corners
(`mag_slot_r`, placeholder), spaced `mag_holder_wall` apart. The slots are 42 mm deep (`mag_slot_depth`, measured), which leaves 8 mm of wall on
the face side (`chk_slot_wall`); the harness rail inserts moved above the slots (`harness_rail_y`, `chk_rail_slots`).

### One design, not three (Darren, 2026-11-24)
The butt, main body and forestock are separate prints, but they should read as one stock:
- **Rear joint.** The butt is built at `body_width` and narrows to `comb_width` over `butt_flare_len`, so both parts are
  the same width at the joint. The cheek stays at `comb_width` (IBU MC 3.1.6.4 b).
- **One edge radius.** Every rigid part uses `body_round` up to both joints; the larger wrist round is gone.
- **One line.** The butt windows start at the height of the top of the spare-mag slots (`comb_beam_h` is derived from
  `mag_holder_top`). Shallow flutes (`flute_d`) carry the slot line along both sides of the main body (`flute_x0` to
  `flute_x1`) and mirror the slots on the forestock's face side. The flutes stop short of the IBU marking surface
  (`chk_flute_mark`).
- **One colour.** All rigid printed parts share one appearance; TPU parts and the two small ASA parts differ.
Fixed features did not move: the action cradle, bolt positions, magazine well, trigger pocket, joints and marking surface.

### What is fitted to the athlete, and what is locked (Darren, 2026-11-24)
Rifles are fitted by stock length and cheek height; everything that meets the action and barrel is a fixed dimension.
So only these follow the fit record (`USER_FITTED` in `fusion_build_demo.py`):

| Fitted item | Parameter | From | Range the layout takes | Check |
|---|---|---|---|---|
| Stock length | `lop` | AA | 215 mm and up; built at 256 and 368 mm | `chk_lop_min` |
| Cheek height | `cheek_to_eye` (sets `comb_top`) | P | built at 24 and 36 mm | `chk_cheek` |
| Hand stop position | `handstop_position` | AG | 307 to 365 mm from the trigger | `chk_handstop_min`, `chk_handstop_max` |
| Front harness connector | `harness_front_position` | AH | 237 to 429 mm | `chk_harness_front_lo`, `chk_harness_front_hi` |
| Rear harness connector | `harness_rear_position` | AI | from 35 mm ahead of the butt plate to the butt's flare | `chk_harness_rear_lo`, `chk_harness_rear_hi` |
| Spare-mag side | `mag_side` (default: away from the face) | T | left or right; same place along the forestock | |

Everything else is locked: the butt plate, hook, grip, guard, standing block frame, forestock length, magazine slots,
joints and the whole action cradle. The loader would drive some of these from body measurements; the build script pins
them with `[manual]` rows at the top of `DEMO_PARAMS`. The TPU covers remain the place for per-athlete shape.

- **Hand stop.** The forestock is a fixed length; the hand stop slides along it and the prone pad always runs from just
  ahead of the front joint to the hand stop.
- **Harness connectors.** Two M5 heat-set inserts each (`harness_pitch` apart, placeholder), at the fitted positions: the
  front pair on the forestock on the side opposite the mag slots, the rear pair in the butt's comb beam.

### Bolt travel and thumb room behind the action (Darren, 2026-11-24)
- The Fortner bolt travels about 45 mm back past the rear of the action (`act_bolt_travel`, 43.16 mm measured), and
  the thumb needs room behind it to push the bolt forward again (`bolt_thumb_room`, 22 mm placeholder).
- From the action's rear back to `bolt_clear_x` the stock is a flat at `wrist_top`, 2 mm below the receiver's
  underside, over the full width. The comb rises behind it (`comb_rise`), so `comb_length` is derived from it. The
  ramp up to the stock top beside the action now starts at the action's rear (`wrist_step`).
- `chk_comb_flat` keeps at least 90 mm of comb for the cheek; `chk_wrist_socket` keeps 5 mm over the rear joint socket.
- The rear joint studs are longer for it (150 mm, see PARTS.md), because their heads sit in the butt's front window.
- Rear sight above the cheek rest: 47.2 mm measured, so P = 47 mm. With the current comb 20 mm above the bore (AB),
  `sight_line_above_bore` becomes 67 mm and the comb stays where it was. Pending: bore centre to aperture centre.

### Organic butt (Darren, 2026-11-24)
- **Outline in curves.** The comb falls to the heel over `heel_sweep` with a large round (`heel_sweep_r`), the heel
  itself is rounded, the comb turns down to the bolt flat in an S-curve (`comb_front_r`), and the underside sweeps
  into the wrist (`wrist_heel_r`) and into the hook (`hook_sweep_r`).
- **Two windows, one rib.** The rear window's back edge follows the butt plate's curve (`rs_post_top_x`,
  `rs_post_low_x`), so the plate post is one even band `plate_thickness` deep. The front window is a triangle. Each
  corner is a large round (`win_round`; sharp-angled corners get less).
- **Rounded struts.** The slim frame and its coved pockets are gone: the butt is one thickness (`comb_width`), and
  both window rims are rounded (`strut_round`), so the rib, lower strut and plate post are rounded bars that run
  into the plate without a step. `frame_width` and `slim_cove` no longer drive geometry. About 45 cm³ heavier.

### Harness module: a built-in mini-rail (Darren, 2026-11-24)
- **Not a rail, not a through-hole, not an added part.** The full-length aluminium rail (r33) and the sleeve-nut
  through-hole (r35) were both rejected. The connector is a short T-slot printed into the forestock's side, opposite
  the spare mags, at `harness_front_position` from the fit record (measurement AH).
- **Layout.** Lengthwise, centred top to bottom on the side of the forestock (`mini_y`). An upright slot open at
  the top edge was tried in r38 and dropped.
- **How it works.** The harness's own sliding block drops into an open mouth (`mini_entry_len`), slides back under
  two lips (`mini_lip_t` thick, the track is `mini_track_w` x `mini_track_h`), and its neck meets the rounded end
  of the slot exactly at the measured position. The harness's nut then clamps on the lips.
- **Sizes are PENDING MEASUREMENT** of the harness block: `mini_block_w`, `mini_block_len`, `mini_block_t`,
  `mini_neck_w`. `chk_mini_lip` keeps at least 1.5 mm of lip over each side of the block.
- **Strength.** The rifle hangs on the two printed lips. Print the forestock so the layers do not run parallel to
  the lips' underside, and treat the lip thickness as the parameter to raise if the block's neck allows.
- **Fitted range.** `chk_harness_front_lo` and `chk_harness_front_hi`: the module sits ahead of the prone pad and
  its mouth ends behind the nose. Centred, it sits at the height of the spare-mag slots, so it must start ahead of
  them: 400 to 407 mm ahead of the trigger. Darren's is 400.
- **Rear connector.** Still two heat-set inserts on the comb beam, pending how the rear of the harness attaches.

### Parameter tolerance (checked 2026-11-24)
Ten driving measurements (AA, AC, AD, AE, AF, E, P, AG, J, M) were scaled together and one at a time.
Standing height (A) drives nothing by itself; the stock follows the rifle-fit measurements.

| Scale (shooter height) | Rebuild from the script | Layout checks that go negative |
|---|---|---|
| 115 % (2.05 m) | builds, all bodies valid, no skipped rounds | none new |
| 100 % (1.78 m) | builds | none new |
| 90 % (1.60 m) | builds | `chk_handstop_min`, `chk_pad_pocket` |
| 80 % (1.42 m) | builds | those two and `chk_slots_handstop` |
| 67 % (1.20 m) | fails: the forestock is too short for the row of four slots | |

- **Rebuild, do not live-edit.** Changing a measurement in Change Parameters breaks recorded rounds from about 5 %,
  because a recorded fillet cannot re-pick its edges. Re-running `fusion_build_demo.py` picks them afresh.
- **Fixed by this check.** `comb_length`, `grip_depth`, `grip_width` and `forend_tip` were fixed numbers, so a 10 % smaller
  shooter broke the outline. They are now derived from the measurements.
- **The real limit is the front joint.** The hand stop and prone pad must sit ahead of the joint's head pocket
  (`chk_handstop_min`), which needs AG of about 347 mm or more with J = 80. Smaller shooters need the front joint or the
  spare-mag row laid out differently; the butt and grip already scale.

## 11. Action cradle (2026-11-24)
Darren's requirement: the stock must take a real barrelled action on its mounting screws, and a different action must
not mean redoing the design. Everything that depends on the action now lives in one component, `action_cradle`.

- **Selection.** `stock_params.ACTIONS` holds one preset per action type. `pick_action()` reads `rifle.action_type`,
  `action_type_other` or `make_model` from the fit record, and the preset fills the `act_*` parameters and the action's
  hardware parameters (`action_rear`, `action_front`, `action_width`, `mag_well_*`). `action_type` is the preset's code
  (1 = Anschütz 1827 F / 1825 Fortner, 2 = Izhmash BI-7-4).
- **Interface.** The main body has a pocket of fixed section, `cradle_w` wide and down to `cradle_y`, from `action_rear`
  to `action_front`. The cradle fills it exactly and is fused to the main body for printing (`FUSE_ACTION = True` in
  `fusion_build_demo.py`; the default keeps it apart so it can be reviewed).
- **Family 1 cradle** (round receiver), laid out from Darren's own 1827 F stock, muzzle to butt: half-round barrel
  channel (`barrel_r`), the step at `action_front`, half-round receiver bed (`act_bed_w`), front mounting bolt
  (`act_screw_front_x`), locating pin (`act_pin_x`), magazine well, seat for the steel cross key (`act_key_*`), rear
  mounting bolt (`act_screw_rear_x`) and a deeper rectangular trigger pocket (`act_trig_*`). The two bolts straddle the
  magazine well. Both go in from below through stepped holes: a bore for an aluminium bedding
  pillar (10 × 1.5 mm tube, `act_pillar_d`, `act_pillar_id`, length `act_pillar_len`) from the bed down to the head seat,
  opened to head size only for the bottom `act_cbore`, so the bolt clamps metal to metal; the rear one sits ahead of the guard leg and the
  standing block, so a key reaches it (`chk_pillar_guard`).
- **Measured (2026-11-24):** bed width 30.19 mm, magazine well width 16.00 mm, action bolt holes 6.84 mm (two bolts),
  trigger pocket width 26.2 mm, and the trigger opening inside it, 20 × 60 mm. The opening goes through to the guard and
  ends at the rear of the guard opening by the grip (`chk_trig_rear`). Other positions, lengths and depths are placeholders.
- **Depths (measured 2026-11-24).** Stock top edge to the trigger pocket floor is 43 mm and bed bottom to that floor is
  31 mm (`act_trig_drop`), so the bed bottom is 12 mm below the stock top (`act_wall_h`). From these, `stock_top_y` puts
  the stock's top edge 3.1 mm below the bore, and `act_trig_depth` puts the pocket floor 46.1 mm below it. The pocket's
  front step is 12.5 mm ahead of the 20 × 60 opening (as read from the third photo).
- **Consequence for the body.** The real pocket is deeper than the earlier underside, so the guard opening's ceiling is
  now level with the wrist underside (`finger_hole_y1 = wrist_under_y`, 55 mm below the bore), which leaves 8.9 mm of
  floor under the pocket (`chk_trig_floor`). `guard_bottom` is derived from a 28 mm opening (`guard_open_h`) and is 93 mm.
- **Underside ramp.** Ahead of the guard opening the underside runs down a ramp (`belly_ramp`) from the wrist level to
  the belly, instead of a step, and the wrist underside edges carry a large round (`wrist_round`) that narrows the body
  to the grip. With the step gone every edge rounds; the build reports no skipped rounds.
- **Rounded corners.** The vertical corners of the trigger pocket, the trigger opening and the magazine well are rounded
  by `pocket_r` (5 mm, estimated from photos).
- **Flared magazine entry.** The bottom of the magazine well has a 45 degree funnel, `mag_flare` wide, clear of both bolt
  counterbores (`chk_flare_bolts`) and inside the flat of the belly (`chk_flare_belly`).
- **Magazine well (measured).** Seen from the underside it is one slot, 60 mm long and 15 mm wide, that takes the
  magazine and, in its rear part, the release lever. There is no separate scoop (`act_rel_len` = 0 for this action).
  The front mounting bolt sits ahead of the slot and the rear one behind it. Their positions
  (`act_screw_front_x`, `act_screw_rear_x`) must match the action's threaded holes exactly, so they are explicit
  parameters pending measurement and are never derived from the well.
- **Fortner bolt-handle notch.** A long notch in the bolt-side wall (`bolt_notch_x`, `bolt_notch_length`,
  `bolt_notch_depth`) with a deeper step at its rear for the lever (`act_bolt_step_len`, `act_bolt_step_depth`). It is cut
  on the side given by `bolt_dir`, which comes from the rifle's bolt side in the fit record and is not a mirror of the
  shooter's handedness. All sizes are placeholders.
- **Scan to come.** Darren will supply a 3D scan of the inlet; it then becomes the primary source for the cradle.
- **Adding an action.** Add a preset. Write a new cradle builder only if the receiver is not a round one on two vertical screws.
- **Still needed**, all from the stock that fits the action: see the list in the project thread (positions from the
  receiver's front step, pocket depths, cross key size, screw head size, barrel channel diameter).

## Files
| File | Purpose |
|---|---|
| `stock_params.py` | Registry and resolver (stdlib only), the parameter source for both models. CLI preview, `--csv` for ParameterIO, `params_from_fit()` for part.py |
| `fusion_load_params.py` | Fusion script: create or update User Parameters from a fit record |
| `fusion_build_demo.py` | Fusion script: skeleton, the three rigid components and the TPU inserts, fully parameter-driven |
| `fusion_render_views.py` | Fusion script: saves the review images (sides, top, bottom, isos, exploded) |
| `fusion_balance.py` | Fusion script (read-only): mass and centre of gravity of the assembled rifle against the standing block |
| `make_param_table.py` | Regenerates `PARAMETERS.md` |
| `PARAMETERS.md` | JSON field → Fusion name, unit, expression |
| `test_stock_params.py` | Tests (no Fusion needed) |
| `samples/fit-sample.json` | Sample export from biathlon-fit-pwa 1.0.0 (placeholder values) |

## Running it
```bash
python3 designs/biathlon-stock/fusion/stock_params.py designs/biathlon-stock/fusion/samples/fit-sample.json
```
In Fusion: create a new design, go to Utilities › Scripts and Add-Ins, click **+**, choose this folder, run
`fusion_load_params`, and pick the JSON. Through the MCP: send `fusion_load_params.py` with
`FIT_JSON` set to the absolute path of the record.
