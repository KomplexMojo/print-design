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
**`chk_*` margin parameters plus a geometric check script**, and flag rather than clamp. From r2 on, **Fusion
becomes the geometry source** and `stock_params.py` becomes the single parameter source.
`part.py` stays frozen at r1 as a reference, which is the same route ammo-tray took.

```
biathlon-fit-pwa  ──export──▶  fit-<name>-<date>.json  (schema biathlon-stock-fit 1.x)
                                         │
                         stock_params.py │ validate, map, evaluate, pre-check IBU
                                         ▼
                 ordered rows: name · unit · expression · comment
                                         │
     fusion_load_params.py  (Scripts dialog, or MCP fusion_mcp_execute "script")
                                         ▼
     Fusion User Parameters ─▶ skeleton sketches ─▶ rear_stock · main_body · forestock
                                         │
                       check script (geometry)  ─▶  STEP / 3MF per component ─▶ slice
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
Three layers. None of them clamps silently, because the project rule is to flag.
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

Parameters that can break a rule are tagged in the `IBU` column of PARAMETERS.md.

## 7. Coexistence with build123d
| Option | Pros | Cons |
|---|---|---|
| **Fusion replaces part.py from r2** (recommended) | One geometry model. Darren works in Fusion. `stock_params.py` is the single parameter source for Fusion, the fit app mapping and the checks. | printloop's automatic checks don't run on Fusion bodies, so the geometric check script covers them (ammo-tray precedent). |
| Keep both, each reading `stock_params.py` | Keeps the printloop checks and CI | Two geometry models to keep equal, which will drift |
| build123d stays primary and Fusion only gets STEP | No new work | Not parametric in Fusion, so it fails the goal |

In every option `stock_params.py` stays importable from `part.py`. The test
`test_defaults_match_part_py` keeps the registry estimates equal to r1's PARAMS until part.py is retired.

## 8. Gaps found between the fit app and part.py
- `comb_height_above_bore` (from AB) is not a part.py parameter, because part.py derives the comb from
  `sight_line_above_bore - cheek_to_eye`. It is kept as `ref_comb_height_current` for comparison.
- `grip_circumference` (π·M) has no consumer in part.py, which uses depth, width and chamfer. The Fusion grip
  section should be driven by it.
- `harness_front_position` and `harness_rear_position` (AH, AI) are not used by part.py, which has rail-insert placeholders
  and no rear connector. They are loaded and will drive the connectors once the clip is known.
- The fit app's `document.cad_target.parameter_table` says `part.py PARAMS`. If Fusion is chosen, it
  should point at `fusion/stock_params.py`.
- With the sample record, `chk_holder_hand` is −0.2 mm. This is the same spare-mag-holder and prone-hand overlap that r1 already flagged.

## 9. Verified so far
- `stock_params.py` against `samples/fit-sample.json`: 153 parameters, all expressions evaluate, and
  values match the fit app. Tests: `uv run --with pytest --no-project python -m pytest designs/biathlon-stock/fusion -q` (9 pass).
- The sample is generated with the fit app's own `buildExport` from its test fixture. The values are
  typical-range midpoints, not Darren's.
- **Not yet run inside Fusion.** The Fusion MCP was unavailable during this work (Fusion closed).
  The first run should check: parameter creation, a unitless switch, negative offsets and
  extrudes (§4), and the read-back of `chk_*`.

## Files
| File | Purpose |
|---|---|
| `stock_params.py` | Registry and resolver (stdlib only). CLI preview, `--csv` for ParameterIO |
| `fusion_load_params.py` | Fusion script: create or update User Parameters from a fit record |
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
