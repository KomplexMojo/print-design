"""Fusion 360 script: build the demo stock from the User Parameters ("Hybrid" restyle).

Run after fusion_load_params.py in the same design. Every sketch point is pinned by two
driving dimensions whose expressions are User Parameter expressions, so changing a
parameter (or re-running the loader with a new fit record) moves the geometry. Features
(extrudes, fillets, chamfers) take their sizes from parameter expressions too. Nothing is
typed as a number except the sketch datum (a fixed point 1000 mm below and behind the
trigger, so every dimension stays positive whatever sign a coordinate has).

Layout (see README.md §5 and §10):
  root      = skeleton: user parameters, the side-outline sketch with the two split lines
  rear_stock / main_body / forestock = rigid components (PAHT-CF); each extrudes its own
              region of the shared outline and adds its own features
  action_cradle = the only part that touches the barrelled action: receiver bed, bedding-screw pillars,
              trigger slot and magazine well. Its dimensions are the act_* parameters, which the loader
              fills from the preset for the fit record's action type (stock_params.ACTIONS). It drops into
              a pocket of fixed section in the main body and is fused to it for printing (FUSE_ACTION).
  tpu_grip / tpu_prone_pad = soft parts (TPU) carried on rigid cores; grip_cap locks the sleeve
  hardware_M6 = bolts and nuts, for reading the joints only

Style ("Hybrid", Darren 2026-11-24): flowing rigid surfaces (profile corners rounded with
parameter radii, a faceted and rounded belly under the forend, rounded side edges) combined
with straight-edged geometric windows (truss windows in the butt, the block window, the row
of spare-mag slots).

Handedness: every lateral feature uses face_side / bolt_dir signed planes and distances.
Nothing is mirrored.

Demo shortcuts (flag in the doc, not in the print model): no teardrop holes, no trigger slot,
no front harness mount, grip and pad surfaces are smooth (no finger grooves or texture yet).
"""

import math
import os
import sys

import adsk.core
import adsk.fusion

DATUM = 1000.0  # mm
OBSOLETE_PARAMS = ("chk_pillar_mag", "act_receiver_d", "sling_tab_r", "rel_len", "guard_div",
                   "block_top_len", "grip_toe", "rs_rib_x", "saddle_h", "block_bolt_x", "block_insert_depth",
                   "chk_slot_pillar", "chk_key_slot", "act_slot_x0", "act_slot_x1", "act_slot_w",
                   "wrist_facet_w", "wrist_facet_h", "chk_belly_step", "chk_rel_travel", "chk_bolts_centred", "sling_head_h", "finger_clear", "blk_scoop_d", "chk_comb_length", "chk_pad_pocket", "rail_w", "rail_h", "rail_y", "chk_rail_barrel", "chk_rail_web", "rail_x0", "rail_len", "rail_screw_inset", "rail_nut_depth", "chk_rail_nose", "blk_win_web", "block_slot_r", "chk_block_top_flat", "collar_round", "rear_cap", "wrist_round")
FUSE_BLOCK = False   # True joins the standing block into the main body (the printed part)
FUSE_ACTION = False  # True joins the action cradle into the main body (the printed part); False keeps it apart for review

# r2 values (PR 3) that differ from the r1 registry defaults: written as [manual] so the
# loader leaves them alone on the next run. New demo-only shape parameters are [demo].
# What an athlete's fit record may change (Darren 2026-11-24): stock length (lop), cheek height (cheek_to_eye),
# hand stop position, the two harness connector positions, and which side the spare magazines sit on. Every other
# dimension is locked: the rows below pin the ones the loader would otherwise drive from body measurements.
USER_FITTED = ("lop", "cheek_to_eye", "handstop_position", "harness_front_position", "harness_rear_position", "face_side")
DEMO_PARAMS = [
    ("buttplate_length", "mm", "150 mm", "[manual] locked: butt plate heel to toe"),
    ("buttplate_drop", "mm", "60 mm", "[manual] locked: bore to butt-plate centre"),
    ("buttplate_curve_radius", "mm", "150 mm", "[manual] locked: curve of the butt plate"),
    ("hook_drop", "mm", "15 mm", "[manual] locked: butt-plate bottom to hook contact"),
    ("hook_reach", "mm", "20 mm", "[manual] locked: hook tip behind the butt plate"),
    ("grip_circumference", "mm", "125.7 mm", "[manual] locked: grip girth (the TPU sleeve is the athlete-specific part)"),
    ("prone_hand_length", "mm", "80 mm", "[manual] locked: no longer drives geometry"),
    ("mag_holder_count", "", "4", "[manual] locked: four spare magazines"),
    ("barrel_d", "mm", "22 mm", "[manual] locked: set by the action, not by the athlete"),
    ("chk_holder_joint", "mm", "mag_holder_start - front_split - 5 mm", "[manual] the spare-mag slots start ahead of the front joint"),
    ("chk_holder_hand", "mm", "0 mm", "[manual] superseded: the prone pad sits below the slots, so the two no longer compete"),
    ("chk_rail_handstop", "mm", "0 mm", "[manual] superseded by the chk_harness_* checks"),
    ("mag_side", "", "-face_side", "[demo] side of the spare-mag slots: +1 = shooter's right, -1 = left. Default is the side away from the face; set +1 or -1 to choose. The slots always sit in the same place along the forestock"),
    ("sight_line_above_bore", "mm", "67 mm", "[manual] PENDING MEASUREMENT: derived as current comb height (AB, 20 mm) + the measured rear sight above the cheek rest (47.2 mm, Darren 2026-11-24). Confirm with bore centre to sight aperture centre"),
    ("forend_tip", "mm", "455 mm", "[manual] locked: forestock length; the hand stop moves along it"),
    ("forend_depth", "mm", "62 mm", "[manual] restyle: 6 mm webs above and below the mag slots; IBU MC 3.1.6.4 a"),
    ("grip_depth", "mm", "40 mm", "[manual] locked"),
    ("grip_width", "mm", "36 mm", "[manual] locked"),
    ("grip_length", "mm", "80 mm", "[manual] Darren 2026-11-24: 5 mm of margin to the 140 mm line (chk_depth_grip)"),
    ("grip_angle_deg", "deg", "78 deg", "[manual] restyle: raked like current biathlon grips"),
    ("mag_holder_start", "mm", "222 mm", "[manual] r2 flush slots"),
    ("mag_holder_wall", "mm", "8 mm", "[manual] web between the spare-mag slots, re-spaced for the 36 mm slots"),
    ("mag_holder_top", "mm", "-19 mm", "[manual] restyle: 6 mm web under the barrel channel"),
    ("min_wall", "mm", "6 mm", "[demo] thinnest structural web allowed in PAHT-CF"),
    # ---- body section
    ("body_round", "mm", "6 mm", "[demo] edge round on the side faces of every rigid part"),
    ("belly_w", "mm", "10 mm", "[demo] belly facet under the forend: width taken off the bottom face"),
    ("belly_h", "mm", "5 mm", "[demo] belly facet: height taken off the side face (must stay under the step up to the wrist: chk_belly_step)"),
    ("pocket_r", "mm", "5 mm", "[demo] corner radius of the inlet pockets and openings, as on Darren's stock (estimated 4 to 6 mm from photos)"),
    ("chk_mark_round", "mm", "forend_depth - body_round - belly_h - 2 mm - marking_height",
     "[demo] MC 3.1.6.4 l: flat side of the forend stays >= 40 mm high after rounding and the belly facet"),
    ("tip_round", "mm", "8 mm", "[demo] forend nose and hook corner"),
    ("tip_rake", "mm", "6 mm", "[demo] forend nose leans back by this much"),
    ("tip_depth", "mm", "38 mm", "[demo] bore to the bottom of the forend nose"),
    ("comb_nose", "mm", "12 mm", "[demo] heel to comb, and comb to wrist ramps"),
    ("bolt_thumb_room", "mm", "22 mm", "[demo] PLACEHOLDER: room for the thumb behind the bolt at the end of its travel (Darren 2026-11-24)"),
    ("bolt_clear_x", "mm", "action_rear - act_bolt_travel - bolt_thumb_room", "[demo] derived: the stock stays below the bolt from the action's rear back to here"),
    ("wrist_top", "mm", "-(act_bed_w / 2 + 2 mm)", "[demo] derived: the flat behind the action sits 2 mm below the receiver's underside, so the bolt and the thumb pass over it"),
    ("comb_rise", "mm", "18 mm", "[demo] length of the ramp from the bolt flat up to the comb"),
    ("wrist_step", "mm", "10 mm", "[demo] length of the ramp from the bolt flat up to the stock top beside the action; it starts at the action's rear"),
    ("comb_length", "mm", "lop + bolt_clear_x - comb_rise", "[manual] derived: the comb starts behind the bolt's travel and the thumb, whatever the length of pull"),
    ("chk_wrist_socket", "mm", "wrist_top - (rear_tongue_y + rear_tongue_height / 2) - 5 mm", "[demo] 5 mm of wall between the bolt flat and the rear joint socket"),
    ("comb_front_r", "mm", "24 mm", "[demo] the comb turns down to the bolt flat in an S-curve of two of these rounds"),
    ("heel_sweep", "mm", "35 mm", "[demo] the comb falls to the heel of the butt plate over this length"),
    ("chk_comb_flat", "mm", "comb_length - heel_sweep - 80 mm", "[demo] USER-FITTED RANGE: at least 80 mm of level comb left for the cheek"),
    ("heel_sweep_r", "mm", "60 mm", "[demo] round where the comb starts to fall toward the heel"),
    ("hook_sweep_r", "mm", "20 mm", "[demo] round where the butt underside turns into the hook"),
    ("strut_round", "mm", "5 mm", "[demo] edge round of the butt's window rims, so the rib, strut and plate post are rounded bars"),
    ("hook_thickness", "mm", "30 mm", "[demo] butt face to the hook's underside corner"),
    ("hook_round", "mm", "6 mm", "[demo]"),
    ("butt_bot_y", "mm", "-buttplate_drop - buttplate_length / 2", "[demo] derived: bore to butt-plate toe"),
    ("hook_tip_y", "mm", "butt_bot_y - hook_drop", "[demo] derived"),
    # ---- wrist and grip
    ("wrist_ramp", "mm", "7 mm", "[demo]"),
    ("wrist_heel_x", "mm", "-130 mm", "[demo]"),
    ("wrist_heel_y", "mm", "-52 mm", "[demo]"),
    ("wrist_heel_r", "mm", "60 mm", "[demo] sweep from the wrist into the butt underside (its tangent must stay behind the rear joint)"),
    ("grip_top_y", "mm", "-55 mm", "[demo] derived: the grip hangs from the wrist underside"),
    ("grip_lean", "", "tan(90 deg - grip_angle_deg)", "[demo] grip lean per mm of height"),
    ("grip_front_x", "mm", "-trigger_reach + grip_depth / 2", "[demo] derived: grip front at its top"),
    ("grip_offset", "mm", "0 mm", "[demo] grip centre offset toward the away (palm) side"),
    ("butt_flare_len", "mm", "45 mm", "[demo] the butt is as wide as the main body at the rear joint and narrows to comb_width over this length, so there is no step at the joint"),
    ("butt_flare_x", "mm", "rear_split - butt_flare_len", "[demo] derived: where the butt reaches comb_width"),
    ("flute_d", "mm", "1.5 mm", "[demo] depth of the side flutes that carry the spare-mag slot line along the main body and the forestock's face side"),
    ("flute_x0", "mm", "0 mm", "[demo] rear end of the main body's flutes (ahead of the bolt-handle notch)"),
    ("flute_x1", "mm", "marking_start - 10 mm", "[demo] derived: front end of the main body's flutes, short of the IBU marking surface"),
    ("chk_flute_mark", "mm", "marking_start - flute_x1 - 5 mm", "[demo] MC 3.1.6.4 l: the flutes stop before the marking surface"),
    ("grip_z0", "mm", "-face_side * (grip_offset + grip_width / 2)", "[demo] derived: away-side skin of the grip"),
    ("grip_round", "mm", "(2 * (grip_depth + grip_width) - grip_circumference) / (8 - 2 * PI)",
     "[demo] derived: corner round that makes the grip girth equal grip_circumference (PI * M)"),
    ("grip_back_r", "mm", "160 mm", "[demo] palm swell: arc of the grip's back"),
    ("chk_grip_round", "mm", "grip_width / 2 - grip_round - 1 mm", "[demo] the girth round fits the grip width"),
    ("chk_depth_grip", "mm", "ibu_depth_max + grip_top_y - grip_length",
     "[demo] MC 3.1.6.4 a read strictly: grip bottom within 140 mm of the bore"),
    # ---- trigger guard and standing block (Darren 2026-11-24: the block is an extension of the guard base)
    ("guard_open_h", "mm", "24 mm", "[demo] trigger guard opening height: compact, close under the action"),
    ("guard_front_x", "mm", "27 mm", "[demo] front of the guard's front leg"),
    ("guard_bar", "mm", "9 mm", "[demo] trigger-guard rail thickness; the rail is the top of the standing block"),
    ("guard_rake", "mm", "4 mm", "[demo] guard front leg thickness over the bar"),
    ("guard_width", "mm", "32 mm", "[demo] trigger-guard width: about midway between the old 18 mm guard and the block, so the two read as one form"),
    ("guard_rear_r", "mm", "10 mm", "[demo] large radius where the guard rail flows into the grip front"),
    ("guard_corner_r", "mm", "8 mm", "[demo] radius of the other corners of the trigger opening"),
    ("blk_tuck", "mm", "12 mm", "[demo] the block starts this far behind the front of the trigger opening, clear of the hand on the grip"),
    ("blk_scoop_r", "mm", "400 mm", "[demo] the block's rear face is near flat; the rail's quarter-round carries the curve"),
    ("block_drop", "mm", "28 mm", "[demo] thickness of the standing block below the guard rail (compact, Darren 2026-11-24)"),
    ("block_height", "mm", "guard_bottom + block_drop", "[manual] derived: bore to the bottom of the standing block; IBU MC 3.1.6.4 a"),
    ("block_top_r", "mm", "8 mm", "[demo] round of the block's top front corner (must exceed block_round)"),
    ("plug_h", "mm", "5 mm", "[demo] lower unit: height of the plate that plugs into the stock underside"),
    ("plug_w", "mm", "30 mm", "[demo] lower unit: width of that plate (inside the flat of the underside)"),
    ("plug_x0", "mm", "rear_split + rear_tongue_length + 2 mm", "[demo] derived: the plate starts ahead of the rear joint socket"),
    ("heel_len", "mm", "14 mm", "[demo] rigid heel at the rear of the standing block (carries the finger scoop and the tongue; the cover slides up to it)"),
    ("blk_heel_x", "mm", "blk_rear_x + heel_len", "[demo] derived: front face of the heel, where the TPU cover stops"),
    ("detent_w", "mm", "4 mm", "[demo] cross groove under the block tongue; a rib inside the cover snaps into it"),
    ("detent_d", "mm", "1.5 mm", "[demo] depth of that groove"),
    ("rail_taper_len", "mm", "18 mm", "[demo] the guard rail narrows over this length before it meets the grip"),
    ("rail_taper_w", "mm", "4 mm", "[demo] half-width the rail narrows to inside the grip"),
    ("chk_plug_floor", "mm", "-act_trig_depth - (finger_hole_y1 + plug_h) - 1.5 mm", "[demo] stock left between the trigger pocket floor and the lower unit's plate"),
    ("guard_gusset_r", "mm", "18 mm", "[demo] quarter-round that carries the guard's front leg forward into the top of the block (tangent at both ends)"),
    ("collar_h", "mm", "5 mm", "[demo] rigid skin (1 mm more than guard_round, so it can carry its edge round): skin along the top of the block, part of the guard's outline, just thick enough to carry its edge round; the TPU cover fits up under it"),
    ("nose_cap", "mm", "4 mm", "[demo] the rigid skin wraps this far round the block's rounded top front corner"),
    ("core_neck", "mm", "3 mm", "[demo] dovetail of the block's rib: this much narrower per side at the top than at the bottom, so the cover cannot pull off downward"),
    ("chk_gusset_bolt", "mm", "act_screw_rear_x - (act_head_d + 3 mm) / 2 - (guard_front_x + guard_gusset_r)", "[demo] the leg's sweep stays clear of the rear mounting bolt's hole"),
    ("guard_blend_r", "mm", "14 mm", "[demo] radius that blends the guard rail into the block's rear face"),
    ("guard_round", "mm", "4 mm", "[demo] edge round on the guard and on the standing block (one radius, so their surfaces line up)"),
    ("rel_front_x", "mm", "guard_front_x - guard_rake - guard_bar", "[demo] derived: front of the trigger opening"),
    ("finger_hole_x1", "mm", "rel_front_x", "[manual] trigger opening front"),
    ("blk_rear_x", "mm", "rel_front_x - blk_tuck", "[demo] derived: rear face of the standing block, under the front of the trigger opening"),
    ("blk_rake", "mm", "0 mm", "[demo] the block's rear face is vertical, so the rail's quarter-round meets it tangentially"),
    ("blk_front_rake", "mm", "2 mm", "[demo] block and front-leg face lean (near vertical)"),
    ("block_width", "mm", "guard_width", "[demo] derived: the block is exactly as wide as the guard, so their sides are one flush surface with no ledge"),
    ("block_round", "mm", "guard_round", "[demo] derived: the cover's edge round equals the rigid frame's, so cover and frame are flush everywhere"),
    ("block_corner_r", "mm", "14 mm", "[demo] round of the block's bottom corners"),
    ("block_length", "mm", "blk_front_x - blk_rear_x",
     "[manual] restyle: derived, the block spans from the finger clearance to the guard front"),
    ("block_position", "mm", "(blk_front_x + blk_rear_x) / 2",
     "[manual] restyle: derived, the block sits under the trigger guard (m_AJ is kept for reference only)"),
    ("chk_block_mag", "mm", "mag_well_x0 + act_rel_zone - blk_front_x - 2 mm",
     "[demo] the block and guard stay behind the magazine well, so the magazine drops free"),
    # ---- hand stop
    ("hs_rake", "mm", "14 mm", "[demo] hand-stop front face leans by this much"),
    ("sling_tab_w", "mm", "40 mm", "[demo] Biatar sling end tab width (Darren, measured 2026-11-24)"),
    ("sling_hole_d", "mm", "5.5 mm", "[demo] Biatar sling eyelet (Darren, measured): M5 thumb screw"),
    ("sling_hole_inset", "mm", "17 mm", "[demo] Biatar sling: tab tip to eyelet centre (Darren, confirmed 2026-11-24)"),
    ("sling_seat_d", "mm", "sling_tab_t", "[demo] derived: the sling seat is as deep as the tab, so the clamp plate closes flat on it"),
    ("sling_seat_r", "mm", "(sling_tab_w + 1 mm) / 2", "[demo] derived: the seat's semicircular end, matching the tab's round tip"),
    ("sling_tip_x", "mm", "handstop_position + handstop_length - tip_round - 2 mm", "[demo] derived: where the tab's tip sits"),
    ("sling_hole_x", "mm", "sling_tip_x - sling_hole_inset", "[demo] derived: sling screw insert"),
    ("hs_width", "mm", "sling_tab_w + 8 mm", "[demo] derived: hand-stop width, 4 mm of shoulder each side of the sling seat"),
    ("chk_hs_width", "mm", "body_width - hs_width", "[demo] the hand stop is no wider than the forend"),
    ("hs_round", "mm", "4 mm", "[demo] edge round on the hand stop"),
    ("hs_rear_r", "mm", "16 mm", "[demo] the hand stop's rear face is rounded to this radius, seen from below: the web between thumb and forefinger rests against it in prone"),
    ("chk_hs_rear", "mm", "hs_width / 2 - hs_rear_r - 2 mm", "[demo] the rear rounding leaves a flat for the sling tab to leave through"),
    ("tip_sweep_x", "mm", "handstop_position + handstop_length + hs_rake + 14 mm", "[demo] derived: where the forend underside turns up to the nose"),
    # ---- spare-mag slots
    ("mag_slot_len", "mm", "36 mm", "[demo] spare-mag holder slot length along the forestock (Darren, measured 2026-11-24)"),
    ("mag_slot_h", "mm", "9.5 mm", "[demo] spare-mag holder slot height (Darren, measured 2026-11-24)"),
    ("mag_slot_r", "mm", "3 mm", "[demo] PLACEHOLDER: corner radius of the spare-mag slots"),
    ("chk_slots_handstop", "mm", "forend_tip - tip_rake - 8 mm - (mag_holder_start + mag_holder_count * mag_slot_len + (mag_holder_count - 1) * mag_holder_wall)", "[demo] the row of slots ends before the forend nose"),
    ("mag_slot_depth", "mm", "42 mm", "[demo] spare-mag holder slot depth into the forestock (Darren, measured 2026-11-24)"),
    ("mag_lead_r", "mm", "2.5 mm", "[demo] rounded lead-in round the mouth of each spare-mag slot (Darren 2026-11-24); the web between slots keeps a 3 mm flat"),
    ("harness_rail_y", "mm", "-10 mm", "[manual] harness rail inserts moved above the mag slots, which now reach to within 8 mm of the face side"),
    ("chk_slot_wall", "mm", "body_width - mag_slot_depth - min_wall", "[demo] wall left on the face side behind the mag slots"),
    ("chk_rail_slots", "mm", "(harness_rail_y - insert_hole_d / 2) - mag_holder_top - 3 mm", "[demo] harness inserts clear above the mag slots"),
    ("chk_slot_channel", "mm", "-(barrel_d / 2 + barrel_float) - mag_holder_top - min_wall",
     "[demo] web between the barrel channel and the mag slots >= min_wall"),
    # ---- skeleton butt: full-width comb beam and plate post, slim frame between, truss windows
    ("plate_thickness", "mm", "14 mm", "[demo] butt-plate post, measured from the deepest point of the concave face"),
    ("comb_beam_h", "mm", "comb_top + 19 mm", "[demo] derived: the butt windows start 19 mm below the bore, clear of the rear joint's bolt heads"),
    ("frame_web", "mm", "12 mm", "[demo] lower strut and window margins"),
    ("frame_rib", "mm", "12 mm", "[demo] width of the rib between the two butt windows (measured along X)"),
    ("frame_width", "mm", "24 mm", "[demo] thickness of the slim frame between the comb beam and the plate post"),
    ("rib_lean", "", "0.5", "[demo] ribs lean back by this much per mm of height (near square to the lower strut)"),
    ("win_round", "mm", "12 mm", "[demo] corner round of the butt windows; sharp-angled corners get half of it"),
    ("slim_cove", "mm", "7 mm", "[demo] cove where the slim frame meets the comb beam and the plate post"),
    ("butt_sagitta", "mm", "buttplate_curve_radius - sqrt(buttplate_curve_radius * buttplate_curve_radius - buttplate_length * buttplate_length / 4)",
     "[demo] derived: depth of the concave butt face"),
    ("rs_low_slope", "", "(wrist_heel_y - (hook_tip_y - tip_round)) / (wrist_heel_x - (-lop + hook_thickness))",
     "[demo] derived: slope of the butt underside"),
    ("rs_web_v", "mm", "frame_web * sqrt(1 + rs_low_slope * rs_low_slope)", "[demo] derived: strut width measured vertically"),
    ("rs_strut_c", "mm", "wrist_heel_y + rs_web_v - rs_low_slope * wrist_heel_x", "[demo] derived: strut upper edge at x = 0"),
    ("rs_win_top", "mm", "comb_top - comb_beam_h", "[demo] derived: top of the windows"),
    ("rs_win_rear_x", "mm", "-lop + butt_sagitta + plate_thickness", "[demo] derived: front face of the plate post"),
    ("rs_win_front_x", "mm", "-lop + comb_length - frame_web", "[demo] derived: front of the front window"),
    ("chk_butt_windows", "mm", "(rs_win_front_x - rs_win_rear_x) - frame_rib - 2 * 30 mm", "[demo] room for the two windows in the butt"),
    ("rs_rib1_x", "mm", "rs_win_rear_x + 0.26 * (rs_win_front_x - rs_win_rear_x)", "[demo] derived: rear rib centre at the window top"),
    ("rs_rib2_x", "mm", "rs_win_rear_x + 0.5 * (rs_win_front_x - rs_win_rear_x)", "[demo] derived: centre of the single rib at the window top"),
    ("rs_win_low_y", "mm", "butt_bot_y + frame_web", "[demo] derived: lowest window edge, above the toe"),
    ("rs_post_top_x", "mm", "-lop + plate_thickness + sqrt(buttplate_curve_radius * buttplate_curve_radius - (rs_win_top + buttplate_drop) * (rs_win_top + buttplate_drop)) - sqrt(buttplate_curve_radius * buttplate_curve_radius - buttplate_length * buttplate_length / 4)",
     "[demo] derived: the rear window follows the butt plate's curve, plate_thickness ahead of it (top end)"),
    ("rs_post_low_x", "mm", "-lop + plate_thickness + sqrt(buttplate_curve_radius * buttplate_curve_radius - (rs_win_low_y + buttplate_drop) * (rs_win_low_y + buttplate_drop)) - sqrt(buttplate_curve_radius * buttplate_curve_radius - buttplate_length * buttplate_length / 4)",
     "[demo] derived: same, bottom end"),
    ("rs_win_low_x", "mm", "wrist_heel_x + (rs_win_low_y - wrist_heel_y - rs_web_v) / rs_low_slope",
     "[demo] derived: where the window bottom meets the strut"),
    # ---- bolted tongue joints (Darren 2026-11-23): two fasteners per joint along X, hex nuts in the main body
    ("joint_head_d", "mm", "10 mm", "[demo] M6 socket-head diameter"),
    ("joint_head_clear", "mm", "1 mm", "[demo] clearance round the head in its cavity"),
    ("nut_af", "mm", "10 mm", "[demo] M6 hex nut across flats, ISO 4032"),
    ("nut_m", "mm", "5.2 mm", "[demo] M6 hex nut thickness, ISO 4032"),
    ("nut_slot_af", "mm", "nut_af + 2 * fit_snug", "[demo] slot across flats: snug, so the nut cannot turn"),
    ("nut_slot_len", "mm", "nut_m + 2 * fit_slide", "[demo] slot length along the bolt: slide fit, so the nut drops down the slot (the flats stay snug so it cannot turn)"),
    ("bolt_tail", "mm", "8 mm", "[demo] bolt end past the nut slot"),
    ("rear_tongue_height", "mm", "24 mm", "[manual] bolted joint"),
    ("rear_tongue_width", "mm", "34 mm", "[manual] bolted joint: both bolts inside the tongue"),
    ("rear_tongue_y", "mm", "-36 mm", "[manual] bolted joint: below the action inlet floor"),
    ("rj_bolt_z", "mm", "9 mm", "[demo] rear bolts at +/- this"),
    ("rj_engage", "mm", "6 mm", "[demo] main-body material between the tongue tip and the nuts"),
    ("rj_nut_x0", "mm", "rear_split + rear_tongue_length + rj_engage", "[demo] derived"),
    ("joint_cbore", "mm", "7 mm", "[demo] rear joint: the heads sit this deep in counterbores in the window wall (nothing proud to snag)"),
    ("joint_head_h", "mm", "6.8 mm", "[demo] what sits in a joint counterbore: M6 nut (5.2) on an ISO 7089 washer (1.6)"),
    ("rj_seat_x", "mm", "rs_win_front_x + joint_cbore", "[demo] derived: rear joint head seat"),
    ("rj_bolt_len", "mm", "rj_nut_x0 + nut_slot_len + bolt_tail - rj_seat_x", "[demo] derived: rear fastener length under the head"),
    # ---- no-snag rule (Darren 2026-11-24): every fastener head is recessed; each margin below must stay >= 0
    ("act_head_h", "mm", "6 mm", "[demo] action bolt head height"),
    ("act_bolt_hole_d", "mm", "act_screw_d + 2 * fit_slide + hole_shrink", "[demo] derived: printed clearance hole for the 6 mm action bolt (the 6.84 mm reading was the hole in the wood stock)"),
    ("act_pillar_id", "mm", "7 mm", "[demo] bedding pillar bore: 10 x 1.5 mm aluminium tube"),
    ("act_pillar_bore_d", "mm", "act_pillar_d + 2 * fit_press", "[demo] derived: printed bore for the pillar, press fit and bedded in epoxy"),
    ("act_pillar_len", "mm", "forend_depth - act_cbore - act_bed_r - 0.5 mm", "[demo] derived: pillar length, head seat to just under the receiver"),
    ("chk_pillar_head", "mm", "act_pillar_d - act_head_d", "[demo] the bolt head bears on the pillar, not on plastic"),
    ("chk_pillar_bolt", "mm", "act_pillar_id - act_screw_d - 0.5 mm", "[demo] the bolt passes through the pillar"),
    ("chk_bolt_clamp", "mm", "forend_depth - act_cbore - act_bed_r - 15 mm", "[demo] at least 15 mm of solid stock between the bolt head seat and the bed"),
    ("chk_head_action", "mm", "act_cbore - act_head_h", "[demo] no-snag: action bolt heads below the underside"),
    ("chk_head_rear_joint", "mm", "joint_cbore - joint_head_h", "[demo] no-snag: rear joint heads inside their counterbores"),
    ("joint_cbore_d", "mm", "13.5 mm", "[demo] counterbore diameter for the joint fasteners: an M6 nut or head plus a thin-wall socket"),
    ("chk_head_front_joint", "mm", "joint_cbore - joint_head_h", "[demo] no-snag: front joint heads inside their counterbores"),
    ("cap_head_d", "mm", "8.5 mm", "[demo] M5 low-head cap screw: head diameter"),
    ("cap_head_h", "mm", "3.5 mm", "[demo] M5 low-head cap screw: head height"),
    ("cap_cbore", "mm", "4 mm", "[demo] counterbore depth for the grip cap screw"),
    ("chk_head_cap", "mm", "cap_cbore - cap_head_h", "[demo] no-snag: grip cap screw head below the cap"),
    ("sling_tab_t", "mm", "3.5 mm", "[demo] Biatar sling: thickness of the tab where it meets the rifle (Darren, measured 2026-11-24)"),
    ("clamp_t", "mm", "7 mm", "[demo] sling clamp plate thickness (the extension under the hand stop that sandwiches the tab)"),
    ("clamp_cbore", "mm", "4 mm", "[demo] counterbore in the clamp plate for the M5 bolt head"),
    ("m5_nut_af", "mm", "8 mm", "[demo] M5 hex nut across flats, ISO 4032"),
    ("m5_nut_m", "mm", "4.7 mm", "[demo] M5 hex nut thickness, ISO 4032 (a 4 mm DIN 934 nut also fits)"),
    ("sling_nut_y", "mm", "-forend_fore_depth - handstop_height + sling_tab_t + 6 mm", "[demo] derived: underside of the captive nut slot in the hand stop"),
    ("chk_head_sling", "mm", "clamp_cbore - cap_head_h", "[demo] no-snag: sling bolt head inside the clamp plate"),
    ("chk_clamp_floor", "mm", "clamp_t - clamp_cbore - 2.5 mm", "[demo] clamp plate material under the bolt head"),
    ("chk_depth_clamp", "mm", "ibu_depth_max - (forend_fore_depth + handstop_height + clamp_t)", "[demo] MC 3.1.6.4 a: hand stop with the clamp plate"),
    ("front_tongue_height", "mm", "20 mm", "[manual] restyle: bolted joint"),
    ("front_tongue_y", "mm", "-46 mm", "[manual] restyle: head pocket leaves min_wall under the mag slots"),
    ("fj_bolt_z", "mm", "10 mm", "[demo] front fasteners at +/- this (room for a counterbore each)"),
    ("fj_engage", "mm", "6 mm", "[demo] main-body material between the tongue tip and the nuts"),
    ("fj_head_wall", "mm", "14 mm", "[demo] forestock material between the tongue root and the head pocket (takes the counterbores)"),
    ("front_tongue_width", "mm", "34 mm", "[manual] bolted joint: both fasteners inside the tongue"),
    ("fj_pocket_len", "mm", "34 mm", "[demo] head pocket length (socket room)"),
    ("fj_nut_x0", "mm", "front_split - front_tongue_length - fj_engage - nut_slot_len", "[demo] derived"),
    ("fj_head_x", "mm", "front_split + fj_head_wall", "[demo] derived: head seat face"),
    ("fj_seat_x", "mm", "fj_head_x - joint_cbore", "[demo] derived: front fastener seat, at the bottom of its counterbore"),
    ("fj_bolt_len", "mm", "fj_seat_x - (fj_nut_x0 - bolt_tail)", "[demo] derived: front fastener length under the head"),
    ("chk_fj_seat_wall", "mm", "fj_head_wall - joint_cbore - min_wall", "[demo] forestock left between the front counterbores and the tongue root"),
    ("chk_fj_pocket_slots", "mm", "(mag_holder_top - mag_slot_h) - (front_tongue_y + joint_cbore_d / 2 + joint_head_clear) - min_wall",
     "[demo] head pocket keeps >= min_wall under the mag slots"),
    ("chk_fj_tongue_floor", "mm", "forend_depth + front_tongue_y - front_tongue_height / 2 - min_wall",
     "[demo] socket floor under the front tongue >= min_wall"),
    ("chk_fj_pocket_hand", "mm", "handstop_position - (fj_head_x + fj_pocket_len)", "[demo] head pocket behind the hand stop"),
    ("chk_rj_head_window", "mm", "(rs_win_top - (rear_tongue_y + joint_head_d / 2)) ", "[demo] rear heads fit under the window top"),
    # ---- TPU inserts (Darren 2026-11-24): surfaces shaped purely by the athlete's body are separate TPU parts
    ("tpu_wall", "mm", "4 mm", "[demo] thinnest TPU over the rigid grip core"),
    ("cap_t", "mm", "7 mm", "[demo] rigid cap under the grip that locks the TPU sleeve; thick enough to counterbore the screw head"),
    ("cap_screw_d", "mm", "5.5 mm", "[demo] M5 clearance hole in the cap"),
    ("stock_top_y", "mm", "-(act_bed_r - act_wall_h)", "[demo] derived: top edge of the stock beside the action, from the measured bed depth"),
    ("act_trig_depth", "mm", "act_bed_r + act_trig_drop", "[demo] derived: bore to the trigger pocket floor (measured 31 mm below the bed)"),
    ("cradle_w", "mm", "action_width + 2 * cradle_wall", "[demo] derived: width of the action cradle and of its pocket in the main body"),
    ("cradle_y", "mm", "-(bore_above_inlet_floor + cradle_floor)", "[demo] derived: underside of the action cradle"),
    ("act_bed_r", "mm", "act_bed_w / 2", "[demo] derived: bed radius, copied from the measured inlet of the existing stock"),
    ("barrel_r", "mm", "barrel_d / 2 + barrel_float", "[demo] derived: half-round barrel channel radius"),
    ("chk_cradle_side", "mm", "(body_width - cradle_w) / 2 - 3 mm", "[demo] main-body wall beside the cradle"),
    ("chk_pillar_guard", "mm", "act_screw_rear_x - act_pillar_d / 2 - guard_front_x", "[demo] rear bolt pillar ahead of the trigger guard leg, so a key reaches it past the standing block"),
    ("chk_key_pillar", "mm", "act_key_x - (act_screw_rear_x + act_pillar_d / 2) - 2 mm", "[demo] cross key ahead of the rear bolt pillar"),
    ("chk_pillar_front", "mm", "action_front - (act_screw_front_x + act_pillar_d / 2) - 2 mm", "[demo] front bolt pillar inside the cradle"),
    ("chk_mag_key", "mm", "mag_well_x0 - fit_slide - (act_key_x + act_key_w) - 2 mm", "[demo] magazine well ahead of the cross key"),
    ("chk_trig_rear", "mm", "trigger_slot_x0 - (grip_front_x - grip_lean * (grip_top_y - finger_hole_y1))",
     "[demo] the trigger opening ends at the rear of the guard opening, just ahead of the grip front"),
    ("chk_trig_front", "mm", "rel_front_x - trigger_slot_x1", "[demo] the trigger opening stays inside the guard opening"),
    ("chk_trig_pocket", "mm", "(act_trig_w - trigger_slot_width) / 2 - 2 mm", "[demo] the trigger opening is inside the trigger pocket"),
    ("chk_trig_floor", "mm", "-finger_hole_y1 - act_trig_depth - min_wall", "[demo] floor under the trigger pocket"),
    ("pad_t", "mm", "3 mm", "[demo] prone hand pad thickness"),
    ("pad_wrap", "mm", "14 mm", "[demo] the pad wraps this far up each side of the forend"),
    ("pad_x0", "mm", "fj_head_x + fj_pocket_len + 4 mm", "[demo] locked: the prone pad always starts just ahead of the front joint and runs to the hand stop, wherever that is"),
    ("chk_handstop_min", "mm", "handstop_position - pad_x0 - 40 mm", "[demo] USER-FITTED RANGE: furthest back the hand stop can sit"),
    ("chk_handstop_max", "mm", "forend_tip - tip_rake - 4 mm - tip_sweep_x", "[demo] USER-FITTED RANGE: furthest forward the hand stop can sit"),
    ("harness_pitch", "mm", "20 mm", "[demo] PLACEHOLDER: spacing of the two inserts of each harness connector"),
    ("harness_rear_y", "mm", "comb_top - 14 mm", "[demo] height of the rear harness connector, in the comb beam"),
    # ---- harness anchor (Darren 2026-11-24): no rail. One steel sleeve nut at the measured harness position, right
    # through the forestock; the harness's threaded end screws into it and its own nut locks against a steel washer.
    ("anchor_y", "mm", "-36 mm", "[demo] height of the harness anchor: below the spare-mag slots and the barrel, above the belly facet"),
    ("anchor_sleeve_d", "mm", "9 mm", "[demo] PENDING MEASUREMENT: outside diameter of the M6 sleeve nut (set by the harness's thread)"),
    ("anchor_head_d", "mm", "15 mm", "[demo] PENDING: head diameter of the sleeve nut"),
    ("anchor_head_h", "mm", "3 mm", "[demo] no-snag: depth of the head's recess on the mag side"),
    ("anchor_washer_d", "mm", "12 mm", "[demo] M6 washer, ISO 7089, under the harness's lock nut"),
    ("anchor_washer_t", "mm", "1.6 mm", "[demo] washer thickness; its seat is this deep, so the washer sits flush"),
    ("chk_harness_front_lo", "mm", "harness_front_position - anchor_head_d / 2 - (mag_holder_start + mag_holder_count * mag_slot_len + (mag_holder_count - 1) * mag_holder_wall) - 2 mm", "[demo] USER-FITTED RANGE: the harness anchor sits ahead of the spare-mag slots"),
    ("chk_harness_front_hi", "mm", "forend_tip - tip_rake - 20 mm - harness_front_position", "[demo] USER-FITTED RANGE: the harness anchor sits behind the forend's nose"),
    ("chk_harness_rear_lo", "mm", "harness_rear_position - harness_pitch / 2 - (-lop + 25 mm)", "[demo] USER-FITTED RANGE: rear harness connector ahead of the butt plate"),
    ("chk_harness_rear_hi", "mm", "(-lop + comb_length) - (harness_rear_position + harness_pitch / 2) - 5 mm", "[demo] USER-FITTED RANGE: rear harness connector behind the front of the comb"),
    ("chk_lop_min", "mm", "comb_length - 80 mm", "[demo] USER-FITTED RANGE: shortest stock the butt takes"),
    ("keel_w", "mm", "8 mm", "[demo] pad keel width at its neck"),
    ("keel_flare", "mm", "2 mm", "[demo] dovetail undercut per side"),
    ("keel_h", "mm", "5 mm", "[demo] pad keel height"),
    ("forend_fore_depth", "mm", "50 mm", "[demo] bore to the forend underside ahead of the drop belly (the hand's forend)"),
    ("belly_x0", "mm", "fj_head_x + 2 mm", "[demo] derived: the drop belly starts to rise just ahead of the joint's head seat"),
    ("belly_x1", "mm", "fj_head_x + fj_pocket_len", "[demo] derived: the underside reaches forend_fore_depth at the end of the head pocket"),
    ("belly_sweep_r", "mm", "30 mm", "[demo] sweep radius at both ends of the drop-belly ramp"),
    ("wrist_under_y", "mm", "rear_tongue_y - rear_tongue_height / 2 - min_wall - 1 mm", "[demo] derived: wrist underside, min_wall below the rear joint socket"),
    ("grip_top_y", "mm", "wrist_under_y", "[demo] derived: the grip hangs from the wrist underside"),
    ("finger_hole_y1", "mm", "wrist_under_y", "[manual] guard opening top: level with the wrist underside, which the measured trigger pocket floor sets"),
    ("guard_bottom", "mm", "-finger_hole_y1 + guard_open_h + guard_bar", "[manual] derived: rail tight under the opening; IBU MC 3.1.6.4 a"),
    ("finger_hole_y0", "mm", "-guard_bottom + guard_bar", "[manual] guard opening bottom"),
    ("mag_flare", "mm", "4 mm", "[demo] flare round the magazine well's bottom entry (45 degrees), so magazines guide in"),
    ("rel_scoop_r", "mm", "(act_rel_len * act_rel_len / 4 + act_rel_depth * act_rel_depth) / (2 * act_rel_depth)",
     "[demo] derived: radius of the release-lever scoop from its length and depth"),
    ("chk_front_bolt_joint", "mm", "(fj_nut_x0 - bolt_tail) - (act_screw_front_x + (act_head_d + 3 mm) / 2) - 1 mm",
     "[demo] the front mounting bolt stays behind the front joint's fasteners"),
    ("chk_rel_bolt", "mm", "(mag_well_x0 - fit_slide - act_rel_len) - (act_screw_rear_x + (act_head_d + 3 mm) / 2) - 2 mm",
     "[demo] the release scoop stays clear of the rear bolt counterbore"),
    ("chk_bolt_step_socket", "mm", "-(rear_tongue_y + rear_tongue_height / 2) - act_bolt_step_depth - 2 mm",
     "[demo] the bolt-handle step stays above the rear joint socket"),
    ("chk_flare_bolts", "mm", "(mag_well_x0 - mag_flare) - (act_screw_rear_x + (act_head_d + 3 mm) / 2) - 2 mm",
     "[demo] the flare stays clear of the rear bolt counterbore (the front one is the same distance away)"),
    ("chk_flare_belly", "mm", "body_width / 2 - belly_w - (mag_well_width / 2 + fit_slide + mag_flare) - 1 mm",
     "[demo] the flare stays on the flat of the belly"),
    ("belly_ramp", "mm", "30 mm", "[demo] length of the ramp from the wrist underside down to the belly, ahead of the guard opening"),
    ("chk_ramp_bolt", "mm", "act_screw_rear_x - (act_head_d + 3 mm) / 2 - (rel_front_x + belly_ramp)", "[demo] the rear bolt counterbore sits on the flat belly, ahead of the ramp"),
    ("spine_d", "mm", "10 mm", "[demo] rigid front strip of the grip above the guard bar, so the TPU edge there is full thickness"),
    ("chk_pad_slots", "mm", "(mag_holder_top - mag_slot_h) - (-forend_fore_depth + pad_wrap) - 2 mm", "[demo] the pad stays below the mag slots"),
]


def strut_y(x):
    """Upper edge of the butt's lower strut at x (the underside line moved up by frame_web)."""
    return f"rs_low_slope * ({x}) + rs_strut_c"


def rib_hit(xt):
    """Where a rib edge that starts at (xt, rs_win_top) and leans by rib_lean meets the strut."""
    x = f"(({xt}) + rib_lean * (rs_win_top - rs_strut_c)) / (1 + rib_lean * rs_low_slope)"
    return x, strut_y(x)


def gf(y):
    """Grip front X at height y."""
    return f"grip_front_x - grip_lean * (grip_top_y - ({y}))"


def gb(y):
    """Grip back X at height y (chord of the palm-swell arc)."""
    return f"{gf(y)} - grip_depth"


def lf(y):
    """Front face of the guard leg and standing block at height y (one straight line)."""
    return f"guard_front_x - blk_front_rake * (-forend_depth - ({y})) / (block_height - forend_depth)"


class Builder:
    def __init__(self, design):
        self.d = design
        self.root = design.rootComponent
        self.um = design.unitsManager
        self.problems = []

    # ---------------------------------------------------------------- helpers
    def ev(self, expr):
        v = self.um.evaluateExpression(expr, "mm")
        if v == -1 and not self.um.isValidExpression(expr, "mm"):
            raise ValueError(f"bad expression: {expr}")
        return v  # cm

    def vi(self, expr):
        return adsk.core.ValueInput.createByString(expr)

    def sketch(self, name, plane=None):
        sk = self.root.sketches.add(plane or self.root.xYConstructionPlane)
        sk.name = name
        sk.isComputeDeferred = True
        a = sk.sketchPoints.add(adsk.core.Point3D.create(-DATUM / 10, -DATUM / 10, 0))
        a.isFixed = True
        sk._datum = a
        return sk

    def pt(self, sk, ex, ey):
        try:
            return self._pt(sk, ex, ey)
        except Exception as e:
            raise RuntimeError(f"sketch {sk.name}: point ({ex}, {ey}): {e}") from None

    def _pt(self, sk, ex, ey):
        x, y = self.ev(ex), self.ev(ey)
        # Place each point slightly off its target (the dimensions then pull it exact), so
        # Fusion infers no alignment constraints with earlier points at the same X or Y.
        self._n = getattr(self, "_n", 0) + 1
        j = 0.0007 * (self._n % 7 + 1)
        p = sk.sketchPoints.add(adsk.core.Point3D.create(x + j, y - j, 0))
        dims = sk.sketchDimensions
        O = adsk.fusion.DimensionOrientations
        dh = dims.addDistanceDimension(sk._datum, p, O.HorizontalDimensionOrientation,
                                       adsk.core.Point3D.create((x - DATUM / 10) / 2, -DATUM / 10 - 2, 0))
        dh.parameter.expression = f"({ex}) + {DATUM:g} mm"
        dv = dims.addDistanceDimension(sk._datum, p, O.VerticalDimensionOrientation,
                                       adsk.core.Point3D.create(-DATUM / 10 - 2, (y - DATUM / 10) / 2, 0))
        dv.parameter.expression = f"({ey}) + {DATUM:g} mm"
        return p

    def poly(self, sk, pts, closed=True, arcs=None):
        """pts: list of (x_expr, y_expr). arcs: {i: radius_expr} makes segment i -> i+1 an arc
        bulging toward +normal of the chord (as part.py's _arc_mid with inward=1)."""
        arcs = arcs or {}
        sps = [self.pt(sk, *p) for p in pts]
        n = len(sps)
        lines = sk.sketchCurves.sketchLines
        for i in range(n if closed else n - 1):
            a, b = sps[i], sps[(i + 1) % n]
            if i in arcs:
                rexpr, way = arcs[i] if isinstance(arcs[i], tuple) else (arcs[i], 1)     # way -1 bulges the other side
                r = self.ev(rexpr)
                ax, ay, bx, by = a.geometry.x, a.geometry.y, b.geometry.x, b.geometry.y
                cx, cy = (ax + bx) / 2, (ay + by) / 2
                ch = math.hypot(bx - ax, by - ay)
                s = r - math.sqrt(max(r * r - (ch / 2) ** 2, 0))
                nx, ny = (by - ay) / ch, -(bx - ax) / ch
                mid = adsk.core.Point3D.create(cx + way * s * nx, cy + way * s * ny, 0)
                arc = sk.sketchCurves.sketchArcs.addByThreePoints(a, mid, b)
                d = sk.sketchDimensions.addRadialDimension(arc, mid)
                d.parameter.expression = rexpr
            else:
                lines.addByTwoPoints(a, b)
        return sps

    def rect(self, sk, x0, x1, y0, y1):
        return self.poly(sk, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def circle(self, sk, cx, cy, d_expr):
        c = self.pt(sk, cx, cy)
        circ = sk.sketchCurves.sketchCircles.addByCenterRadius(c, self.ev(d_expr) / 2)
        dd = sk.sketchDimensions.addDiameterDimension(
            circ, adsk.core.Point3D.create(c.geometry.x + 1, c.geometry.y + 1, 0))
        dd.parameter.expression = d_expr
        return circ

    def done(self, sk):
        sk.isComputeDeferred = False
        return sk

    def profiles(self, sk):
        return [sk.profiles.item(i) for i in range(sk.profiles.count)]

    def offset_plane(self, name, expr, base=None):
        inp = self.root.constructionPlanes.createInput()
        inp.setByOffset(base or self.root.xYConstructionPlane, self.vi(expr))
        pl = self.root.constructionPlanes.add(inp)
        pl.name = name
        return pl

    def yz_sketch(self, name, x_expr):
        pl = self.offset_plane(f"{name}_plane", x_expr, self.root.yZConstructionPlane)
        return self.sketch(name, pl)          # sketch x = -Z, sketch y = Y, normal +X

    def extrude(self, occ, profiles, op, *, sym=None, dist=None, start=None, name=None, bodies=None, taper=None):
        comp = occ.component
        ext = comp.features.extrudeFeatures
        if isinstance(profiles, list):
            col = adsk.core.ObjectCollection.create()
            for p in profiles:
                col.add(p)
            profiles = col
        inp = ext.createInput(profiles, op)
        inp.creationOccurrence = occ
        if op != adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
            # Name the target explicitly: target detection from a root-sketch profile is not
            # reliable for every component.
            inp.participantBodies = [b.createForAssemblyContext(occ) for b in (bodies or comp.bRepBodies)]
        if sym:
            inp.setSymmetricExtent(self.vi(sym), True)
        else:
            if start:
                inp.startExtent = adsk.fusion.OffsetStartDefinition.create(self.vi(start))
            ext_def = adsk.fusion.DistanceExtentDefinition.create(self.vi(dist))
            if taper:
                inp.setOneSideExtent(ext_def, adsk.fusion.ExtentDirections.PositiveExtentDirection, self.vi(taper))
            else:
                inp.setOneSideExtent(ext_def, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        try:
            f = ext.add(inp)
        except Exception as e:
            bb = [(b.name, [round(v * 10) for v in (b.boundingBox.minPoint.x, b.boundingBox.maxPoint.x,
                                                     b.boundingBox.minPoint.y, b.boundingBox.maxPoint.y)])
                  for b in comp.bRepBodies]
            raise RuntimeError(f"{name} in {comp.name} failed: {e}; bodies {bb}") from None
        if name:
            f.name = name
        return f

    def combine(self, target, tools, op, name, keep=True):
        """target, tools: (occurrence, body) pairs. The feature lives in the root component."""
        col = adsk.core.ObjectCollection.create()
        for occ, b in tools:
            col.add(b.createForAssemblyContext(occ))
        feats = self.root.features.combineFeatures
        inp = feats.createInput(target[1].createForAssemblyContext(target[0]), col)
        inp.operation = op
        inp.isKeepToolBodies = keep
        f = feats.add(inp)
        f.name = name
        return f

    # ---- edge finders and rounding
    @staticmethod
    def sharp(e):
        if e.faces.count != 2:
            return False
        ok, t0, t1 = e.evaluator.getParameterExtents()
        ok, p = e.evaluator.getPointAtParameter((t0 + t1) / 2)
        ok1, n1 = e.faces.item(0).evaluator.getNormalAtPoint(p)
        ok2, n2 = e.faces.item(1).evaluator.getNormalAtPoint(p)
        return ok1 and ok2 and n1.angleTo(n2) > 0.08

    @staticmethod
    def z_edge(e):
        g = e.geometry
        if g.curveType != adsk.core.Curve3DTypes.Line3DCurveType:
            return None
        a, b = g.startPoint, g.endPoint
        if abs(a.x - b.x) < 1e-4 and abs(a.y - b.y) < 1e-4 and abs(a.z - b.z) > 0.05:
            return a.x, a.y
        return None

    def fillet(self, comp, sets, name, chain=False):
        """sets: list of (edges, radius_expr). A failure is reported, not raised, so one bad
        round does not hide the rest of the model."""
        fil = comp.features.filletFeatures
        inp = fil.createInput()
        n = 0
        for edges, r in sets:
            col = adsk.core.ObjectCollection.create()
            for e in edges:
                col.add(e)
            n += col.count
            if col.count:
                try:
                    inp.edgeSetInputs.addConstantRadiusEdgeSet(col, self.vi(r), chain)
                except AttributeError:
                    inp.addConstantRadiusEdgeSet(col, self.vi(r), chain)
        if not n:
            self.problems.append(f"{name}: no edges found")
            return None
        try:
            f = fil.add(inp)
            f.name = name
            return f
        except Exception as e:
            self.problems.append(f"{name}: {str(e).splitlines()[0][:120]}")
            return None

    def corners(self, occ, pts, label, body=None):
        """Round profile corners: the edge along Z at each (x, y) gets its own radius parameter."""
        comp = occ.component
        for i, (x, y, r) in enumerate(pts):
            b = body or comp.bRepBodies.item(0)
            cx, cy = self.ev(x), self.ev(y)
            edges = []
            for e in b.edges:
                xy = self.z_edge(e)
                if xy and abs(xy[0] - cx) < 0.03 and abs(xy[1] - cy) < 0.03:
                    edges.append(e)
            self.fillet(comp, [(edges, r)], f"{label}_corner_{i}")

    def round_faces(self, occ, half, r, name, zc="0 mm", facets=False, skip_x=(), skip_y=(), body=None, skip=None,
                    half_max=None):
        """Round the sharp edges of the side faces (normal along Z) that sit `half` from the
        centre plane zc. facets=True also takes the inclined belly-facet faces."""
        comp = occ.component
        b = body or comp.bRepBodies.item(0)
        zc_v, half_v = self.ev(zc), self.ev(half)
        skips = [self.ev(s) for s in skip_x]
        skips_y = [self.ev(s) for s in skip_y]
        picked = {}
        for f in b.faces:
            g = f.geometry
            if g.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
                ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
                if not (facets and ok and 0.2 < abs(n.z) < 0.95):
                    continue
            elif facets and 0.2 < abs(g.normal.z) < 0.95:
                pass
            elif half_max:      # side faces that lean (a taper): anywhere between half and half_max from the centre
                off = abs(f.pointOnFace.z - zc_v)
                if not (abs(g.normal.z) > 0.9 and half_v - 0.01 <= off <= self.ev(half_max) + 0.01):
                    continue
            elif not (abs(g.normal.z) > 0.99 and abs(abs(f.pointOnFace.z - zc_v) - half_v) < 0.01):
                continue
            for e in f.edges:
                if e.tempId in picked or not self.sharp(e):
                    continue
                if skip and skip(e):
                    continue
                ys = (e.startVertex.geometry.y, e.endVertex.geometry.y)
                if any(abs(ys[0] - s) < 0.01 and abs(ys[1] - s) < 0.01 for s in skips_y):
                    continue          # the junction with the body underside stays square
                xs = (e.startVertex.geometry.x, e.endVertex.geometry.x)
                if any(abs(xs[0] - s) < 0.06 and abs(xs[1] - s) < 0.06 for s in skips):
                    continue          # an edge lying in a joint face: leave the seam square
                picked[e.tempId] = e
        mids = [self.mid(e) for e in picked.values()]
        n_before = len(self.problems)
        f = self.fillet(comp, [(list(picked.values()), r)], name)
        if f is None and len(mids) > 1:
            # The set would not round as one feature: round the edges one at a time, so a single
            # awkward edge does not leave the whole part square, and report the ones that fail.
            del self.problems[n_before:]
            bad = []
            for i, m in enumerate(mids):
                near = [e for e in (body or comp.bRepBodies.item(0)).edges
                        if self.mid(e).distanceTo(m) < 0.005 and self.sharp(e)]
                k = len(self.problems)
                if not near or self.fillet(comp, [(near[:1], r)], f"{name}_{i}") is None:
                    del self.problems[k:]
                    bad.append("(%.0f, %.0f, %.0f)" % (m.x * 10, m.y * 10, m.z * 10))
            if bad:
                self.problems.append(f"{name}: {len(bad)} of {len(mids)} edges left square at " + " ".join(bad))
        return f

    @staticmethod
    def mid(e):
        ok, t0, t1 = e.evaluator.getParameterExtents()
        ok, p = e.evaluator.getPointAtParameter((t0 + t1) / 2)
        return p

    def fillet_y_edges(self, occ, feature, r, name):
        """Round the vertical inside corners of a pocket or opening that a cut feature made."""
        picked = {}
        for f in feature.faces:
            for e in f.edges:
                g = e.geometry
                if g.curveType != adsk.core.Curve3DTypes.Line3DCurveType or not self.sharp(e):
                    continue
                a, b = g.startPoint, g.endPoint
                if abs(a.x - b.x) < 1e-4 and abs(a.z - b.z) < 1e-4 and abs(a.y - b.y) > 0.05:
                    picked[e.tempId] = e
        return self.fillet(occ.component, [(list(picked.values()), r)], name)

    def round_rear_face(self, occ, x_expr, half_expr, r, name, body=None):
        """Round a part's rear face as seen from above or below: fillet its two vertical edges at x, +/- half."""
        b = body or occ.component.bRepBodies.item(0)
        x, half = self.ev(x_expr), self.ev(half_expr)
        picked = []
        for e in b.edges:
            g = e.geometry
            if g.curveType != adsk.core.Curve3DTypes.Line3DCurveType:
                continue
            a, c = g.startPoint, g.endPoint
            if (abs(a.x - c.x) < 1e-4 and abs(a.z - c.z) < 1e-4 and abs(a.y - c.y) > 0.05
                    and abs(a.x - x) < 0.01 and abs(abs(a.z) - half) < 0.01 and self.sharp(e)):
                picked.append(e)
        return self.fillet(occ.component, [(picked, r)], name)

    def fillet_z_edges(self, occ, feature, r, name):
        """Round the corners (edges along Z) that a cut feature made: geometric windows with soft corners."""
        picked = {}
        for f in feature.faces:
            for e in f.edges:
                if self.z_edge(e) and self.sharp(e):
                    picked[e.tempId] = e
        return self.fillet(occ.component, [(list(picked.values()), r)], name)

    def belly(self, occ, label, ys=("-forend_depth", "-forend_fore_depth"), w="belly_w", h="belly_h"):
        """Facet the two bottom edges at height ys (w off the bottom face, h off the side face)."""
        comp = occ.component
        cf = comp.features.chamferFeatures
        ys, zh = [self.ev(y) for y in ys], self.ev("body_width / 2")
        for sign in (1, -1):
            for flipped in (False, True):
                edge = None       # the longest straight underside edge; the chamfer follows its tangent chain
                for e in comp.bRepBodies.item(0).edges:
                    g = e.geometry
                    if g.curveType != adsk.core.Curve3DTypes.Line3DCurveType or e.length < 2:
                        continue
                    a, b = g.startPoint, g.endPoint
                    if any(all(abs(p.y - y) < 1e-3 and abs(p.z - sign * zh) < 1e-3 for p in (a, b)) for y in ys):
                        if edge is None or e.length > edge.length:
                            edge = e
                if edge is None:
                    self.problems.append(f"{label}_belly: bottom edge not found (side {sign})")
                    break
                col = adsk.core.ObjectCollection.create()
                col.add(edge)
                inp = cf.createInput2()
                inp.chamferEdgeSets.addTwoDistancesChamferEdgeSet(col, self.vi(w), self.vi(h), flipped, True)
                try:
                    f = cf.add(inp)
                except Exception as e:
                    self.problems.append(f"{label}_belly: {str(e).splitlines()[0][:120]}")
                    break
                n = next(fc.geometry.normal for fc in f.faces
                         if fc.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType)
                if (abs(n.y) > abs(n.z)) == (self.ev(w) > self.ev(h)):   # w lies on the bottom face: correct way round
                    f.name = f"{label}_belly_{'p' if sign > 0 else 'n'}"
                    break
                f.deleteMe()

    # ---------------------------------------------------------------- build
    def params(self):
        up = self.d.userParameters
        # action parameters normally come from the loader; add any that an older load did not create
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import importlib
        import stock_params
        stock_params = importlib.reload(stock_params)   # Fusion keeps modules loaded between runs
        for row in stock_params.REGISTRY:
            if row.group == "action" and up.itemByName(row.name) is None:
                up.add(row.name, self.vi(row.default), row.unit, f"[fit] {row.note} (placeholder)")
        # apply the preset of the selected action, so a preset edit shows without re-running the loader
        code = round(up.itemByName("action_type").value)
        for a in stock_params.ACTIONS.values():
            if a["code"] == code:
                for name, expr in a["values"].items():
                    q = up.itemByName(name)
                    if q is not None and not q.comment.startswith("[manual]"):
                        q.expression = expr
        for name, unit, expr, comment in DEMO_PARAMS:
            p = up.itemByName(name)
            if p is None:
                up.add(name, self.vi(expr), unit, comment)
            elif not p.comment.startswith("[manual]") or comment.startswith("[manual]") or p.comment.startswith(comment[:8]):
                p.expression, p.comment = expr, comment
        for name in OBSOLETE_PARAMS:          # left behind by earlier versions of this script
            q = up.itemByName(name)
            if q is not None:
                q.deleteMe()  # after the loop above, so nothing still refers to it

    def clear(self):
        tl = self.d.timeline
        for i in range(tl.count - 1, -1, -1):
            e = tl.item(i).entity
            if e is not None:
                e.deleteMe()
        for i in range(self.root.occurrences.count - 1, -1, -1):
            self.root.occurrences.item(i).deleteMe()

    def build(self):
        NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
        INTERSECT = adsk.fusion.FeatureOperations.IntersectFeatureOperation
        self.clear()
        self.params()
        root = self.root

        occs = {}
        for key, label in (("rear", "rear_stock"), ("main", "main_body"), ("fore", "forestock"),
                           ("action", "action_cradle"), ("block", "lower_unit"), ("bcover", "tpu_block_cover"), ("clamp", "sling_clamp"), ("grip", "tpu_grip"), ("pad", "tpu_prone_pad"), ("cap", "grip_cap")):
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = label
            occs[key] = occ
        rear, main, fore = occs["rear"], occs["main"], occs["fore"]

        def xz_sketch(name, y_expr):
            """Sketch on a plane parallel to XZ at height y. Returns the sketch, a function that maps a model X
            expression to the sketch's first axis, and +1 / -1 for whether a positive extrude goes down. The
            sketch's _fz maps a model Z expression to its second axis."""
            y = self.ev(y_expr)
            pl = self.offset_plane(f"{name}_plane", y_expr, root.xZConstructionPlane)
            if abs(pl.geometry.origin.y - y) > 0.01:
                pl.deleteMe()
                pl = self.offset_plane(f"{name}_plane", f"-({y_expr})", root.xZConstructionPlane)
            sk = self.sketch(name, pl)
            q = sk.modelToSketchSpace(adsk.core.Point3D.create(1, y, 1))
            down = -1 if sk.xDirection.crossProduct(sk.yDirection).y > 0 else 1
            sk._fz = (lambda z: z) if q.y > 0 else (lambda z: f"-({z})")
            return sk, (lambda x: x if q.x > 0 else f"-({x})"), down

        def body(key, i=0):
            return occs[key].component.bRepBodies.item(i)

        # ---- skeleton: side outline + split lines (one sketch, three regions)
        fd, ffd = "-forend_depth", "-forend_fore_depth"
        sk = self.sketch("skeleton_outline")
        P = [
            ("-lop", "-buttplate_drop + buttplate_length / 2"),                  # 0 heel
            ("-lop + heel_sweep", "comb_top"),                                    # 1 comb starts to fall to the heel
            ("-lop + comb_length", "comb_top"),                                   # 2 comb front
            ("bolt_clear_x", "wrist_top"),                                        # 3 rear end of the bolt flat
            ("action_rear", "wrist_top"),                                         # 4 bolt flat runs to the action's rear
            ("action_rear + wrist_step", "stock_top_y"),                          # 5 ramp up beside the action (the bed is cut out of it)
            ("forend_tip", "stock_top_y"),                                               # 5 nose top
            ("forend_tip - tip_rake", "-tip_depth"),                              # 6 nose bottom
            ("tip_sweep_x", ffd),                                                 # 7 underside turns up
            ("belly_x1", ffd),                                                    # 8 drop-belly ramp, front
            ("belly_x0", fd),                                                     # 9 drop-belly ramp, rear
            ("rel_front_x + belly_ramp", fd),                                     # 10 ramp down from the wrist to the belly
            ("rel_front_x", "finger_hole_y1"),                                    # 11 release window, top front
            (f"{gb('wrist_under_y')} - wrist_ramp", "wrist_under_y"),             # 12 behind the grip
            ("wrist_heel_x", "wrist_heel_y"),                                     # 13
            ("-lop + hook_thickness", "hook_tip_y - tip_round"),                  # 14
            ("-lop - hook_reach + hook_round", "hook_tip_y - hook_round"),        # 15
            ("-lop - hook_reach", "hook_tip_y"),                                  # 16 hook tip
            ("-lop", "butt_bot_y"),                                               # 17 toe
        ]
        self.poly(sk, P, arcs={17: "hook_radius", 18: "buttplate_curve_radius"})
        for xs in ("rear_split", "front_split"):
            self.poly(sk, [(xs, "sight_line_above_bore + 50 mm"), (xs, "-ibu_depth_max - 60 mm")], closed=False)
        self.done(sk)
        regions = sorted(self.profiles(sk), key=lambda pr: pr.boundingBox.minPoint.x)
        assert len(regions) == 3, f"expected 3 outline regions, got {len(regions)}"
        rear_pr, main_pr, fore_pr = regions

        self.extrude(rear, rear_pr, NEW, sym="body_width", name="rear_blank")
        # the butt leaves the joint at the main body's width and narrows to the comb: no step between the parts
        sk, fx, down = xz_sketch("butt_flare", "sight_line_above_bore + 20 mm")
        far = "-lop - hook_reach - 20 mm"
        for op in ("+", "-"):
            edge = f"cast_z {op} comb_width / 2"
            out = f"0 mm {op} (body_width / 2 + 2 mm)"
            self.poly(sk, [(fx("rear_split"), sk._fz(out)), (fx("rear_split"), sk._fz(f"0 mm {op} body_width / 2")),
                           (fx("butt_flare_x"), sk._fz(edge)), (fx(far), sk._fz(edge)), (fx(far), sk._fz(out))])
        self.done(sk)
        depth = "sight_line_above_bore + ibu_depth_max + 80 mm"
        self.extrude(rear, self.profiles(sk), CUT, dist=depth if down > 0 else f"-({depth})", name="butt_flare")
        self.extrude(main, main_pr, NEW, sym="body_width", name="main_blank")
        self.extrude(fore, fore_pr, NEW, sym="body_width", name="fore_blank")

        # ---- flowing profile: each outline corner gets its own radius (convex ones >= body_round)
        self.corners(rear, [(*P[0], "tip_round"), (*P[1], "heel_sweep_r"), (*P[2], "comb_front_r"), (*P[3], "comb_front_r"),
                            (*P[14], "wrist_heel_r"), (*P[15], "hook_sweep_r"), (*P[18], "hook_round")], "rear")
        self.corners(fore, [(*P[6], "tip_round"), (*P[7], "tip_round + body_round"),
                            (*P[9], "belly_sweep_r"), (*P[10], "belly_sweep_r")], "fore")

        # ---- faceted belly under the forend, then the hand stop, then the side rounds
        self.belly(main, "main")
        self.belly(fore, "fore")

        self.round_faces(rear, "comb_width / 2", "body_round", "rear_round", zc="cast_z", skip_x=("rear_split",),
                         half_max="body_width / 2 + comb_cast")
        self.round_faces(main, "body_width / 2", "body_round", "main_round", facets=True, skip_x=("rear_split", "front_split"))
        self.round_faces(fore, "body_width / 2", "body_round", "fore_round", facets=True, skip_x=("front_split",))
        hp = "handstop_position"
        sk = self.sketch("hand_stop")
        hs_top, hs_bot = f"{ffd} + belly_h + 2 mm", f"{ffd} - handstop_height"
        self.poly(sk, [(hp, hs_top), (f"{hp} + handstop_length + hs_rake", hs_top), (f"{hp} + handstop_length + hs_rake", ffd),
                       (f"{hp} + handstop_length", hs_bot), (hp, hs_bot)])
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), JOIN, sym="hs_width", name="hand_stop")

        self.round_rear_face(fore, hp, "hs_width / 2", "hs_rear_r", "hand_stop_rear")
        y_hull = self.ev(ffd)       # leave the junction with the forend's belly square; round the free edges below it
        self.round_faces(fore, "hs_width / 2", "hs_round", "hand_stop_round", skip_y=(hs_top, hs_bot),
                         skip=lambda e: max(e.startVertex.geometry.y, e.endVertex.geometry.y) > y_hull + 0.01)

        # ---- trigger guard and standing block: ONE component (Darren 2026-11-24), like the 1827 F Comfort. The
        # guard's bottom rail is the top of the block; the trigger opening is compact with rounded corners and
        # a large radius where the rail flows into the grip front. A removable TPU cover, shaped to the athlete's
        # hold, slips over the block from below (bottom, sides and ends) and a dovetail keel holds it on.
        # The component is joined to the main body before printing (FUSE_BLOCK). No fasteners.
        blk, bcov = occs["block"], occs["bcover"]
        gbm, fh0, y1, rf = "-guard_bottom", "finger_hole_y0", "finger_hole_y1", "rel_front_x"
        bh, btop, ct = "-block_height", gbm, "cover_t"
        top_e = f"{y1} + 6 mm"                      # the leg's top is buried in the body
        rr, rc = "guard_rear_r", "guard_corner_r"
        sk = self.sketch("trigger_guard")
        rg, rb, tr = "guard_gusset_r", "guard_blend_r", "block_top_r"
        shoulder = f"{gbm} - collar_h"              # underside of the rigid skin; the TPU cover fits up to it
        nose_y, nose_x = f"{gbm} - {tr}", "blk_front_x - nose_cap"
        # One flowing outline. Every transition is a true tangent arc: the front leg sweeps forward into the top
        # of the block, the top rolls over the front corner, and the rail's underside rolls down into the
        # block's vertical rear face. The TPU cover fits whatever is left underneath.
        self.poly(sk, [(f"{rf} - {rc}", top_e), ("guard_front_x", top_e),
                       (lf(f"{gbm} + {rg}"), f"{gbm} + {rg}"), (f"{lf(gbm)} + {rg}", gbm),          # 2 -> 3: leg into block top
                       (f"blk_front_x - {tr}", gbm), ("blk_front_x", nose_y),                      # 4 -> 5: top front corner
                       (nose_x, nose_y), (f"{nose_x} - ({tr} - collar_h)", shoulder),              # underside of the nose cap
                       ("blk_rear_x + 6 mm", shoulder), ("blk_rear_x + 6 mm", f"{gbm} - {rb}"),
                       ("blk_rear_x", f"{gbm} - {rb}"), (f"blk_rear_x - {rb}", gbm),               # 10 -> 11: rail into the block's rear
                       (f"{gf(gbm)} - 6 mm", gbm), (f"{gf(f'{fh0} + {rr}')} - 6 mm", f"{fh0} + {rr}"),
                       (gf(f"{fh0} + {rr}"), f"{fh0} + {rr}"), (f"{gf(fh0)} + {rr}", fh0),          # 14 -> 15: rail into grip
                       (f"{rf} - {rc}", fh0), (rf, f"{fh0} + {rc}"),                               # 16 -> 17: opening, front lower corner
                       (rf, f"{y1} - {rc}"), (f"{rf} - {rc}", y1)],                                # 18 -> 19: opening, front upper corner
                  arcs={2: rg, 4: (tr, -1), 10: rb, 14: rr, 16: rc, 18: rc})
        self.done(sk)
        self.extrude(blk, sk.profiles.item(0), NEW, sym="guard_width", name="trigger_guard")
        y_sh, y_nose, x_heel, x_rear = self.ev(shoulder), self.ev(nose_y), self.ev("blk_heel_x"), self.ev("blk_rear_x")

        def under_skin(e):      # edges on the underside of the rigid skin: the cover butts against them, keep them square
            a_, b_ = e.startVertex.geometry, e.endVertex.geometry
            if abs(a_.z - b_.z) > 1e-4:
                return False
            buried = (min(a_.x, b_.x) > x_rear - 0.01 and max(a_.x, b_.x) < x_heel + 0.01 and max(a_.y, b_.y) < y_sh + 0.01)
            return buried or (min(a_.x, b_.x) > x_heel - 0.9 and max(a_.y, b_.y) < y_sh + 0.01 and min(a_.y, b_.y) > y_nose - 0.01)

        self.round_faces(blk, "guard_width / 2", "guard_round", "guard_round", skip_y=(top_e,), skip=under_skin)

        def block_profile(sk, inset, x_shift="0 mm", y_top=None, y_low=None):
            lo = y_low or f"{bh} + {inset}"
            self.poly(sk, [(f"blk_rear_x + {inset} + {x_shift}", y_top or btop), (f"blk_front_x - {inset}", y_top or btop),
                           (f"blk_front_x - blk_front_rake - {inset}", lo), (f"blk_rear_x + blk_rake + {inset} + {x_shift}", lo)],
                      arcs={3: "blk_scoop_r"})                                                     # finger scoop at the rear
            self.done(sk)

        def block_solid(occ, name, inset, width, corner_r, edge_r, top_corner=True):
            lo = f"{bh} + {inset}"
            sk = self.sketch(name)
            block_profile(sk, inset)
            self.extrude(occ, sk.profiles.item(0), NEW, sym=width, name=name)
            b = occ.component.bRepBodies.item(occ.component.bRepBodies.count - 1)
            self.corners(occ, [(f"blk_front_x - blk_front_rake - {inset}", lo, corner_r),
                               (f"blk_rear_x + blk_rake + {inset}", lo, corner_r)]
                         + ([(f"blk_front_x - {inset}", btop, "block_top_r")] if top_corner else []), name, body=b)
            if edge_r:
                self.round_faces(occ, f"({width}) / 2", edge_r, f"{name}_round", skip_y=(btop,), body=b)
            return b

        # plate that plugs into the stock underside (the stock gets the matching pocket at the end)
        sk = self.sketch("lower_plug")
        self.rect(sk, "plug_x0", "guard_front_x", y1, f"{y1} + plug_h")
        self.done(sk)
        self.extrude(blk, sk.profiles.item(0), JOIN, sym="plug_w", name="lower_plug")

        # standing block. Rigid: the skin on top (in the guard outline above), a heel at the rear, and a dovetail
        # rib under the skin. The TPU cover is the hold surface: it slides on from the front, under the skin and
        # over the rib, until it meets the heel.
        def cut_box(occ, name, x0, x1, y0, y1_, bodies=None):
            sk = self.sketch(name)
            self.rect(sk, x0, x1, y0, y1_)
            self.done(sk)
            return self.extrude(occ, sk.profiles.item(0), CUT, sym="2 * body_width", name=name, bodies=bodies)

        def cut_above_skin(occ, name, bodies=None):
            """Remove everything from the rigid skin's underside upward (the skin and nose cap own that space)."""
            sk = self.sketch(name)
            self.poly(sk, [("blk_rear_x - 10 mm", f"{btop} + 5 mm"), ("blk_front_x + 10 mm", f"{btop} + 5 mm"),
                           ("blk_front_x + 10 mm", nose_y), (nose_x, nose_y),
                           (f"{nose_x} - ({tr} - collar_h)", shoulder), ("blk_rear_x - 10 mm", shoulder)])
            self.done(sk)
            return self.extrude(occ, sk.profiles.item(0), CUT, sym="2 * body_width", name=name, bodies=bodies)

        # heel and cover are cut from the same rounded shape, so they are flush where they meet
        heel = block_solid(blk, "block_heel", "0 mm", "block_width", "block_corner_r", "block_round", top_corner=False)
        cut_box(blk, "block_heel_front", "blk_heel_x", "blk_front_x + 10 mm", f"{bh} - 5 mm", f"{btop} + 5 mm", [heel])
        cut_above_skin(blk, "block_heel_top", [heel])
        sk = self.yz_sketch("block_rib", "blk_heel_x")
        cw, t_lo = f"(block_width / 2 - {ct})", f"{bh} + {ct}"
        self.poly(sk, [(f"-({cw} - core_neck)", shoulder), (f"{cw} - core_neck", shoulder), (cw, t_lo), (f"-{cw}", t_lo)])
        self.done(sk)
        self.extrude(blk, sk.profiles.item(0), NEW, dist=f"blk_front_x - blk_front_rake - {ct} - blk_heel_x", name="block_rib")
        rib = blk.component.bRepBodies.item(blk.component.bRepBodies.count - 1)
        cut_box(blk, "block_detent", "blk_heel_x + 8 mm", "blk_heel_x + 8 mm + detent_w", f"{t_lo} - 1 mm", f"{t_lo} + detent_d", [rib])
        cut_above_skin(blk, "block_rib_top", [rib])     # the rib stops under the nose cap
        extra = [(blk, blk.component.bRepBodies.item(i)) for i in range(1, blk.component.bRepBodies.count)]
        self.combine((blk, body("block")), extra, JOIN, "lower_unit_join", keep=False)

        # TPU cover: its own part, customised and printed per athlete. Closed at the front and underneath, so it
        # hides the hole for the rear mounting bolt. A rib inside it snaps into the groove under the rigid rib.
        block_solid(bcov, "block_cover", "0 mm", "block_width", "block_corner_r", "block_round", top_corner=False)
        cut_box(bcov, "block_cover_rear", "blk_rear_x - 10 mm", "blk_heel_x", f"{bh} - 5 mm", f"{btop} + 5 mm")
        cut_above_skin(bcov, "block_cover_top")
        self.combine((bcov, body("bcover")), [(blk, body("block"))], CUT, "block_cover_sleeve")

        # ---- action cradle: everything that depends on the action type lives in this one component.
        # The main body only has a pocket of fixed section (cradle_w wide, down to cradle_y).
        act = occs["action"]
        both = (main, act)
        sk = self.sketch("cradle_pocket")
        self.rect(sk, "action_rear", "action_front", "cradle_y", "sight_line_above_bore")
        self.done(sk)
        self.extrude(main, sk.profiles.item(0), CUT, sym="cradle_w", name="cradle_pocket")
        sk = self.sketch("cradle_block")
        self.rect(sk, "action_rear", "action_front", "cradle_y", "stock_top_y")
        self.done(sk)
        self.extrude(act, sk.profiles.item(0), NEW, sym="cradle_w", name="cradle_block")

        sk = self.yz_sketch("receiver_bed", "action_rear")      # half-round bed with straight walls above the bore
        self.poly(sk, [("-act_bed_r", "5 mm"), ("-act_bed_r", "0 mm"), ("act_bed_r", "0 mm"), ("act_bed_r", "5 mm")],
                  arcs={1: "act_bed_r"})
        self.done(sk)
        self.extrude(act, sk.profiles.item(0), CUT, dist="action_front - action_rear", name="receiver_bed")

        def through(name, x0, x1, y0, y1, width, dist=None, comps=None, corners=False):
            corner_r = corners if isinstance(corners, str) else "pocket_r"
            sk = self.sketch(name)
            self.rect(sk, x0, x1, y0, y1)
            self.done(sk)
            for occ in comps or both:
                if dist:
                    f = self.extrude(occ, sk.profiles.item(0), CUT, dist=dist, name=name)
                else:
                    f = self.extrude(occ, sk.profiles.item(0), CUT, sym=width, name=name)
                if corners:
                    self.fillet_y_edges(occ, f, corner_r, f"{name}_corners_{occ.component.name}")

        # 1827 F layout, muzzle to butt: receiver front step (action_front), front mounting bolt, locating pin,
        # magazine well, steel cross key, rear mounting bolt, deeper trigger pocket
        through("mag_well", "mag_well_x0 - fit_slide", "mag_well_x1 + fit_slide", f"{fd} - 1 mm", "0 mm",
                "mag_well_width + 2 * fit_slide", corners=True)
        through("trigger_pocket", "act_trig_x0", "act_trig_x1", "-act_trig_depth", "0 mm", "act_trig_w",
                corners="pocket_r + (act_trig_w - trigger_slot_width) / 2")     # concentric with the opening's corners
        through("trigger_slot", "trigger_slot_x0", "trigger_slot_x1", "finger_hole_y1 - 1 mm", "-act_trig_depth + 1 mm", "trigger_slot_width",
                comps=(main, blk), corners=True)
        through("bolt_notch", "bolt_notch_x - bolt_notch_length / 2", "bolt_notch_x + bolt_notch_length / 2",
                "-bolt_notch_depth", "sight_line_above_bore", None, dist="bolt_dir * body_width")
        if self.ev("act_bolt_step_len") > 0.01:     # deeper step at the rear of the notch, for the handle's lever
            through("bolt_step", "bolt_notch_x - bolt_notch_length / 2", "bolt_notch_x - bolt_notch_length / 2 + act_bolt_step_len",
                    "-act_bolt_step_depth", "sight_line_above_bore", None, dist="bolt_dir * body_width")
        sk = self.sketch("cross_key_seat")
        self.rect(sk, "act_key_x", "act_key_x + act_key_w", "-act_bed_r - act_key_d", "-act_bed_r + 4 mm")
        self.done(sk)
        self.extrude(act, sk.profiles.item(0), CUT, sym="act_key_len", name="cross_key_seat")

        # mounting bolts: a stepped hole each. A bore for an aluminium bedding pillar runs from the bed down to
        # the head seat, and only the bottom act_cbore is opened to head size. The bolt head bears on the
        # pillar and the pillar on the receiver, metal to metal (Darren 2026-11-24)
        def drill(name, y_expr, x_expr, d_expr, depth, comps):
            sk, fx, down = xz_sketch(name, y_expr)
            self.circle(sk, fx(x_expr), "0 mm", d_expr)
            self.done(sk)
            for occ in comps:
                self.extrude(occ, sk.profiles.item(0), CUT, dist=depth if down > 0 else f"-({depth})", name=name)

        for nm, x, under in (("front", "act_screw_front_x", fd), ("rear", "act_screw_rear_x", fd)):
            drill(f"{nm}_pillar_bore", "0 mm", x, "act_pillar_bore_d", "ibu_depth_max", both)
            drill(f"{nm}_screw_counterbore", f"{under} + act_cbore", x, "act_head_d + 3 mm", "act_cbore + 2 mm", (main,))
        # flared magazine entry: a 45 degree funnel round the bottom of the well
        yb, x0, x1 = self.ev(fd), self.ev("mag_well_x0 - fit_slide") - 0.01, self.ev("mag_well_x1 + fit_slide") + 0.01
        zw = self.ev("mag_well_width / 2 + fit_slide") + 0.01
        rim = adsk.core.ObjectCollection.create()
        for e in body("main").edges:
            bb = e.boundingBox
            if (abs(bb.minPoint.y - yb) < 1e-3 and abs(bb.maxPoint.y - yb) < 1e-3 and bb.minPoint.x > x0 and bb.maxPoint.x < x1
                    and bb.minPoint.z > -zw and bb.maxPoint.z < zw):
                rim.add(e)
        if rim.count:
            cf = main.component.features.chamferFeatures
            inp = cf.createInput2()
            inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(rim, self.vi("mag_flare"), True)
            try:
                cf.add(inp).name = "mag_well_flare"
            except Exception as e:
                self.problems.append(f"mag_well_flare: {str(e).splitlines()[0][:120]}")
        else:
            self.problems.append("mag_well_flare: rim not found")
        if self.ev("act_rel_len") > 0.01:
            # scoop for the magazine-release lever: a rounded relief in the underside just behind the well,
            # toward the trigger (Darren 2026-11-24)
            sk = self.sketch("release_scoop")
            self.poly(sk, [("mag_well_x0 - fit_slide", fd), ("mag_well_x0 - fit_slide - act_rel_len", fd)], arcs={0: "rel_scoop_r"})
            self.done(sk)
            self.extrude(main, sk.profiles.item(0), CUT, sym="mag_well_width + 2 * fit_slide + 2 * mag_flare", name="release_scoop")
        # the block runs under the rear mounting bolt: a hole through the frame for the bolt and key; the TPU cover hides it
        drill("rear_bolt_access", gbm, "act_screw_rear_x", "act_head_d + 3 mm", "block_height", (blk,))
        drill("locating_pin", "-act_bed_r + 1 mm", "act_pin_x", "act_pin_d", "7 mm", (act,))

        # sling seat (Biatar / Larsen type sling): the flat end tab nests in a pocket under the hand stop that
        # is as wide as the tab, with a semicircular end for its round tip. It is open to the rear, where the
        # sling leaves toward the arm, and a thumb screw goes through the eyelet into a heat-set insert.
        sk, fx, down = xz_sketch("sling_seat", hs_bot)
        xr, xc, r = f"{hp} - 1 mm", "sling_tip_x - sling_seat_r", "sling_seat_r"
        ring = [(fx(xr), f"-{r}"), (fx(xc), f"-{r}"), (fx(xc), r), (fx(xr), r)]
        if fx("1") != "1":
            ring = [(x, z[1:] if z.startswith("-") else f"-{z}") for x, z in ring]   # keep the arc bulging forward
        self.poly(sk, ring, arcs={1: r})
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), CUT, dist="-(sling_seat_d)" if down > 0 else "sling_seat_d", name="sling_seat")
        # sling clamp (Darren 2026-11-24): a separate plate under the hand stop sandwiches the tab in its seat.
        # One M5 bolt goes up through the plate and the tab's eyelet into a captive hex nut that slides into a
        # slot in the hand stop; the bolt head is recessed in the plate, so nothing stands proud.
        clamp = occs["clamp"]
        cb = f"{hs_bot} - clamp_t"
        xf = f"{hp} + handstop_length - hs_rake * clamp_t / handstop_height"     # the front face carries on down
        sk = self.sketch("sling_clamp")
        self.poly(sk, [(hp, hs_bot), (f"{hp} + handstop_length", hs_bot), (xf, cb), (hp, cb)])
        self.done(sk)
        self.extrude(clamp, sk.profiles.item(0), NEW, sym="hs_width", name="sling_clamp")
        self.corners(clamp, [(xf, cb, "clamp_t - 1 mm")], "sling_clamp")
        self.round_rear_face(clamp, hp, "hs_width / 2", "hs_rear_r", "sling_clamp_rear")
        # the whole underside edge of the plate, followed round the rear curve
        cx_, cy_ = self.ev(hp), self.ev(cb)
        seed = [e for e in body("clamp").edges if self.z_edge(e)
                and abs(self.z_edge(e)[0] - cx_) < 0.03 and abs(self.z_edge(e)[1] - cy_) < 0.03]
        self.fillet(clamp.component, [(seed, "hs_round")], "sling_clamp_underside", chain=True)
        sk = self.sketch("sling_nut_slot")
        self.rect(sk, "sling_hole_x - m5_nut_af / 2 - fit_snug", "sling_hole_x + m5_nut_af / 2 + fit_snug",
                  "sling_nut_y", "sling_nut_y + m5_nut_m + 2 * fit_snug")
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), CUT, start="face_side * (m5_nut_af / 2 + 1 mm)", dist="-face_side * body_width",
                     name="sling_nut_slot")
        drill("sling_bolt_hole", "sling_nut_y + m5_nut_m + 4 mm", "sling_hole_x", "cap_screw_d", "m5_nut_m + 4 mm + 6 mm + sling_tab_t + clamp_t + 1 mm",
              (fore, clamp))
        drill("sling_bolt_counterbore", f"{cb} + clamp_cbore", "sling_hole_x", "cap_head_d + 1 mm", "clamp_cbore + 1 mm", (clamp,))

        sk = self.yz_sketch("barrel_channel", "action_front")   # half-round, like the receiver bed
        self.poly(sk, [("-barrel_r", "5 mm"), ("-barrel_r", "0 mm"), ("barrel_r", "0 mm"), ("barrel_r", "5 mm")],
                  arcs={1: "barrel_r"})
        self.done(sk)
        for occ in (main, fore):
            self.extrude(occ, sk.profiles.item(0), CUT, dist="forend_tip + tip_round - action_front", name="barrel_channel")

        # ---- joints (Darren 2026-11-23): each joint is a tongue that overlaps into a socket, locked
        # by two fasteners running along the stock (X). Hex nuts sit in printed slots in the main body
        # that match the nut's flats, so a nut cannot turn. Both nut slots open upward into the action
        # inlet or barrel channel, so they are hidden under the action and barrel and need no cover.
        def tongue_socket(carrier, x0, x1, y, h, w, sx0, sx1, label):
            sk = self.sketch(f"{label}_tongue")
            self.rect(sk, x0, x1, f"{y} - {h} / 2", f"{y} + {h} / 2")
            self.done(sk)
            self.extrude(carrier, sk.profiles.item(0), JOIN, sym=w, name=f"{label}_tongue")
            sk = self.sketch(f"{label}_socket")
            self.rect(sk, sx0, sx1, f"{y} - {h} / 2 - fit_snug", f"{y} + {h} / 2 + fit_snug")
            self.done(sk)
            self.extrude(main, sk.profiles.item(0), CUT, sym=f"{w} + 2 * fit_snug", name=f"{label}_socket")

        def nut_slots(label, x0, y, zs, top, comps=None):
            """Hex pocket matched to the nut (flats vertical, so it cannot turn), opening up to `top`."""
            sk = self.yz_sketch(f"{label}_nut_slots", x0)
            h, c2 = "nut_slot_af / 2", "nut_slot_af / 2 / (2 * cos(30 deg))"
            for z in zs:
                pts = [(z, f"{y} - 2 * {c2}"), (f"{z} + {h}", f"{y} - {c2}"), (f"{z} + {h}", top),
                       (f"{z} - {h}", top), (f"{z} - {h}", f"{y} - {c2}")]
                self.poly(sk, [(f"-({zz})", yy) for zz, yy in pts])
            self.done(sk)
            for occ in comps or (main,):
                self.extrude(occ, self.profiles(sk), CUT, dist="nut_slot_len", name=f"{label}_nut_slots")

        def bolt_holes(label, x0, length, y, zs, comps):
            sk = self.yz_sketch(f"{label}_bolts", x0)
            for z in zs:
                self.circle(sk, f"-({z})", y, "hole_d_bolt")
            self.done(sk)
            for occ in comps:
                self.extrude(occ, self.profiles(sk), CUT, dist=length, name=f"{label}_bolt_holes")

        # rear: butt-stock tongue into the main body; heads in the butt's front window
        tongue_socket(rear, "rear_split - fit_loose", "rear_split + rear_tongue_length", "rear_tongue_y",
                      "rear_tongue_height", "rear_tongue_width",
                      "rear_split - fit_loose", "rear_split + rear_tongue_length + fit_snug", "rear")
        rz = ("rj_bolt_z", "-rj_bolt_z")
        nut_slots("rear", "rj_nut_x0", "rear_tongue_y", rz, "5 mm", both)       # open right up through the bed, so the nut drops in
        bolt_holes("rear", "rs_win_front_x - 1 mm", "rj_bolt_len + joint_cbore + 1 mm", "rear_tongue_y", rz, (rear, main))
        sk = self.yz_sketch("rear_head_counterbores", "rs_win_front_x - 1 mm")
        for z in rz:
            self.circle(sk, f"-({z})", "rear_tongue_y", "joint_cbore_d")
        self.done(sk)
        self.extrude(rear, self.profiles(sk), CUT, dist="joint_cbore + 1 mm", name="rear_head_counterbores")

        # front: forestock tongue into the main body; heads in a pocket under the forestock,
        # open at the bottom, min_wall below the mag slots and outside the marking surface
        tongue_socket(fore, "front_split - front_tongue_length", "front_split + fit_loose", "front_tongue_y",
                      "front_tongue_height", "front_tongue_width",
                      "front_split - front_tongue_length - fit_snug", "front_split + fit_loose", "front")
        fz = ("fj_bolt_z", "-fj_bolt_z")
        nut_slots("front", "fj_nut_x0", "front_tongue_y", fz, "5 mm")           # open right up through the channel wall
        bolt_holes("front", "fj_nut_x0 - bolt_tail", "fj_bolt_len + joint_cbore + 1 mm", "front_tongue_y", fz, (main, fore))
        sk = self.yz_sketch("front_head_counterbores", "fj_seat_x")       # the fasteners sit below the pocket wall: nothing proud
        for z in fz:
            self.circle(sk, f"-({z})", "front_tongue_y", "joint_cbore_d")
        self.done(sk)
        self.extrude(fore, self.profiles(sk), CUT, dist="joint_cbore + 1 mm", name="front_head_counterbores")

        # hardware bodies so the joints read in the model; not printed
        hw = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        hw.component.name = "hardware_M6"
        occs["hw"] = hw
        # bedding pillars (aluminium tube), shown so the stepped holes read correctly; not printed
        sk, fx, down = xz_sketch("bedding_pillars", f"{fd} + act_cbore")
        for x in ("act_screw_front_x", "act_screw_rear_x"):
            self.circle(sk, fx(x), "0 mm", "act_pillar_d")
            self.circle(sk, fx(x), "0 mm", "act_pillar_id")
        self.done(sk)
        rings = [pr for pr in self.profiles(sk) if pr.profileLoops.count == 2]
        self.extrude(hw, rings, NEW, dist="-(act_pillar_len)" if down > 0 else "act_pillar_len", name="bedding_pillars")

        def bolt(label, seat, direction, length, y, zs):
            head_x0 = f"{seat} - 6 mm" if direction > 0 else seat
            sk = self.yz_sketch(f"{label}_bolt_heads", head_x0)
            for z in zs:
                self.circle(sk, f"-({z})", y, "joint_head_d")
            self.done(sk)
            self.extrude(hw, self.profiles(sk), NEW, dist="6 mm", name=f"{label}_heads")
            shank_x0 = seat if direction > 0 else f"{seat} - {length}"
            sk = self.yz_sketch(f"{label}_bolt_shanks", shank_x0)
            for z in zs:
                self.circle(sk, f"-({z})", y, "bolt_d")
            self.done(sk)
            self.extrude(hw, self.profiles(sk), NEW, dist=length, name=f"{label}_shanks")

        def nuts(label, x0, y, zs):
            sk = self.yz_sketch(f"{label}_nuts", f"{x0} + fit_snug")
            h, c2 = "nut_af / 2", "nut_af / 2 / (2 * cos(30 deg))"
            for z in zs:
                pts = [(z, f"{y} - 2 * {c2}"), (f"{z} + {h}", f"{y} - {c2}"), (f"{z} + {h}", f"{y} + {c2}"),
                       (z, f"{y} + 2 * {c2}"), (f"{z} - {h}", f"{y} + {c2}"), (f"{z} - {h}", f"{y} - {c2}")]
                self.poly(sk, [(f"-({zz})", yy) for zz, yy in pts])
            self.done(sk)
            self.extrude(hw, self.profiles(sk), NEW, dist="nut_m", name=f"{label}_nuts")

        bolt("rear", "rj_seat_x", 1, "rj_bolt_len", "rear_tongue_y", rz)
        nuts("rear", "rj_nut_x0", "rear_tongue_y", rz)
        bolt("front", "fj_seat_x", -1, "fj_bolt_len", "front_tongue_y", fz)
        nuts("front", "fj_nut_x0", "front_tongue_y", fz)

        sk = self.sketch("front_head_pocket")
        self.rect(sk, "fj_head_x", "fj_head_x + fj_pocket_len", f"{fd} - 1 mm",
                  "front_tongue_y + joint_cbore_d / 2 + joint_head_clear")
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), CUT, sym="2 * (fj_bolt_z + joint_cbore_d / 2 + joint_head_clear)",
                     name="front_head_pocket")

        # ---- rear stock: one thickness throughout (the slim frame and its coved pockets are gone), opened by
        # two windows. The rear window follows the butt plate's curve, so the plate
        # post is one even band; every window corner is a large round and every strut edge is rounded.
        top, low = "rs_win_top", "rs_win_low_y"
        far = "-ibu_depth_max - 60 mm"
        r2a, r2b = "rs_rib2_x - frame_rib / 2", "rs_rib2_x + frame_rib / 2"
        plate_r = "buttplate_curve_radius"
        sk = self.sketch("butt_windows")
        w1 = [("rs_post_top_x", top), (r2a, top), rib_hit(r2a), ("rs_win_low_x", low), ("rs_post_low_x", low)]
        w2 = [(r2b, top), ("rs_win_front_x", top), rib_hit(r2b)]
        self.poly(sk, w1, arcs={4: plate_r})
        self.poly(sk, w2)
        self.done(sk)
        self.extrude(rear, self.profiles(sk), CUT, sym="2 * comb_width", name="butt_windows")
        full, half_r = "win_round", "win_round / 2"
        for i, (pt, r) in enumerate(((w1[0], full), (w1[1], full), (w1[2], full), (w1[3], half_r), (w1[4], full),
                                     (w2[0], "win_round * 2 / 3"), (w2[1], "win_round * 2 / 3"), (w2[2], half_r))):
            for rr_ in (r, f"({r}) / 2", f"({r}) / 4"):      # a corner that will not take its round gets a smaller one
                k = len(self.problems)
                cx, cy = self.ev(pt[0]), self.ev(pt[1])
                edges = [e for e in body("rear").edges
                         if self.z_edge(e) and abs(self.z_edge(e)[0] - cx) < 0.03 and abs(self.z_edge(e)[1] - cy) < 0.03]
                if self.fillet(rear.component, [(edges, rr_)], f"butt_window_corner_{i}") is not None:
                    break
                if rr_ != f"({r}) / 4":
                    del self.problems[k:]
        # strut edges: the rim of both windows, on both sides, so the rib, strut and plate post read as rounded bars
        x_hi, y_hi, y_lo = self.ev("rs_win_front_x") + 0.05, self.ev(top) + 0.005, self.ev(low) - 0.005

        def not_window(e):
            m = self.mid(e)
            return not (m.x < x_hi and y_lo < m.y < y_hi)

        self.round_faces(rear, "comb_width / 2", "strut_round", "strut_round", zc="cast_z", skip=not_window)

        # ---- forestock: flush horizontal spare-mag slots on the away side, patterned by count
        away = self.offset_plane("mag_side_plane", "mag_side * body_width / 2")
        sk = self.sketch("mag_slot", away)
        self.rect(sk, "mag_holder_start", "mag_holder_start + mag_slot_len",
                  "mag_holder_top - mag_slot_h", "mag_holder_top")
        self.done(sk)
        slot = self.extrude(fore, sk.profiles.item(0), CUT, dist="-mag_side * mag_slot_depth", name="mag_slot")
        forec = fore.component
        ents = adsk.core.ObjectCollection.create()
        ents.add(slot)
        rounded = self.fillet_z_edges(fore, slot, "mag_slot_r", "mag_slot_corners")     # every corner rounded
        if rounded:
            ents.add(rounded)
        pin = forec.features.rectangularPatternFeatures.createInput(
            ents, forec.xConstructionAxis, self.vi("mag_holder_count"), self.vi("mag_slot_len + mag_holder_wall"),
            adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
        forec.features.rectangularPatternFeatures.add(pin).name = "mag_slots"
        # lead-in: the mouth of every slot is rounded, so a magazine finds its way in and seats easily
        mx0, mx1 = self.ev("mag_holder_start") - 0.05, self.ev("mag_holder_start + mag_holder_count * (mag_slot_len + mag_holder_wall)")
        my0, my1 = self.ev("mag_holder_top - mag_slot_h") - 0.005, self.ev("mag_holder_top") + 0.005
        side_sign = self.ev("mag_side * 1 mm")

        def not_slot_mouth(e):
            m = self.mid(e)
            return not (m.z * side_sign > 0 and mx0 < m.x < mx1 and my0 < m.y < my1)

        self.round_faces(fore, "body_width / 2", "mag_lead_r", "mag_slot_lead_in", skip=not_slot_mouth)

        face = self.offset_plane("flute_side_plane", "-mag_side * body_width / 2")     # the side opposite the slots
        # flutes: shallow recesses on both sides of the main body, on the line of the spare-mag slots. They stop
        # short of the IBU marking surface. The forestock's harness side is plain (Darren 2026-11-24: no indents).
        sk = self.sketch("body_flute")
        self.rect(sk, "flute_x0", "flute_x1", "mag_holder_top - mag_slot_h", "mag_holder_top")
        self.done(sk)
        for nm, start in (("p", "body_width / 2 - flute_d"), ("n", "-(body_width / 2) - 1 mm")):
            fl = self.extrude(main, sk.profiles.item(0), CUT, start=start, dist="flute_d + 1 mm", name=f"body_flute_{nm}")
            self.fillet_z_edges(main, fl, "mag_slot_r", f"body_flute_corners_{nm}")

        # harness anchor (Darren 2026-11-24): a measured position, not a rail. The harness carries the whole rifle,
        # so the load does not go into printed threads or a heat-set insert. A steel sleeve nut goes in from the
        # mag side, its head recessed, and reaches right through the forestock. The harness's threaded end screws
        # into it from the other side and its own nut locks against a steel washer in a flush seat.
        hx = "harness_front_position"
        sk = self.sketch("harness_anchor_bore", face)
        self.circle(sk, hx, "anchor_y", "anchor_sleeve_d + 2 * fit_slide")
        self.done(sk)
        self.extrude(fore, self.profiles(sk), CUT, dist="mag_side * body_width", name="harness_anchor_bore")
        sk = self.sketch("harness_anchor_washer_seat", face)
        self.circle(sk, hx, "anchor_y", "anchor_washer_d + 0.5 mm")
        self.done(sk)
        seat = max(self.profiles(sk), key=lambda pr: pr.areaProperties().area)
        self.extrude(fore, [seat], CUT, dist="mag_side * anchor_washer_t", name="harness_anchor_washer_seat")
        sk = self.sketch("harness_anchor_head_recess", away)
        self.circle(sk, hx, "anchor_y", "anchor_head_d + 0.5 mm")
        self.done(sk)
        seat = max(self.profiles(sk), key=lambda pr: pr.areaProperties().area)
        self.extrude(fore, [seat], CUT, dist="-mag_side * anchor_head_h", name="harness_anchor_head_recess")
        # the sleeve nut, for the picture
        hw_occ = occs["hw"]
        sk = self.sketch("harness_anchor_head", away)
        self.circle(sk, hx, "anchor_y", "anchor_head_d")
        self.done(sk)
        self.extrude(hw_occ, [max(self.profiles(sk), key=lambda pr: pr.areaProperties().area)], NEW,
                     dist="-mag_side * anchor_head_h", name="harness_anchor_head")
        hw_occ.component.bRepBodies.item(hw_occ.component.bRepBodies.count - 1).name = "harness_anchor"

        # rear harness connector (user-fitted): two heat-set inserts on the butt's comb beam, PENDING the rear hardware
        rear_face = self.offset_plane("harness_rear_plane", "cast_z - mag_side * comb_width / 2")
        sk = self.sketch("harness_rear_inserts", rear_face)
        for sg in ("-", "+"):
            self.circle(sk, f"harness_rear_position {sg} harness_pitch / 2", "harness_rear_y", "insert_hole_d")
        self.done(sk)
        self.extrude(rear, self.profiles(sk), CUT, dist="mag_side * insert_depth", name="harness_rear_inserts")

        # ---- TPU prone hand pad: a 3 mm skin over the belly behind the hand stop. It sits in a
        # recess (so no edge can peel), wraps up both sides and snaps in with a dovetail keel.
        pad = occs["pad"]
        ptop = f"{ffd} + pad_wrap"
        sk = self.sketch("pad_zone")
        self.rect(sk, "pad_x0", hp, f"{fd} - 1 mm", ptop)
        self.done(sk)
        self.extrude(pad, sk.profiles.item(0), NEW, sym="2 * body_width", name="pad_zone")
        self.combine((pad, body("pad")), [(fore, body("fore"))], INTERSECT, "pad_outer")
        self.extrude(fore, sk.profiles.item(0), CUT, sym="2 * body_width", name="pad_recess")
        sk = self.yz_sketch("pad_core", "pad_x0")
        hw_, lo = "body_width / 2 - pad_t", f"{ffd} + pad_t"
        self.poly(sk, [(f"-({hw_})", ptop), (hw_, ptop), (hw_, f"{lo} + belly_h"), (f"{hw_} - belly_w", lo),
                       (f"-({hw_} - belly_w)", lo), (f"-({hw_})", f"{lo} + belly_h")])
        self.done(sk)
        self.extrude(fore, sk.profiles.item(0), JOIN, dist=f"{hp} - pad_x0", name="pad_core")
        self.combine((pad, body("pad")), [(fore, body("fore"))], CUT, "pad_skin")
        kx0 = "pad_x0 + pad_t"
        sk = self.yz_sketch("pad_keel", kx0)
        kn, kw = "keel_w / 2", "keel_w / 2 + keel_flare"
        self.poly(sk, [(f"-({kn})", lo), (kn, lo), (kw, f"{lo} + keel_h"), (f"-({kw})", f"{lo} + keel_h")])
        self.done(sk)
        klen = f"{hp} - pad_t - ({kx0})"
        self.extrude(fore, sk.profiles.item(0), CUT, dist=klen, name="pad_keel_groove")
        self.extrude(pad, sk.profiles.item(0), JOIN, dist=klen, name="pad_keel")

        # ---- TPU grip: the whole hand surface is a TPU sleeve over a rigid core. The sleeve slides on
        # from below along the grip axis, is keyed by the core's section and the front spine (which also
        # carries the trigger-guard bar), and is locked by a rigid cap screwed into the core.
        grip, cap = occs["grip"], occs["cap"]
        gtop, gbot = "grip_top_y", "grip_top_y - grip_length"
        gb2 = f"{gbot} + cap_t"

        def grip_solid(occ, name, y_hi, y_lo):
            sk = self.sketch(name)
            self.poly(sk, [(gf(y_hi), y_hi), (gb(y_hi), y_hi), (gb(y_lo), y_lo), (gf(y_lo), y_lo)], arcs={1: "grip_back_r"})
            self.done(sk)
            self.extrude(occ, sk.profiles.item(0), NEW, start="grip_z0", dist="face_side * grip_width", name=name)
            b = occ.component.bRepBodies.item(0)
            long_edges = {}
            for f in b.faces:
                g = f.geometry
                if g.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType and abs(g.normal.z) > 0.99:
                    for e in f.edges:
                        if abs(e.startVertex.geometry.y - e.endVertex.geometry.y) > 0.1:
                            long_edges[e.tempId] = e
            self.fillet(occ.component, [(list(long_edges.values()), "grip_round")], f"{name}_girth")

        grip_solid(grip, "grip_outer", gtop, gb2)
        grip_solid(cap, "grip_cap", gb2, gbot)

        # no thumb shelf: Darren chose a clean grip (2026-11-24)

        # rigid core and front spine: part of the lower unit, trimmed to the grip's outer shape
        def last():
            return blk.component.bRepBodies.item(blk.component.bRepBodies.count - 1)

        sk = self.sketch("grip_core")
        ov = f"{gtop} + 3 mm"
        self.poly(sk, [(f"{gf(ov)} - tpu_wall", ov), (f"{gf(gb2)} - tpu_wall", gb2),
                       (f"{gb(gb2)} + tpu_wall", gb2), (f"{gb(ov)} + tpu_wall", ov)])
        self.done(sk)
        self.extrude(blk, sk.profiles.item(0), NEW, start="grip_z0 + face_side * tpu_wall",
                     dist="face_side * (grip_width - 2 * tpu_wall)", name="grip_core")
        long_edges = {}
        for f in last().faces:
            g = f.geometry
            if g.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType and abs(g.normal.z) > 0.99:
                for e in f.edges:
                    if abs(e.startVertex.geometry.y - e.endVertex.geometry.y) > 0.1:
                        long_edges[e.tempId] = e
        self.fillet(blk.component, [(list(long_edges.values()), "grip_round - tpu_wall")], "grip_core_girth")
        sk = self.sketch("grip_spine")
        self.poly(sk, [(gf(ov), ov), (gf(gbm), gbm), (f"{gf(gbm)} - spine_d", gbm), (f"{gf(ov)} - spine_d", ov)])
        self.done(sk)
        self.extrude(blk, sk.profiles.item(0), JOIN, start="grip_z0", dist="face_side * grip_width",
                     name="grip_spine", bodies=[last()])
        self.combine((blk, last()), [(grip, body("grip"))], INTERSECT, "grip_core_trim")
        extra = [(blk, blk.component.bRepBodies.item(i)) for i in range(1, blk.component.bRepBodies.count)]
        self.combine((blk, body("block")), extra, JOIN, "grip_core_join", keep=False)
        # the rail narrows toward the grip, so it runs into the grip's rounded front without shoulders. The wedges
        # are trimmed to the grip's outer shape first, so they only take rail that stands outside the grip.
        sk, fx, down = xz_sketch("rail_taper", f"{fh0} + guard_rear_r")
        xa, xe = f"({gf(fh0)} + guard_rear_r + rail_taper_len)", f"({gf(gbm)} - 6 mm)"
        for sgn in ("", "-"):
            self.poly(sk, [(fx(xa), f"{sgn}(guard_width / 2 + 1 mm)"), (fx(xe), f"{sgn}(guard_width / 2 + 1 mm)"),
                           (fx(xe), f"{sgn}(rail_taper_w)")])
        self.done(sk)
        depth = "guard_rear_r + guard_bar + 1 mm"
        self.extrude(blk, self.profiles(sk), NEW, dist=depth if down > 0 else f"-({depth})", name="rail_taper")
        for i in range(1, blk.component.bRepBodies.count):
            self.combine((blk, blk.component.bRepBodies.item(i)), [(grip, body("grip"))], CUT, "rail_taper_trim")
        wedges = [(blk, blk.component.bRepBodies.item(i)) for i in range(1, blk.component.bRepBodies.count)]
        self.combine((blk, body("block")), wedges, CUT, "rail_taper_cut", keep=False)
        self.combine((grip, body("grip")), [(blk, body("block"))], CUT, "grip_sleeve")
        # the stock gets a pocket that matches everything the lower unit pushes up into it (plate, guard leg, grip top)
        self.combine((main, body("main")), [(blk, body("block"))], CUT, "lower_pocket")

        # cap screw: M5 through the cap into a heat-set insert in the core
        ybot = self.ev(gbot)
        pl = self.offset_plane("cap_plane", gbot, root.xZConstructionPlane)
        if abs(pl.geometry.origin.y - ybot) > 0.01:
            pl.deleteMe()
            pl = self.offset_plane("cap_plane", f"-({gbot})", root.xZConstructionPlane)
        sk = self.sketch("cap_screw", pl)
        q = sk.modelToSketchSpace(adsk.core.Point3D.create(1, ybot, 1))
        cx = f"({gf(gbot)} - grip_depth / 2)"
        cz = "(-face_side * grip_offset)"
        ex = cx if q.x > 0 else f"-{cx}"
        ez = cz if q.y > 0 else f"-{cz}"
        self.circle(sk, ex, ez, "cap_screw_d")
        self.circle(sk, ex, ez, "insert_hole_d")
        self.done(sk)
        prs = sorted(self.profiles(sk), key=lambda pr: pr.areaProperties().area)
        self.extrude(cap, prs[-1], CUT, sym="2 * cap_t + 2 mm", name="cap_screw_hole")
        drill("cap_screw_counterbore", f"{gbot} + cap_cbore", cx, "cap_head_d + 1 mm", "cap_cbore + 1 mm", (cap,))
        self.extrude(blk, prs, CUT, sym="2 * (cap_t + insert_depth)", name="cap_insert_hole")

        if FUSE_BLOCK:
            self.combine((main, body("main")), [(blk, body("block"))], JOIN, "lower_unit_fused", keep=False)
        if FUSE_ACTION:
            self.combine((main, body("main")), [(act, body("action"))], JOIN, "action_cradle_fused", keep=False)
        self.colour(occs)
        return occs

    def colour(self, occs):
        app = adsk.core.Application.get()
        lib = app.materialLibraries.itemByName("Fusion Appearance Library")
        rigid, soft, dark = "Plastic - Matte (Gray)", "Plastic - Matte (Yellow)", "Plastic - Matte (Black)"
        # one colour for every rigid printed part, so the stock reads as one design; TPU and the small ASA parts differ
        names = {"rear": rigid, "main": rigid, "fore": rigid, "action": rigid, "block": rigid,
                 "grip": soft, "pad": soft, "bcover": soft, "cap": dark, "clamp": dark}
        for key, name in names.items():
            a = lib.appearances.itemByName(name) if lib else None
            if a:
                occs[key].appearance = self.d.appearances.itemByName(a.name) or self.d.appearances.addByCopy(a, a.name)
        self.root.isSketchFolderLightBulbOn = False
        self.root.isConstructionFolderLightBulbOn = False


def report(design, occs, problems=(), log=print):
    up = design.userParameters
    for key, occ in occs.items():
        if key == "hw":
            continue
        for b in occ.component.bRepBodies:
            bb = b.boundingBox
            size = [round((getattr(bb.maxPoint, a) - getattr(bb.minPoint, a)) * 10, 1) for a in "xyz"]
            log(f"{occ.component.name}: {b.name} valid={b.isValid} lumps={b.lumps.count} size_mm={size} "
                f"vol_cm3={b.volume:.0f} faces={b.faces.count}")
    for key in ("rear", "main", "fore", "block", "bcover", "clamp", "pad", "grip", "cap"):
        occ = occs[key]
        if not occ.component.bRepBodies.count:
            continue
        low = -min(b.boundingBox.minPoint.y for b in occ.component.bRepBodies) * 10
        log(f"{occ.component.name}: lowest point {low:.1f} mm below the bore")
    log(f"(MC 3.1.6.4 a: forestock depth incl. shelf, mag and guard <= {up.itemByName('ibu_depth_max').value * 10:.0f} mm; "
        "the standing block is part of the guard and counts; the butt hook does not)")
    bad = [up.item(i).name for i in range(up.count)
           if up.item(i).name.startswith("chk_") and up.item(i).value < -1e-7]
    log("chk_* below zero: " + (", ".join(bad) if bad else "none"))
    for n in ("action_type", "act_bed_w", "act_screw_front_x", "act_screw_rear_x", "cradle_w",
              "rj_bolt_len", "fj_bolt_len", "block_length", "block_position", "grip_round"):
        log(f"{n} = {up.itemByName(n).value * 10:.1f} mm")
    tl = design.timeline
    errs = [f"{tl.item(i).name}: {tl.item(i).errorOrWarningMessage}" for i in range(tl.count)
            if tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState]
    log("timeline problems: " + ("; ".join(errs) if errs else "none"))
    log("skipped rounds: " + ("; ".join(problems) if problems else "none"))


def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design.userParameters.itemByName("lop") is None:
        raise RuntimeError("Run fusion_load_params.py first.")
    b = Builder(design)
    occs = b.build()
    report(design, occs, b.problems)
