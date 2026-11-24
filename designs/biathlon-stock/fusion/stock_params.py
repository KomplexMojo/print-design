"""biathlon-stock: fit record JSON -> Fusion 360 User Parameters.

Pure standard-library Python, so the same module runs:
  * inside Fusion 360 (imported by fusion_load_params.py), and
  * on the command line, to preview or test without Fusion:
        python3 stock_params.py samples/fit-sample.json            # table
        python3 stock_params.py samples/fit-sample.json --csv      # ParameterIO-style CSV

Pipeline:
    fit JSON (biathlon-fit-pwa, schema biathlon-stock-fit v1)
      -> m_*  measurement parameters (raw, one per measured letter)
      -> r_*  rifle parameters
      -> fit / stock / joint parameters, as Fusion EXPRESSIONS of m_* and r_* where a rule
         exists, otherwise the part.py default as a literal (marked "estimate")
      -> chk_* IBU margin parameters (must stay >= 0)

Every row in REGISTRY is one Fusion User Parameter. Names for the fit, stock and joint
parameters are the part.py PARAMS names (tuples split into named scalars), so the
build123d model, the fit app's cad_parameters block and the Fusion model share one
vocabulary. See README.md and PARAMETERS.md next to this file.

Expressions use only Fusion syntax that is also valid Python once units are stripped
(+ - * / and parentheses, the constant PI, literals written with a unit such as `15 mm`),
so this module can evaluate every value and run the IBU checks before Fusion sees them.
"""

from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_ID = "biathlon-stock-fit"
SCHEMA_MAJOR = 1
TAG = "[fit]"          # comment prefix on every parameter this loader owns
MANUAL = "[manual]"    # a parameter whose comment starts with this is never overwritten

# Letters on the measurement sheet that are sides, not numbers (they drive face_side).
SIDE_LETTERS = {"S", "T"}


@dataclass
class P:
    """One Fusion User Parameter.

    expr     Fusion expression used when every name it references exists
    default  literal fallback (with unit) when a referenced m_* / r_* is missing
    """
    name: str
    unit: str            # "mm", "deg", "kg" or "" (unitless)
    default: str         # e.g. "335 mm", "4", "0 mm"
    group: str
    note: str = ""
    expr: str | None = None
    sources: tuple = ()  # measurement letters / rifle keys, for the table
    ibu: str = ""        # IBU rule this parameter can break


# ---------------------------------------------------------------------------- registry
# Order matters: a row may only reference rows above it.

def _p(*a, **k):
    return P(*a, **k)


# ---------------------------------------------------------------------------- actions
# One preset per action type. The fit record's rifle.action_type (or make_model) picks the preset, and
# its values become the act_* parameters and override the listed hardware parameters. The stock only
# meets the action through the `action_cradle` component (fusion_build_demo.py), so supporting another
# action means adding a preset here (and a cradle builder only if its shape family is new).
# "family" selects the cradle builder: 1 = round receiver in a half-round bed, two vertical screws from below.
# EVERY number below is a placeholder until the action is measured out of its stock (brief, "Fixed by hardware").
ACTIONS = {
    "anschutz_1827f": {
        "label": "Anschütz 1827 F / 1825 Fortner", "code": 1, "family": 1,
        "match": ("1827", "1825", "fortner"),
        # Layout read from Darren's own 1827 F stock (2026-11-24), muzzle to butt: round barrel channel, step,
        # receiver bed, FRONT mounting bolt, locating pin, magazine well, steel cross key, REAR mounting bolt,
        # trigger pocket. The two bolts straddle the magazine well, centred on it, heads recessed from below
        # (Darren, 2026-11-24). MEASURED: act_bed_w, mag_well_width, act_screw_hole_d, act_trig_w. Every
        # position, length and depth is still a placeholder.
        "values": {"act_bed_w": "30.19 mm", "mag_well_width": "16 mm", "act_screw_hole_d": "6.84 mm", "act_trig_w": "26.2 mm",
                   "action_rear": "-105 mm", "action_front": "146 mm", "action_width": "32 mm",
                   "act_screw_front_x": "136 mm", "act_pin_x": "122 mm", "mag_well_x0": "74 mm", "mag_well_x1": "114 mm",
                   "act_key_x": "62 mm", "act_screw_rear_x": "52 mm",
                   "act_trig_x0": "-42 mm", "act_trig_x1": "22 mm", "trigger_slot_x0": "-8 mm", "trigger_slot_x1": "12 mm",
                   "act_screw_d": "6 mm", "act_head_d": "10 mm"},
    },
    "izhmash_7_4": {
        "label": "Izhmash BI-7-4", "code": 2, "family": 1,
        "match": ("izhmash", "bi-7", "7-4", "7-3"),
        "values": {"act_bed_w": "28 mm", "act_screw_front_x": "130 mm", "act_screw_rear_x": "50 mm",
                   "act_screw_d": "6 mm", "act_head_d": "10 mm",
                   "action_rear": "-100 mm", "action_front": "140 mm", "action_width": "30 mm",
                   "mag_well_x0": "70 mm", "mag_well_x1": "110 mm", "mag_well_width": "22 mm"},
    },
}
DEFAULT_ACTION = "anschutz_1827f"


def pick_action(rifle: dict) -> tuple[str, bool]:
    """(preset key, matched) from rifle.action_type, action_type_other or make_model."""
    text = " ".join(str(rifle.get(k) or "") for k in ("action_type", "action_type_other", "make_model")).lower()
    for key, a in ACTIONS.items():
        if key in text or any(m in text for m in a["match"]):
            return key, True
    return DEFAULT_ACTION, False


REGISTRY: list[P] = [
    # ---- handedness and hardware sides (numeric switches; Fusion has no text parameters
    #      that features can consume, so a sign is used and the text goes in the comment)
    _p("face_side", "", "1", "switch", "+1 = left-handed (cheek on +Z, shooter's right), -1 = right-handed. Multiplies every face-side lateral offset", sources=("T",)),
    _p("bolt_dir", "", "-1", "switch", "+1 = bolt handle on the shooter's right, -1 = left. Hardware side, NOT tied to face_side", sources=("rifle.bolt_side",)),

    # ---- printer fits (printer/h2s.yaml `fits`; per side)
    _p("fit_press", "mm", "0.10 mm", "fits", "per-side clearance, press"),
    _p("fit_snug", "mm", "0.15 mm", "fits", "per-side clearance, snug (joint tongues)"),
    _p("fit_slide", "mm", "0.25 mm", "fits", "per-side clearance, slide (mag well)"),
    _p("fit_loose", "mm", "0.40 mm", "fits", "per-side clearance, loose (action inlet, bedding room)"),
    _p("hole_shrink", "mm", "0.10 mm", "fits", "small vertical holes print this much undersize (diameter)"),

    # ---- IBU limits (MC references from brief.md)
    _p("ibu_depth_max", "mm", "140 mm", "ibu", "MC 3.1.6.4 a: depth below bore incl. mag and guard"),
    _p("ibu_cheek_max", "mm", "40 mm", "ibu", "MC 3.1.6.4 b: cheek piece thickness"),
    _p("ibu_mark_start", "mm", "150 mm", "ibu", "MC 3.1.6.4 l: marking surface starts this far ahead of the trigger"),
    _p("ibu_mark_height", "mm", "40 mm", "ibu", "MC 3.1.6.4 l: marking surface min height"),
    _p("ibu_sling_max", "mm", "40 mm", "ibu", "sling width"),
    _p("ibu_mass_min", "kg", "3.5 kg", "ibu", "MC 3.1.6.4 i: rifle without mags"),

    # ---- athlete fit (part.py names). expr references m_* rows created from the JSON.
    _p("lop", "mm", "335 mm", "fit", "trigger blade to butt-plate centre; single value for prone and standing", expr="m_AA", sources=("AA", "D")),
    _p("cheek_to_eye", "mm", "27 mm", "fit", "cheek contact to aiming pupil", expr="m_P", sources=("P",)),
    _p("comb_length", "mm", "185 mm", "fit", "butt plate to comb front (design input)"),
    _p("comb_width", "mm", "40 mm", "fit", "rear stock thickness at the cheek", ibu="MC 3.1.6.4 b"),
    _p("comb_cast", "mm", "0 mm", "fit", "+ = away from the face (design input from R, Q)", sources=("R", "Q"), ibu="MC 3.1.6.4 b"),
    _p("buttplate_length", "mm", "120 mm", "fit", "butt plate heel to toe; must cover U and Y", expr="m_AD", sources=("AD", "U", "Y")),
    _p("buttplate_drop", "mm", "60 mm", "fit", "bore to butt-plate centre", expr="m_AC", sources=("AC",)),
    _p("buttplate_curve_radius", "mm", "150 mm", "fit", "circle through the plate ends with sagitta E",
       expr="(m_AD / 2) * (m_AD / 2) / (2 * m_E) + m_E / 2", sources=("AD", "E")),
    _p("hook_drop", "mm", "55 mm", "fit", "butt-plate bottom to hook contact, vertical",
       expr="m_AF - (m_AC + m_AD / 2)", sources=("AF", "AC", "AD")),
    _p("hook_reach", "mm", "30 mm", "fit", "hook tip behind the butt plate", expr="m_AE", sources=("AE",)),
    _p("hook_radius", "mm", "40 mm", "fit", "armpit curve (design input; X positions it)", sources=("X",)),
    _p("grip_angle_deg", "deg", "85 deg", "fit", "grip axis to bore (design input)"),
    _p("grip_circumference", "mm", "143 mm", "fit", "target grip girth; drives the grip section", expr="PI * m_M", sources=("M",)),
    _p("grip_length", "mm", "85 mm", "fit", "grip top to bottom (design input from F, G, J)", sources=("F", "G", "J")),
    _p("grip_depth", "mm", "48 mm", "fit", "front to back"),
    _p("grip_width", "mm", "40 mm", "fit", "side to side"),
    _p("grip_chamfer", "mm", "14 mm", "fit", "rounds the grip section"),
    _p("trigger_reach", "mm", "69 mm", "fit", "grip centre to trigger blade (design input from H, D)", sources=("H", "D")),
    _p("thumb_rest_height", "mm", "62 mm", "fit", "bore to thumb-rest centre (design input from N)", sources=("N",)),
    _p("thumb_rest_depth", "mm", "10 mm", "fit", "thumb rest stands proud of the face side"),
    _p("glove_thickness", "mm", "2 mm", "fit", "added to grip and guard clearance (Q12)"),
    _p("prone_hand_length", "mm", "90 mm", "fit", "hand behind the hand stop in prone", expr="m_J", sources=("J",)),
    _p("handstop_position", "mm", "380 mm", "fit", "trigger blade to hand-stop face", expr="m_AG", sources=("AG", "V"), ibu="MC 3.1.6.4 l"),
    _p("handstop_height", "mm", "25 mm", "fit", "below the forend", ibu="MC 3.1.6.4 a"),
    _p("handstop_length", "mm", "52 mm", "fit", ""),
    _p("sling_slot_width", "mm", "41 mm", "fit", "for a <= 40 mm sling", ibu="sling 40 mm"),
    _p("sling_slot_height", "mm", "8 mm", "fit", ""),
    _p("block_position", "mm", "150 mm", "fit", "trigger to centre of the standing block", expr="m_AJ", sources=("AJ", "Z"), ibu="MC 3.1.6.4 l"),
    _p("block_height", "mm", "130 mm", "fit", "bore to block bottom (design input from Z, Y)", sources=("Z", "Y"), ibu="MC 3.1.6.4 a"),
    _p("block_length", "mm", "90 mm", "fit", ""),
    _p("block_ramp", "mm", "15 mm", "fit", ""),
    _p("harness_front_position", "mm", "350 mm", "fit", "X of the front harness connector (not yet in part.py)", expr="m_AH", sources=("AH",), ibu="MC 3.1.6.4 l"),
    _p("harness_rear_position", "mm", "-240 mm", "fit", "X of the rear harness connector, behind the trigger (not yet in part.py)", expr="-m_AI", sources=("AI",)),
    _p("harness_rail_hole_1", "mm", "270 mm", "fit", "trigger to rear rail insert (placeholder until AH and the rail are measured)"),
    _p("harness_rail_hole_2", "mm", "350 mm", "fit", "trigger to front rail insert"),
    _p("harness_rail_y", "mm", "-30 mm", "fit", "bore to insert centre line"),
    _p("insert_hole_d", "mm", "6.4 mm", "fit", "M5 heat-set insert hole, per insert maker"),
    _p("insert_depth", "mm", "10 mm", "fit", ""),

    # ---- current-rifle reference values (informational, not driving geometry)
    _p("ref_comb_height_current", "mm", "0 mm", "reference", "current comb top relative to bore (+ above); compare with comb_top", expr="m_AB", sources=("AB",)),

    # ---- stock body
    _p("body_width", "mm", "50 mm", "stock", "main body and forestock thickness"),
    _p("wrist_top", "mm", "-12 mm", "stock", "stock top behind the action"),
    _p("forend_depth", "mm", "55 mm", "stock", "bore to forend bottom", ibu="MC 3.1.6.4 a"),
    _p("forend_tip", "mm", "440 mm", "stock", "trigger to front of the stock"),
    _p("edge_chamfer", "mm", "3 mm", "stock", ""),
    _p("foot_chamfer", "mm", "0.4 mm", "stock", "elephant's-foot chamfer on bed edges"),

    # ---- hardware (placeholders until the action is measured)
    _p("action_rear", "mm", "-105 mm", "hardware", ""),
    _p("action_front", "mm", "125 mm", "hardware", ""),
    _p("action_width", "mm", "32 mm", "hardware", ""),
    _p("bore_above_inlet_floor", "mm", "20 mm", "hardware", ""),
    _p("sight_line_above_bore", "mm", "37 mm", "hardware", "diopter + front globe"),
    _p("barrel_d", "mm", "22 mm", "hardware", "barrel at the action", expr="r_barrel_d_action", sources=("rifle.barrel_diameter_action_mm",)),
    _p("barrel_float", "mm", "2 mm", "hardware", "free-float clearance"),
    _p("guard_bottom", "mm", "90 mm", "hardware", "bore to bottom of the trigger guard", ibu="MC 3.1.6.4 a"),
    _p("trigger_slot_x0", "mm", "-8 mm", "hardware", ""),
    _p("trigger_slot_x1", "mm", "28 mm", "hardware", ""),
    _p("trigger_slot_width", "mm", "12 mm", "hardware", ""),
    _p("finger_hole_x0", "mm", "-42 mm", "hardware", ""),
    _p("finger_hole_x1", "mm", "38 mm", "hardware", ""),
    _p("finger_hole_y0", "mm", "-82 mm", "hardware", ""),
    _p("finger_hole_y1", "mm", "-45 mm", "hardware", ""),
    _p("mag_well_x0", "mm", "50 mm", "hardware", ""),
    _p("mag_well_x1", "mm", "100 mm", "hardware", ""),
    _p("mag_well_width", "mm", "22 mm", "hardware", ""),
    _p("spare_mag_t", "mm", "14 mm", "hardware", "spare mag thickness (along X)"),
    _p("spare_mag_l", "mm", "32 mm", "hardware", "spare mag length (lateral)"),
    _p("spare_mag_h", "mm", "50 mm", "hardware", "spare mag height"),
    _p("bolt_notch_x", "mm", "-62 mm", "hardware", "bolt-handle notch centre; side from bolt_dir"),
    _p("bolt_notch_length", "mm", "26 mm", "hardware", ""),
    _p("bolt_notch_depth", "mm", "12 mm", "hardware", ""),

    # ---- action cradle (values come from the ACTIONS preset; placeholders until measured)
    _p("action_type", "", "1", "action", "action preset code: 1 = Anschütz 1827 F / 1825 Fortner, 2 = Izhmash BI-7-4", sources=("rifle.action_type",)),
    _p("action_family", "", "1", "action", "cradle builder: 1 = round receiver, half-round bed, two vertical screws"),
    _p("act_bed_w", "mm", "30.19 mm", "action", "width across the half-round receiver bed"),
    _p("act_screw_front_x", "mm", "136 mm", "action", "trigger to the front mounting bolt, ahead of the magazine well"),
    _p("act_screw_rear_x", "mm", "52 mm", "action", "trigger to the rear mounting bolt, behind the magazine well"),
    _p("act_pin_x", "mm", "122 mm", "action", "trigger to the locating pin behind the receiver's front step"),
    _p("act_pin_d", "mm", "4 mm", "action", "locating pin hole"),
    _p("act_key_x", "mm", "62 mm", "action", "trigger to the rear face of the steel cross key (recoil bearing)"),
    _p("act_key_w", "mm", "8 mm", "action", "cross key size along the bore"),
    _p("act_key_d", "mm", "6 mm", "action", "cross key depth below the bed"),
    _p("act_key_len", "mm", "34 mm", "action", "cross key length across the stock"),
    _p("act_screw_hole_d", "mm", "6.84 mm", "action", "clearance hole for each of the two action mounting bolts (bore of the bedding pillar)"),
    _p("act_trig_x0", "mm", "-42 mm", "action", "trigger to the rear of the trigger pocket"),
    _p("act_trig_x1", "mm", "22 mm", "action", "trigger to the front of the trigger pocket"),
    _p("act_trig_w", "mm", "26.2 mm", "action", "trigger pocket width"),
    _p("act_trig_depth", "mm", "33 mm", "action", "bore to the trigger pocket floor"),
    _p("act_screw_d", "mm", "6 mm", "action", "action screw thread"),
    _p("act_head_d", "mm", "10 mm", "action", "action screw head"),
    _p("act_pillar_d", "mm", "12 mm", "action", "aluminium bedding pillar outside diameter"),
    _p("act_cbore", "mm", "8 mm", "action", "screw-head counterbore depth from the stock underside"),
    _p("cradle_wall", "mm", "5 mm", "action", "cradle wall each side of the receiver"),
    _p("cradle_floor", "mm", "3 mm", "action", "cradle material under the inlet floor"),

    # ---- spare magazine holder (away side)
    _p("mag_holder_count", "", "4", "holder", "", expr="r_spare_mag_count", sources=("rifle.spare_mag_count",)),
    _p("mag_holder_start", "mm", "228 mm", "holder", "trigger to rear of the holder"),
    _p("mag_holder_wall", "mm", "4 mm", "holder", ""),
    _p("mag_holder_top", "mm", "-4 mm", "holder", "bore to top of the holder"),
    _p("mag_holder_floor", "mm", "4 mm", "holder", ""),
    _p("mag_finger_notch", "mm", "18 mm", "holder", "thumb notch width in the outer wall"),
    _p("mag_holder_end", "mm", "305 mm", "holder", "derived",
       expr="mag_holder_start + mag_holder_count * (spare_mag_t + 2 * fit_snug) + (mag_holder_count + 1) * mag_holder_wall"),
    _p("mag_holder_bottom", "mm", "62 mm", "holder", "derived: bore to holder bottom",
       expr="-mag_holder_top + spare_mag_h + fit_snug + mag_holder_floor", ibu="MC 3.1.6.4 a"),

    # ---- IBU marking surface
    _p("marking_start", "mm", "150 mm", "marking", "", expr="ibu_mark_start"),
    _p("marking_length", "mm", "50 mm", "marking", ""),
    _p("marking_height", "mm", "40 mm", "marking", "", expr="ibu_mark_height"),

    # ---- splits and joints
    _p("rear_split", "mm", "-108 mm", "joints", "trigger to rear joint face"),
    _p("front_split", "mm", "215 mm", "joints", "trigger to front joint face", ibu="MC 3.1.6.4 l"),
    _p("rear_tongue_length", "mm", "40 mm", "joints", ""),
    _p("rear_tongue_height", "mm", "22 mm", "joints", ""),
    _p("rear_tongue_width", "mm", "22 mm", "joints", ""),
    _p("rear_tongue_y", "mm", "-37 mm", "joints", ""),
    _p("front_tongue_length", "mm", "30 mm", "joints", ""),
    _p("front_tongue_height", "mm", "28 mm", "joints", ""),
    _p("front_tongue_width", "mm", "30 mm", "joints", ""),
    _p("front_tongue_y", "mm", "-34 mm", "joints", ""),
    _p("bolt_d", "mm", "6 mm", "joints", "M6"),
    _p("cross_dowel_d", "mm", "10 mm", "joints", ""),
    _p("cross_dowel_x", "mm", "250 mm", "joints", "derived", expr="front_split + 35 mm"),
    _p("tie_rod_spacing", "mm", "16 mm", "joints", ""),
    _p("tie_rod_cbore_d", "mm", "11 mm", "joints", ""),
    _p("tie_rod_cbore_depth", "mm", "7 mm", "joints", ""),

    # ---- derived geometry used by several components
    _p("comb_top", "mm", "10 mm", "derived", "bore to comb top", expr="sight_line_above_bore - cheek_to_eye"),
    _p("face_z", "mm", "25 mm", "derived", "lateral position of the face-side skin of the body", expr="face_side * body_width / 2"),
    _p("away_z", "mm", "-25 mm", "derived", "lateral position of the away-side skin", expr="-face_side * body_width / 2"),
    _p("cast_z", "mm", "0 mm", "derived", "lateral shift of the rear stock (cast is away from the face)", expr="-face_side * comb_cast"),
    _p("bolt_z", "mm", "-25 mm", "derived", "lateral skin the bolt notch is cut from", expr="bolt_dir * body_width / 2"),
    _p("hole_d_bolt", "mm", "6.6 mm", "derived", "modelled M6 slide hole", expr="bolt_d + 2 * fit_slide + hole_shrink"),
    _p("hole_d_dowel", "mm", "10.3 mm", "derived", "modelled cross-dowel press hole", expr="cross_dowel_d + 2 * fit_press + hole_shrink"),

    # ---- IBU and layout margins: every chk_* must be >= 0
    _p("chk_depth_forend", "mm", "0 mm", "check", "MC 3.1.6.4 a", expr="ibu_depth_max - forend_depth"),
    _p("chk_depth_block", "mm", "0 mm", "check", "MC 3.1.6.4 a", expr="ibu_depth_max - block_height"),
    _p("chk_depth_handstop", "mm", "0 mm", "check", "MC 3.1.6.4 a", expr="ibu_depth_max - (forend_depth + handstop_height)"),
    _p("chk_depth_guard", "mm", "0 mm", "check", "MC 3.1.6.4 a", expr="ibu_depth_max - guard_bottom"),
    _p("chk_depth_holder", "mm", "0 mm", "check", "MC 3.1.6.4 a", expr="ibu_depth_max - mag_holder_bottom"),
    _p("chk_cheek", "mm", "0 mm", "check", "MC 3.1.6.4 b", expr="ibu_cheek_max - comb_width"),
    _p("chk_mark_joint", "mm", "0 mm", "check", "MC 3.1.6.4 l: front joint clear of the marking surface",
       expr="front_split - (marking_start + marking_length + 15 mm)"),
    _p("chk_mark_height", "mm", "0 mm", "check", "MC 3.1.6.4 l: flat side >= 40 mm",
       expr="forend_depth - 2 * edge_chamfer - marking_height"),
    _p("chk_rail_mark", "mm", "0 mm", "check", "MC 3.1.6.4 l: harness-rail inserts clear of the marking surface",
       expr="harness_rail_hole_1 - (marking_start + marking_length + 10 mm)"),
    _p("chk_sling", "mm", "0 mm", "check", "sling slot implies <= 40 mm sling", expr="ibu_sling_max + 1 mm - sling_slot_width"),
    _p("chk_holder_joint", "mm", "0 mm", "check", "holder clear of the front joint", expr="mag_holder_start - (front_split + 10 mm)"),
    _p("chk_holder_hand", "mm", "0 mm", "check", "holder clear of the prone hand",
       expr="(handstop_position - prone_hand_length) - mag_holder_end"),
    _p("chk_rail_handstop", "mm", "0 mm", "check", "harness-rail inserts behind the hand stop",
       expr="handstop_position - 5 mm - harness_rail_hole_2"),
    _p("chk_main_body_plate", "mm", "0 mm", "check", "main body length fits the 340 mm plate with 5 mm margins",
       expr="330 mm - (front_split - rear_split)"),
]

BY_NAME = {p.name: p for p in REGISTRY}

# Fit-app cad_parameters keys that map onto a registry row of a different name, or not at all.
CAD_ALIASES = {
    "handedness": "face_side",
    "bolt_side": "bolt_dir",
    "comb_height_above_bore": "ref_comb_height_current",
}

# Rifle fields copied as r_* parameters: JSON key -> (name, unit)
RIFLE_PARAMS = {
    "barrel_diameter_action_mm": ("r_barrel_d_action", "mm"),
    "barrel_diameter_muzzle_mm": ("r_barrel_d_muzzle", "mm"),
    "barrel_length_mm": ("r_barrel_length", "mm"),
    "spare_mag_count": ("r_spare_mag_count", ""),
    "weight_kg": ("r_weight", "kg"),
}

# Fusion rejects names that are units or built-in functions/constants.
RESERVED = {"mm", "cm", "m", "in", "ft", "deg", "rad", "kg", "g", "lb", "PI", "E",
            "sin", "cos", "tan", "sqrt", "abs", "min", "max", "round", "floor", "ceil", "exp", "log", "ln"}
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


# ---------------------------------------------------------------------------- evaluation

_UNIT_RE = re.compile(r"(?<=[0-9.])\s*(mm|deg|kg)\b")
_NAME_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def names_in(expr: str) -> set[str]:
    return {n for n in _NAME_RE.findall(_UNIT_RE.sub("", expr)) if n != "PI"}


def evaluate(expr: str, values: dict[str, float]) -> float:
    """Evaluate a registry expression (Fusion syntax subset) in mm / deg / kg / unitless."""
    py = _UNIT_RE.sub("", expr)
    missing = names_in(expr) - values.keys()
    if missing:
        raise KeyError(", ".join(sorted(missing)))
    return float(eval(py, {"__builtins__": {}}, {"PI": math.pi, **values}))  # registry-only expressions


def literal(value: float, unit: str) -> str:
    v = round(value, 3)
    v = int(v) if v == int(v) else v
    return f"{v} {unit}".strip()


# ---------------------------------------------------------------------------- resolve

@dataclass
class Row:
    name: str
    unit: str
    expression: str     # what goes into Fusion
    value: float        # evaluated, in the row's unit
    comment: str
    status: str         # measured | derived | estimate | rifle | switch | fixed | check


@dataclass
class Result:
    rows: list[Row] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ibu_flags: list[str] = field(default_factory=list)

    def by_name(self):
        return {r.name: r for r in self.rows}


def load_fit(path: str | Path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema", {}).get("id") != SCHEMA_ID:
        raise ValueError(f"{path} is not a {SCHEMA_ID} record")
    major = int(str(doc["schema"].get("version", "0")).split(".")[0])
    if major != SCHEMA_MAJOR:
        raise ValueError(f"Unsupported schema version {doc['schema'].get('version')} (need {SCHEMA_MAJOR}.x)")
    return doc


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def resolve(doc: dict, fits: dict | None = None) -> Result:
    """Turn a fit record into the ordered list of Fusion User Parameters."""
    res = Result()
    values: dict[str, float] = {}

    def add(name, unit, expression, value, comment, status):
        assert NAME_RE.match(name) and name not in RESERVED, f"bad Fusion parameter name {name}"
        values[name] = value
        res.rows.append(Row(name, unit, expression, value, f"{TAG} {comment}".strip(), status))

    # 1. raw measurements
    for letter, m in (doc.get("measurements") or {}).items():
        if letter in SIDE_LETTERS:
            continue
        v = _num(m.get("value"))
        if v is None:
            continue
        unit = {"mm": "mm", "deg": "deg"}.get(m.get("unit"), "mm")
        flag = " (outside typical range)" if m.get("flag") else ""
        add(f"m_{letter}", unit, literal(v, unit), v, f"{letter} {m.get('name', '')}{flag}", "measured")
        if flag:
            res.warnings.append(f"{letter} {m.get('name')} = {v} is outside the typical range")

    # 2. rifle
    rifle = doc.get("rifle") or {}
    for key, (name, unit) in RIFLE_PARAMS.items():
        v = _num(rifle.get(key))
        if v is not None:
            add(name, unit, literal(v, unit), v, f"rifle.{key}", "rifle")

    # 3. switches from text fields
    hand = (doc.get("athlete") or {}).get("stock_handedness") or \
        ((doc.get("cad_parameters") or {}).get("handedness") or {}).get("value")
    bolt = ((doc.get("cad_parameters") or {}).get("bolt_side") or {}).get("value")
    switch = {
        "face_side": (1 if hand == "left" else -1 if hand == "right" else None, hand),
        "bolt_dir": (1 if bolt == "right" else -1 if bolt == "left" else None, bolt),
    }
    if (doc.get("athlete") or {}).get("cross_dominant"):
        res.warnings.append("Cross-dominant athlete (aiming eye differs from shooting hand): comb and cast need a design decision")

    # 4. registry rows
    fits = fits or {}
    akey, matched = pick_action(rifle)
    action = ACTIONS[akey]
    if not matched:
        res.warnings.append(f"action type not recognised in the fit record, using {action['label']}")
    preset = {**action["values"], "action_type": str(action["code"]), "action_family": str(action["family"])}
    for p in REGISTRY:
        if p.name in preset and not p.expr:
            v = evaluate(preset[p.name], {})
            add(p.name, p.unit, preset[p.name], v, f"{p.note} [{action['label']}, placeholder]", "action")
            continue
        if p.name in switch:
            v, text = switch[p.name]
            if v is None:
                v = float(p.default)
                res.warnings.append(f"{p.name}: no value in the fit record, using default {p.default}")
                text = "default"
            add(p.name, "", str(int(v)), v, f"{text}. {p.note}", "switch")
            continue
        if p.group == "fits" and p.name in fits:
            add(p.name, p.unit, literal(fits[p.name], p.unit), fits[p.name], p.note, "fixed")
            continue
        status = "check" if p.group == "check" else "fixed"
        expr = p.expr
        if expr:
            try:
                v = evaluate(expr, values)
                if p.name == "buttplate_curve_radius" and values.get("m_E", 0) < 1:
                    raise ValueError("E under 1 mm gives a near-flat plate")
                if status != "check":
                    status = "measured" if expr.startswith("m_") or expr.startswith("r_") else "derived"
                add(p.name, p.unit, expr, v, p.note, status)
                continue
            except KeyError as e:
                if p.sources:
                    res.warnings.append(f"{p.name}: missing {e.args[0]}, using estimate {p.default}")
            except (ValueError, ZeroDivisionError) as e:
                res.warnings.append(f"{p.name}: {e}, using estimate {p.default}")
        v = evaluate(p.default, {})
        note = p.note + (" (estimate)" if p.sources else "")
        add(p.name, p.unit, p.default, v, note, "estimate" if p.sources else status)

    # 5. IBU / layout checks
    for r in res.rows:
        if r.status == "check" and r.value < 0:
            res.ibu_flags.append(f"{r.name} = {r.value:.1f} mm ({BY_NAME[r.name].note})")
    return res


def printer_fits(repo_root: Path) -> dict:
    """Read the `fits` block of printer/h2s.yaml without PyYAML (Fusion's Python has none)."""
    path = repo_root / "printer" / "h2s.yaml"
    out, inside = {}, False
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        if re.match(r"^fits:\s*$", line):
            inside = True
            continue
        if inside:
            m = re.match(r"^\s+(\w+):\s*([0-9.]+)", line)
            if not m:
                if line.strip() and not line.startswith(" "):
                    break
                continue
            key = {"hole_shrink_mm": "hole_shrink"}.get(m.group(1), m.group(1))
            out[f"fit_{key}" if key != "hole_shrink" else key] = float(m.group(2))
    return out


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------- build123d

# part.py tuple PARAMS rebuilt from the split Fusion scalars.
PART_TUPLES = {
    "harness_rail_holes": ("harness_rail_hole_1", "harness_rail_hole_2"),
    "bolt_notch": ("bolt_notch_x", "bolt_notch_length", "bolt_notch_depth"),
    "mag_well": ("mag_well_x0", "mag_well_x1", "mag_well_width"),
    "spare_mag": ("spare_mag_t", "spare_mag_l", "spare_mag_h"),
    "rear_tongue": ("rear_tongue_length", "rear_tongue_height", "rear_tongue_width", "rear_tongue_y"),
    "front_tongue": ("front_tongue_length", "front_tongue_height", "front_tongue_width", "front_tongue_y"),
    "tie_rod_counterbore": ("tie_rod_cbore_d", "tie_rod_cbore_depth"),
    "trigger_slot": ("trigger_slot_x0", "trigger_slot_x1", "trigger_slot_width"),
    "finger_hole": ("finger_hole_x0", "finger_hole_x1", "finger_hole_y0", "finger_hole_y1"),
}


def part_params(res: Result, part_keys) -> dict:
    """PARAMS overrides for part.py from the same resolved rows Fusion gets.

    Only keys that part.py already has are returned, so part.py does
    `p = {**PARAMS, **part_params(resolve(load_fit(path)), PARAMS)}`. Values are the evaluated
    numbers (build123d has no expressions), so both models see identical dimensions.
    """
    rows = {r.name: r.value for r in res.rows}
    out = {}
    if "face_side" in rows:
        out["handedness"] = "left" if rows["face_side"] > 0 else "right"
    if "bolt_dir" in rows:
        out["bolt_side"] = "right" if rows["bolt_dir"] > 0 else "left"
    for key, parts in PART_TUPLES.items():
        if all(n in rows for n in parts):
            out[key] = tuple(rows[n] for n in parts)
    for name, v in rows.items():
        if name in part_keys and name not in out:
            out[name] = int(v) if name == "mag_holder_count" else v
    return {k: v for k, v in out.items() if k in part_keys}


def params_from_fit(path, part_keys) -> dict:
    """Convenience for part.py: fit JSON path -> PARAMS overrides (prints warnings and IBU flags)."""
    res = resolve(load_fit(path), printer_fits(repo_root()))
    for w in res.warnings:
        print("fit warning:", w)
    for f in res.ibu_flags:
        print("IBU ⚠️ ", f)
    return part_params(res, part_keys)


# ---------------------------------------------------------------------------- CLI

def _main(argv):
    if not argv:
        print(__doc__)
        return 2
    res = resolve(load_fit(argv[0]), printer_fits(repo_root()))
    if "--csv" in argv:
        # Same columns as Autodesk's ParameterIO sample add-in: Name,Unit,Expression,Value,Comment
        print("Name,Unit,Expression,Value,Comment")
        for r in res.rows:
            print(",".join([r.name, r.unit, r.expression, f"{r.value:g}", '"' + r.comment.replace('"', "'") + '"']))
        return 0
    w = max(len(r.name) for r in res.rows)
    for r in res.rows:
        print(f"{r.name:<{w}}  {r.value:>9.2f} {r.unit:<3}  {r.status:<8}  {r.expression}")
    for m in res.warnings:
        print("warning:", m)
    for m in res.ibu_flags:
        print("IBU ⚠️ ", m)
    return 1 if res.ibu_flags else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
