# biathlon-stock: parts list

Everything that is not printed, plus the printed parts for reference. Sizes come from the Fusion build
(`fusion/fusion_build_demo.py`); the parameter that sets each size is named so the list can be re-checked after a change.
Every fastener is a standard catalogue size. Checked 2026-11-24.

## Fasteners and hardware to buy

| # | Item | Standard | Size | Qty | Where it goes | Set by |
|---|---|---|---|---|---|---|
| 1 | Threaded rod, cut to length | DIN 976-1, M6, A2 stainless | 150 mm long | 2 | Rear joint studs (butt to main body) | `rj_bolt_len` (146.7 mm; fits 145 to 153 mm) |
| 2 | Threaded rod, cut to length | DIN 976-1, M6, A2 stainless | 60 mm long | 2 | Front joint studs (forestock to main body) | `fj_bolt_len` (fits 55 to 63 mm) |
| 3 | Hex nut | ISO 4032, M6, A2 | 10 mm across flats, 5.2 mm thick | 8 | Joints: 4 captive in the main body's slots, 4 in the counterbores | `nut_af`, `nut_m` |
| 4 | Plain washer | ISO 7089, M6, A2 | 12 mm outside, 1.6 mm thick | 4 | Under the 4 outer joint nuts | `joint_cbore_d` (13.5 mm counterbore) |
| 5 | Low-head socket cap screw | DIN 7984, M5 x 12, A2 | head 8.5 mm wide, 3.5 mm high | 1 | Grip cap | `cap_head_d`, `cap_head_h`, `cap_cbore` |
| 6 | Low-head socket cap screw | DIN 7984, M5 x 20, A2 | head 8.5 mm wide, 3.5 mm high | 1 | Sling clamp plate | `clamp_t`, `sling_tab_t`, `sling_nut_y` |
| 7 | Hex nut | ISO 4032, M5, A2 | 8 mm across flats, 4.7 mm thick | 1 | Captive in the hand stop, for the sling bolt | `m5_nut_af`, `m5_nut_m` |
| 8 | Heat-set threaded insert, brass | M5, for a 6.4 mm hole, up to 9.5 mm long | | 5 | 1 in the grip core (cap screw), 2 in the forestock and 2 in the butt (harness connectors) | `insert_hole_d`, `insert_depth` |
| 9 | Aluminium tube | 10 mm outside x 1.5 mm wall (7 mm bore) | cut to 38.4 mm | 2 | Bedding pillars for the action bolts | `act_pillar_d`, `act_pillar_id`, `act_pillar_len` |

Notes:
- **Items 1 and 2 are studs, not bolts.** A bolt that long cannot be inserted: the butt window and the forestock pocket
  are shorter than the bolt. Thread the rod into the captive nut, slide the part on, then fit the washer and outer nut.
  With a 5.2 mm nut on a 1.6 mm washer in a 7 mm counterbore, nothing stands proud (`chk_head_rear_joint`,
  `chk_head_front_joint`). Tighten with a 10 mm thin-wall socket.
- **Item 9:** cut the pillars only after the action bolt counterbore depth is measured; the length depends on it.
- **Item 8:** check the hole size against the insert maker's data sheet. 6.4 mm suits common M5 x 9.5 inserts.

## Parts reused from the rifle (not bought)

| Item | Size | Qty | Status |
|---|---|---|---|
| Action mounting bolts | M6; length, head size and position pending measurement | 2 | Darren's existing bolts. The stock gives a 6.6 mm clearance hole (ISO 273 medium for M6) through the pillar, and a 13 mm wide, 8 mm deep counterbore. |
| Steel cross key (recoil bearing) | 8 x 6 x 34 mm assumed, pending measurement | 1 | From the existing stock, or cut from key steel to the measured size. |
| Sling | Biatar, tab 40 mm wide, 3.5 mm thick, 5.5 mm eyelet 17 mm from the tip | 1 | Measured. |

## Printed parts

| Component | Material | Notes |
|---|---|---|
| `rear_stock` | PAHT-CF | butt, comb, hook |
| `main_body` | PAHT-CF | joined with `action_cradle` and `lower_unit` before printing |
| `action_cradle` | PAHT-CF | action-specific inlet |
| `lower_unit` | PAHT-CF | grip core, trigger guard, standing block tongue |
| `forestock` | PAHT-CF | |
| `sling_clamp` | ASA | |
| `grip_cap` | ASA | |
| `tpu_grip` | TPU | sleeve over the grip core |
| `tpu_block_cover` | TPU | sleeve over the standing block tongue, customised per athlete |
| `tpu_prone_pad` | TPU | |

## Hole sizes in the printed parts

| Hole | Size | Standard behind it |
|---|---|---|
| M6 clearance (joints, action bolts) | 6.6 mm | ISO 273 medium fit for M6 |
| M5 clearance (grip cap, sling clamp) | 5.5 mm | ISO 273 medium fit for M5 |
| Pillar bore | 10.2 mm | 10 mm tube plus press fit |
| M6 nut slot | 10.3 mm across flats, 5.7 mm along the stud | ISO 4032 M6 nut plus fit |
| M5 nut slot | 8.3 mm across flats, 5.0 mm thick | ISO 4032 M5 nut plus fit |
