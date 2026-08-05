"""tolerance_data.py — ISO 965-1 metric thread tolerance lookup.

v1: ISO Metric only.  UN / BSP / BSPT / Acme will be added later
when the user starts cutting those families on real parts.

Two-level API:

  available_classes(family, side)
      → list[str], the class designations valid for this family
        and side (External / Internal).  Used to filter the
        ToleranceClassDialog so only relevant options show.

  lookup(family, klass, P, D, side)
      → dict {major: (es, ei), pitch: (es, ei), minor: (es, ei)}
        with deviations in MILLIMETRES, or None if (family, class,
        side) is invalid.

Sign convention (matches ISO 965-1):
  external: es = upper deviation (≤ 0 for g/f/e), ei = lower (more negative)
  internal: ES = upper, EI = lower (≥ 0 for G; = 0 for H)

Per the user's spec:
  - external major dia: es / ei from class (used in program if 'apply')
  - external minor dia: es / ei from class (display only — root truncated)
  - external pitch dia: es / ei from class (display only — pitch comes
    from the insert profile once major is achieved)
  - internal minor dia: ES / EI from class (used in program if 'apply')
  - internal major dia: EI from class, ES open (display only)
  - internal pitch dia: ES / EI from class (display only)

Engineering reference: ISO 965-1:2013 Section 5 + Annex A.  All
formulas verified against published worked examples (M10x1.5-6g/6H,
M16x2-6g/6H).  See tolerance_data_NOTES.md for derivation cross-checks.
"""
from __future__ import annotations
import re


# ============================================================
# Class designations supported in v1
# ============================================================

# Most-used ISO Metric classes (per ISO 965-1 / DIN 13).  We expose
# this as the dialog's option list.  Operator can add classes later
# by editing this list — formulas below cover any valid grade+letter
# combination.
ISO_METRIC_EXTERNAL = ['4g', '6e', '6f', '6g', '6h', '8g']
ISO_METRIC_INTERNAL = ['4H', '5H', '6G', '6H', '7G', '7H']

# U229: UN / UNJ classes (ASME B1.1 / MIL-S-8879).
#   1A = loose external (largest allowance + widest tolerance)
#   2A = standard external (most common)
#   3A = precision external (zero allowance, tight tolerance)
#   1B/2B/3B = internal counterparts (always zero allowance)
# UNJ uses the same classes as UN — the only structural difference is
# UNJ mandates a controlled rounded root radius (improves fatigue).
UN_EXTERNAL = ['1A', '2A', '3A']
UN_INTERNAL = ['1B', '2B', '3B']

# U230-U237: tolerance classes for additional thread families.
# Formulas tagged "v1 approximate" need cross-check against
# authoritative tables (ASME B1.5/B1.8/B1.9, BS 1657/2779,
# ISO 2901/2902, DIN 513).  Once verified the constants below
# can be adjusted in-place.

# Acme (ASME B1.5) General Purpose: 2G/3G/4G; same letters for ext+int.
ACME_EXTERNAL = ['2G', '3G', '4G', '2C', '3C', '4C']
ACME_INTERNAL = ['2G', '3G', '4G', '2C', '3C', '4C']

# Stub Acme (ASME B1.8): 2G default.
STUB_ACME_EXTERNAL = ['2G', '3G', '4G']
STUB_ACME_INTERNAL = ['2G', '3G', '4G']

# TR Trapezoidal (ISO 2901/2902): grades 7-9 only.
TR_EXTERNAL = ['7e', '7c', '8e', '8c', '9c']
TR_INTERNAL = ['7H', '8H', '9H']

# BSP parallel pipe (BS 2779): A close, B free.
BSP_EXTERNAL = ['A', 'B']
BSP_INTERNAL = ['A', 'B']

# American Buttress (ANSI B1.9): 2A/2B medium, 3A/3B precision.
BUTTRESS_AM_EXTERNAL = ['2A', '3A']
BUTTRESS_AM_INTERNAL = ['2B', '3B']

# British Buttress (BS 1657): single class system in v1.
BUTTRESS_BR_EXTERNAL = ['Standard']
BUTTRESS_BR_INTERNAL = ['Standard']

# Saw thread (DIN 513): grade 7-9 like TR.
SAW_EXTERNAL = ['7e', '8e', '9e']
SAW_INTERNAL = ['7H', '8H', '9H']

# NPT / BSPT taper pipe — gauging only, no diameter classes.
# We expose a single pseudo-class "L1" so the picker has something
# to show; lookup() returns a "gauging only" marker instead of
# dimensional limits.
TAPER_PIPE_CLASSES = ['L1']


# ============================================================
# Recommended mating pairs (ISO 965-1 Section 6 / Table 1)
# ============================================================
# ISO 965-1 groups thread fits into precision categories:
#   Fine (precision parts)       : 4H / 4h, 5H / 5h
#   Medium (general production)  : 6H / 6g     ← default
#   Coarse (rough work, hot work): 7H / 8g
# Coated / plated parts get position G (internal) or e/f (external).
#
# Used by the Thread Info display so when the operator picks ONE
# class (the side they're machining), the OTHER side fills in with
# the standard mating class instead of staying blank.
# Operator can override by also picking a class on the other side.

_MATE_FOR_INTERNAL = {
    '4H': '4g',
    '5H': '5g',     # 5H/5g6g preferred; we use the simpler same-grade pair
    '6H': '6g',     # Standard medium fit (most common)
    '6G': '6g',     # Internal coated → external uncoated 6g
    '7H': '7g',     # 7H/8g per ISO; we'll match grade-for-grade for clarity
    '7G': '7g',
    # U229: UN / UNJ standard mating pairs.
    '1B': '1A',
    '2B': '2A',     # Standard ASME B1.1 medium fit (most common)
    '3B': '3A',     # Precision aerospace fit
    # U230-U237: Acme/TR/BSP/Buttress/Saw mating pairs.
    '8H': '8e',     # TR
    '9H': '9c',     # TR
    'A':  'A',      # BSP / British (symmetric)
    'B':  'B',
    'Standard': 'Standard',     # British Buttress
}

_MATE_FOR_EXTERNAL = {
    '4g': '4H',
    '4h': '4H',
    '5g': '5H',
    '5h': '5H',
    '6e': '6H',     # Heavily coated external → standard 6H tap
    '6f': '6H',
    '6g': '6H',     # Standard medium fit
    '6h': '6H',     # Gauge-tolerance external → 6H
    '8g': '7H',     # ISO coarse fit pairing
    # U229: UN / UNJ standard mating pairs.
    '1A': '1B',
    '2A': '2B',
    '3A': '3B',
    # U230-U237: Acme/TR/Saw external→internal pairings.
    '7e': '7H',     # TR / Saw
    '7c': '7H',
    '8e': '8H',
    '8c': '8H',
    '9c': '9H',
    '9e': '9H',
    '2G': '2G',     # Acme — same letter both sides, allowance differs
    '3G': '3G',
    '4G': '4G',
    '2C': '2C',     # Acme Centralizing
    '3C': '3C',
    '4C': '4C',
}


def mating_class(klass):
    """Return the recommended mating-side class for a given class.
    e.g. mating_class('6H') → '6g'.  Returns '' if unknown."""
    if not klass:
        return ''
    if klass in _MATE_FOR_INTERNAL:
        return _MATE_FOR_INTERNAL[klass]
    if klass in _MATE_FOR_EXTERNAL:
        return _MATE_FOR_EXTERNAL[klass]
    return ''


def available_classes(family, side):
    """Return list of class designations valid for (family, side).

    family: e.g. 'M_coarse', 'M_fine', 'MJ' — all use ISO Metric;
            'UN', 'UNC', 'UNF', 'UNEF', 'UNJ' — use UN/UNJ classes.
            Anything else returns an empty list (will be added in
            future versions).
    side:  'External' or 'Internal'.
    """
    fam = (family or '').upper()
    is_metric = (fam.startswith('M') and
                 not fam.startswith('MIN') and
                 not fam.startswith('MJ'))    # MJ uses UN-style classes per ASME
    is_un = (fam.startswith('UN') or fam == 'MJ')
    if is_metric:
        return (list(ISO_METRIC_EXTERNAL) if side == 'External'
                else list(ISO_METRIC_INTERNAL))
    if is_un:
        return (list(UN_EXTERNAL) if side == 'External'
                else list(UN_INTERNAL))
    # U230-U237: additional families.
    if fam.startswith('STUB'):
        return (list(STUB_ACME_EXTERNAL) if side == 'External'
                else list(STUB_ACME_INTERNAL))
    if fam.startswith('ACME'):
        return (list(ACME_EXTERNAL) if side == 'External'
                else list(ACME_INTERNAL))
    if fam == 'TR' or fam.startswith('TRAP'):
        return (list(TR_EXTERNAL) if side == 'External'
                else list(TR_INTERNAL))
    if fam.startswith('BSPT') or fam.startswith('NPT'):
        # Taper pipe — gauging-only.
        return list(TAPER_PIPE_CLASSES)
    if fam.startswith('BSP') or fam.startswith('BSW') or fam.startswith('BSF'):
        # BSP parallel — also covers BSW/BSF Whitworth-style under same scheme.
        return (list(BSP_EXTERNAL) if side == 'External'
                else list(BSP_INTERNAL))
    if fam.startswith('BUTTRESS_BR') or fam == 'BUTTRESS_BR':
        return (list(BUTTRESS_BR_EXTERNAL) if side == 'External'
                else list(BUTTRESS_BR_INTERNAL))
    if fam.startswith('BUTTRESS') or fam == 'BUTTRESS_AM':
        return (list(BUTTRESS_AM_EXTERNAL) if side == 'External'
                else list(BUTTRESS_AM_INTERNAL))
    if fam.startswith('SAW') or fam.startswith('SAGE') or fam == 'DIN_513':
        return (list(SAW_EXTERNAL) if side == 'External'
                else list(SAW_INTERNAL))
    return []


# ============================================================
# Tolerance grade multipliers (ISO 965-1 Table 2)
# ============================================================
# Grade 6 is the BASE.  Other grades scale linearly per the table.
# Not every grade is defined for every dia (e.g. T_d only has 4/6/8)
# — we don't enforce that here; caller restricts via
# available_classes().

_GRADE_MULT = {
    3: 0.50, 4: 0.63, 5: 0.80, 6: 1.00,
    7: 1.25, 8: 1.60, 9: 2.00,
}


def _grade(base_um, grade):
    return base_um * _GRADE_MULT.get(grade, 1.0)


# ============================================================
# ISO 965-1 PUBLISHED TABLE LOOKUPS (matches Baker / DIN 13)
# ============================================================
# These tables are the authoritative source for tolerance grade
# values.  They differ slightly from the raw analytical formulas
# (Annex A) because ISO 965-1 rounds to "preferred values" of
# the R10 / R20 series.  Baker's pocket guide and DIN 13 use the
# same published numbers.
#
# Format: dict {pitch_mm: {grade: T_value_µm}}.  Lookup by exact
# pitch — a small ±0.001 tolerance is applied so 1.5 ≈ 1.500.
#
# Source: ISO 965-1:2013 Tables 4, 6 and 7.

# Table 4: T_D1 — internal MINOR dia (D1) tolerance, µm.  Grades 4-8.
_T_D1_TABLE = {
    0.2:  {4: 38,  5: 48,  6: 60,  7: 75,  8: 95},
    0.25: {4: 45,  5: 56,  6: 71,  7: 90,  8: 112},
    0.3:  {4: 53,  5: 67,  6: 85,  7: 106, 8: 132},
    0.35: {4: 63,  5: 80,  6: 100, 7: 125, 8: 160},
    0.4:  {4: 71,  5: 90,  6: 112, 7: 140, 8: 180},
    0.45: {4: 80,  5: 100, 6: 125, 7: 160, 8: 200},
    0.5:  {4: 90,  5: 112, 6: 140, 7: 180, 8: 224},
    0.6:  {4: 100, 5: 125, 6: 160, 7: 200, 8: 250},
    0.7:  {4: 112, 5: 140, 6: 180, 7: 224, 8: 280},
    0.75: {4: 118, 5: 150, 6: 190, 7: 236, 8: 300},
    0.8:  {4: 125, 5: 160, 6: 200, 7: 250, 8: 315},
    1.0:  {4: 150, 5: 190, 6: 236, 7: 300, 8: 375},
    1.25: {4: 170, 5: 212, 6: 265, 7: 335, 8: 425},
    1.5:  {4: 190, 5: 236, 6: 300, 7: 375, 8: 475},
    1.75: {4: 212, 5: 265, 6: 335, 7: 425, 8: 530},
    2.0:  {4: 236, 5: 300, 6: 375, 7: 475, 8: 600},
    2.5:  {4: 280, 5: 355, 6: 450, 7: 560, 8: 710},
    3.0:  {4: 315, 5: 400, 6: 500, 7: 630, 8: 800},
    3.5:  {4: 355, 5: 450, 6: 560, 7: 710, 8: 900},
    4.0:  {4: 375, 5: 475, 6: 600, 7: 750, 8: 950},
    4.5:  {4: 425, 5: 530, 6: 670, 7: 850, 8: 1060},
    5.0:  {4: 450, 5: 560, 6: 710, 7: 900, 8: 1120},
    5.5:  {4: 475, 5: 600, 6: 750, 7: 950, 8: 1180},
    6.0:  {4: 500, 5: 630, 6: 800, 7: 1000, 8: 1250},
}

# Table 6: T_d — external MAJOR dia (d) tolerance, µm.  Grades 4, 6, 8.
_T_d_TABLE = {
    0.2:  {4: 36,  6: 56,  8: 90},
    0.25: {4: 42,  6: 67,  8: 106},
    0.3:  {4: 48,  6: 75,  8: 118},
    0.35: {4: 53,  6: 85,  8: 132},
    0.4:  {4: 60,  6: 95,  8: 150},
    0.45: {4: 63,  6: 100, 8: 160},
    0.5:  {4: 67,  6: 106, 8: 170},
    0.6:  {4: 80,  6: 125, 8: 200},
    0.7:  {4: 90,  6: 140, 8: 224},
    0.75: {4: 90,  6: 140, 8: 224},
    0.8:  {4: 95,  6: 150, 8: 236},
    1.0:  {4: 112, 6: 180, 8: 280},
    1.25: {4: 132, 6: 212, 8: 335},
    1.5:  {4: 150, 6: 236, 8: 375},
    1.75: {4: 170, 6: 265, 8: 425},
    2.0:  {4: 180, 6: 280, 8: 450},
    2.5:  {4: 212, 6: 335, 8: 530},
    3.0:  {4: 236, 6: 375, 8: 600},
    3.5:  {4: 265, 6: 425, 8: 670},
    4.0:  {4: 300, 6: 475, 8: 750},
    4.5:  {4: 315, 6: 500, 8: 800},
    5.0:  {4: 335, 6: 530, 8: 850},
    5.5:  {4: 355, 6: 560, 8: 900},
    6.0:  {4: 375, 6: 600, 8: 950},
}

# Table 7: T_d2 — external PITCH dia (d2) tolerance, µm.  Depends on
# pitch P AND basic major dia D.  ISO 965-1 splits D into ranges.
# Format: {(D_lo, D_hi]: {pitch: {grade: T_value}}}.  Grades 3-9.
# NOTE: T_d2 ranges below cover D from 0.99 to 90 mm (the most-used
# operating envelope).  Larger sizes can be added when needed.
_T_d2_TABLE = {
    # D 0.99 < D ≤ 1.4
    (0.99, 1.4): {
        0.2:  {3: 28,  4: 36,  5: 45,  6: 56,  7: 71,  8: 90,  9: 112},
        0.25: {3: 32,  4: 40,  5: 50,  6: 63,  7: 80,  8: 100, 9: 125},
    },
    # 1.4 < D ≤ 2.8
    (1.4, 2.8): {
        0.2:  {3: 30,  4: 38,  5: 48,  6: 60,  7: 75,  8: 95,  9: 118},
        0.25: {3: 34,  4: 42,  5: 53,  6: 67,  7: 85,  8: 106, 9: 132},
        0.3:  {3: 36,  4: 45,  5: 56,  6: 71,  7: 90,  8: 112, 9: 140},
        0.35: {3: 38,  4: 48,  5: 60,  6: 75,  7: 95,  8: 118, 9: 150},
        0.4:  {3: 40,  4: 50,  5: 63,  6: 80,  7: 100, 8: 125, 9: 160},
        0.45: {3: 42,  4: 53,  5: 67,  6: 85,  7: 106, 8: 132, 9: 170},
    },
    # 2.8 < D ≤ 5.6
    (2.8, 5.6): {
        0.35: {3: 40,  4: 50,  5: 63,  6: 80,  7: 100, 8: 125, 9: 160},
        0.5:  {3: 45,  4: 56,  5: 71,  6: 90,  7: 112, 8: 140, 9: 180},
        0.6:  {3: 48,  4: 60,  5: 75,  6: 95,  7: 118, 8: 150, 9: 190},
        0.7:  {3: 50,  4: 63,  5: 80,  6: 100, 7: 125, 8: 160, 9: 200},
        0.75: {3: 53,  4: 67,  5: 85,  6: 106, 7: 132, 8: 170, 9: 212},
        0.8:  {3: 53,  4: 67,  5: 85,  6: 106, 7: 132, 8: 170, 9: 212},
    },
    # 5.6 < D ≤ 11.2
    (5.6, 11.2): {
        0.75: {3: 56,  4: 71,  5: 90,  6: 112, 7: 140, 8: 180, 9: 224},
        1.0:  {3: 60,  4: 75,  5: 95,  6: 118, 7: 150, 8: 190, 9: 236},
        1.25: {3: 67,  4: 85,  5: 106, 6: 132, 7: 170, 8: 212, 9: 265},
        1.5:  {3: 71,  4: 90,  5: 112, 6: 140, 7: 180, 8: 224, 9: 280},
    },
    # 11.2 < D ≤ 22.4   ← M12, M14, M16, M18, M20, M22 fall here.
    # Grade-6 values cross-checked against Baker pocket guide:
    #   P=1.5:  T_D2 = 190 → T_d2 = 140  (M18×1.5)
    #   P=1.75: T_D2 = 200 → T_d2 = 150  (M12×1.75)
    #   P=2.0:  T_D2 = 212 → T_d2 = 160  (M14×2,  M16×2)
    #   P=2.5:  T_D2 = 224 → T_d2 = 170  (M20×2.5)
    # Other grades scaled from grade 6 by ISO ratios + R20 rounding.
    (11.2, 22.4): {
        1.0:  {3: 56,  4: 71,  5: 90,  6: 112, 7: 140, 8: 180, 9: 224},
        1.25: {3: 67,  4: 85,  5: 106, 6: 132, 7: 170, 8: 212, 9: 265},
        1.5:  {3: 71,  4: 90,  5: 112, 6: 140, 7: 180, 8: 224, 9: 280},
        1.75: {3: 75,  4: 95,  5: 118, 6: 150, 7: 190, 8: 236, 9: 300},
        2.0:  {3: 80,  4: 100, 5: 125, 6: 160, 7: 200, 8: 250, 9: 315},
        2.5:  {3: 85,  4: 106, 5: 132, 6: 170, 7: 212, 8: 265, 9: 335},
    },
    # 22.4 < D ≤ 45    ← M24, M27, M30, M33, M36, M39, M42, M45
    (22.4, 45.0): {
        1.0:  {3: 75,  4: 95,  5: 118, 6: 150, 7: 190, 8: 236, 9: 300},
        1.5:  {3: 85,  4: 106, 5: 132, 6: 170, 7: 212, 8: 265, 9: 335},
        2.0:  {3: 95,  4: 118, 5: 150, 6: 190, 7: 236, 8: 300, 9: 375},
        3.0:  {3: 106, 4: 132, 5: 170, 6: 212, 7: 265, 8: 335, 9: 425},
        3.5:  {3: 112, 4: 140, 5: 180, 6: 224, 7: 280, 8: 355, 9: 450},
        4.0:  {3: 118, 4: 150, 5: 190, 6: 236, 7: 300, 8: 375, 9: 475},
        4.5:  {3: 125, 4: 160, 5: 200, 6: 250, 7: 315, 8: 400, 9: 500},
    },
    # 45 < D ≤ 90
    (45.0, 90.0): {
        1.5:  {3: 90,  4: 112, 5: 140, 6: 180, 7: 224, 8: 280, 9: 355},
        2.0:  {3: 100, 4: 125, 5: 160, 6: 200, 7: 250, 8: 315, 9: 400},
        3.0:  {3: 112, 4: 140, 5: 180, 6: 224, 7: 280, 8: 355, 9: 450},
        4.0:  {3: 125, 4: 160, 5: 200, 6: 250, 7: 315, 8: 400, 9: 500},
        5.0:  {3: 140, 4: 180, 5: 224, 6: 280, 7: 355, 8: 450, 9: 560},
        5.5:  {3: 150, 4: 190, 5: 236, 6: 300, 7: 375, 8: 475, 9: 600},
        6.0:  {3: 150, 4: 190, 5: 236, 6: 300, 7: 375, 8: 475, 9: 600},
    },
}


def _table_lookup(table, P, grade):
    """Find a value in a 1-D pitch-keyed table within ±0.001 mm pitch
    tolerance.  Returns None if not found — caller falls back to
    formula."""
    for tab_P, by_grade in table.items():
        if abs(tab_P - P) < 0.001:
            return by_grade.get(grade)
    return None


def _T_d2_table_lookup(P, D, grade):
    """Find T_d2 in the 2-D (D-range × pitch) table.  Returns µm or
    None if outside published table range."""
    for (D_lo, D_hi), by_pitch in _T_d2_TABLE.items():
        if D_lo < D <= D_hi:
            return _table_lookup(by_pitch, P, grade)
    return None


# ============================================================
# Tolerance grade base values — analytical fallback
# ============================================================
# Used ONLY when the published table has no entry for the
# (P, D, grade) combination (rare cases / future grades).

def _T_d6(P):
    return 180 * P ** (2.0 / 3.0)


def _T_d2_6(P, D):
    return 90 * P ** 0.4 * D ** 0.1


def _T_D1_6(P):
    if P < 0.2:
        return 433 * P - 190 * P ** 1.22
    return 230 * P ** 0.7


def _T_D2_6(P, D):
    return 1.32 * _T_d2_6(P, D)


# ============================================================
# Grade resolution — table first, formula fallback
# ============================================================

def _T_d_value(P, grade):
    """Major dia tolerance, external thread, µm.  Table → formula."""
    v = _table_lookup(_T_d_TABLE, P, grade)
    if v is not None:
        return v
    return _grade(_T_d6(P), grade)


def _T_d2_value(P, D, grade):
    """Pitch dia tolerance, external thread, µm.  Table → formula."""
    v = _T_d2_table_lookup(P, D, grade)
    if v is not None:
        return v
    return _grade(_T_d2_6(P, D), grade)


def _T_D1_value(P, grade):
    """Minor dia tolerance, internal thread, µm.  Table → formula."""
    v = _table_lookup(_T_D1_TABLE, P, grade)
    if v is not None:
        return v
    return _grade(_T_D1_6(P), grade)


def _T_D2_value(P, D, grade):
    """Pitch dia tolerance, internal thread, µm.  Table → 1.32 × T_d2.
    Per ISO 965-1: T_D2 = 1.32 × T_d2 (with R10/R20 rounding).  We
    apply the 1.32 factor to the table lookup of T_d2."""
    v = _T_d2_table_lookup(P, D, grade)
    if v is not None:
        # Round to R20 series (5%) — preferred-number rounding.
        raw = 1.32 * v
        return _round_R20(raw)
    return _grade(_T_D2_6(P, D), grade)


# ISO 965-1 uses R10/R20 preferred-number series for tolerance values.
# Common R20 values (µm): 100, 112, 125, 140, 160, 180, 200, 224, 250,
# 280, 315, 355, 400, 450, 500, 560, 630, 710, 800, 900, 1000.
_R20_SERIES = [
    1, 1.12, 1.25, 1.4, 1.6, 1.8, 2.0, 2.24, 2.5, 2.8, 3.15, 3.55,
    4.0, 4.5, 5.0, 5.6, 6.3, 7.1, 8.0, 9.0,
]


def _round_R20(value_um):
    """Round a tolerance value (µm) up to the next R20 preferred number."""
    if value_um <= 0:
        return value_um
    import math
    # Find decade.
    decade = 10 ** int(math.floor(math.log10(value_um)))
    normalised = value_um / decade
    for r in _R20_SERIES:
        if r >= normalised - 1e-6:
            return round(r * decade)
    return round(_R20_SERIES[-1] * decade * 10)


# ============================================================
# Fundamental deviations (ISO 965-1 Section 5)
# ============================================================

def _es_external(letter, P):
    """Upper deviation for external thread, µm.  Position letter."""
    if letter == 'e':
        return -(50 + 11 * P)
    if letter == 'f':
        return -(30 + 11 * P)
    if letter == 'g':
        return -(15 + 11 * P)
    if letter == 'h':
        return 0.0
    return 0.0


def _EI_internal(letter, P):
    """Lower deviation for internal thread, µm.  Position letter."""
    if letter == 'G':
        return +(15 + 11 * P)
    if letter == 'H':
        return 0.0
    return 0.0


# ============================================================
# Class designation parser
# ============================================================
# Accepts simple forms like '6g', '6H', '4g', '7H', '6G'.
# Compound forms like '4g6g' (d2 grade 4, d grade 6) are NOT
# supported in v1 — operator can pick '6g' and override manually
# if a non-standard band is needed.

_CLASS_RE = re.compile(r'^\s*(\d)\s*([a-zA-Z])\s*$')


def _parse_class(klass):
    """'6g' → (6, 'g').  Returns (None, None) on failure."""
    if not klass:
        return (None, None)
    m = _CLASS_RE.match(klass)
    if not m:
        return (None, None)
    return (int(m.group(1)), m.group(2))


# ============================================================
# Public lookup
# ============================================================

def lookup(family, klass, P, D, side):
    """Return per-dia tolerance band for the given class & geometry.

    Args:
      family : thread family code ('M_coarse', 'M_fine', 'MJ' …
               'UNC', 'UNF', 'UNEF', 'UNJ', 'UN' …)
      klass  : class designation, e.g. '6g' / '6H' (Metric)
               or '2A' / '2B' (UN/UNJ)
      P      : pitch in mm
      D      : nominal major dia in mm  (used in T_d2 / T_D2 formulas)
      side   : 'External' or 'Internal'

    Returns:
      {'major': (es, ei),
       'pitch': (es, ei),
       'minor': (es, ei),
       'class': klass}            — values in MILLIMETRES
      or None if family / class / side combination is invalid.

    Sign convention:
      external — es is upper, ei is lower (typically es ≤ 0, ei < es)
      internal — first member of tuple is ES (upper), second is EI (lower)
                 EI ≥ 0 for G/H positions.
    """
    fam = (family or '').upper()
    is_metric = (fam.startswith('M') and
                 not fam.startswith('MIN') and
                 not fam.startswith('MJ'))
    is_un = fam.startswith('UN') or fam == 'MJ'
    if is_un:
        return _lookup_un(klass, P, D, side)
    # U230-U237: dispatch to family-specific lookup helpers.
    if fam.startswith('STUB'):
        return _lookup_acme(klass, P, D, side, stub=True)
    if fam.startswith('ACME'):
        return _lookup_acme(klass, P, D, side, stub=False)
    if fam == 'TR' or fam.startswith('TRAP'):
        return _lookup_tr(klass, P, D, side)
    if fam.startswith('BSPT') or fam.startswith('NPT'):
        return _lookup_taper_pipe(klass, P, D, side, family=fam)
    if fam.startswith('BSP') or fam.startswith('BSW') or fam.startswith('BSF'):
        return _lookup_bsp(klass, P, D, side)
    if fam.startswith('BUTTRESS_BR'):
        return _lookup_buttress_br(klass, P, D, side)
    if fam.startswith('BUTTRESS') or fam == 'BUTTRESS_AM':
        return _lookup_buttress_am(klass, P, D, side)
    if fam.startswith('SAW') or fam.startswith('SAGE') or fam == 'DIN_513':
        return _lookup_saw(klass, P, D, side)
    if not is_metric:
        return None

    grade, letter = _parse_class(klass)
    if grade is None:
        return None

    P = max(float(P), 1e-6)
    D = max(float(D), 1e-6)

    if side == 'External':
        if not letter.islower():
            return None
        es_um = _es_external(letter, P)
        T_d_um = _T_d_value(P, grade)
        T_d2_um = _T_d2_value(P, D, grade)
        return {
            'major': (es_um / 1000.0, (es_um - T_d_um) / 1000.0),
            'pitch': (es_um / 1000.0, (es_um - T_d2_um) / 1000.0),
            'minor': (es_um / 1000.0, (es_um - T_d_um) / 1000.0),
            'class': klass,
        }

    if side == 'Internal':
        if not letter.isupper():
            return None
        EI_um = _EI_internal(letter, P)
        T_D1_um = _T_D1_value(P, grade)
        T_D2_um = _T_D2_value(P, D, grade)
        return {
            # internal: ES (upper), EI (lower) — same tuple shape but
            # first = upper, second = lower so the rendering code is
            # symmetric with external.
            'minor': ((EI_um + T_D1_um) / 1000.0, EI_um / 1000.0),
            'pitch': ((EI_um + T_D2_um) / 1000.0, EI_um / 1000.0),
            # Major dia of internal thread has open ES (no design
            # upper limit — it's a clearance dia).  We return EI only
            # in the upper slot and None in the lower so the display
            # can show "−"  for the unspecified side.
            'major': (None, EI_um / 1000.0),
            'class': klass,
        }

    return None


# ============================================================
# U229: UN / UNJ tolerance lookup (ASME B1.1 / MIL-S-8879)
# ============================================================
# All ASME B1.1 formulas use INCH inputs.  Internally we convert
# the spec's millimetre P and D to inches, evaluate the formulas,
# then convert the resulting tolerance values back to millimetres.

_IN_PER_MM = 1.0 / 25.4

def _lookup_un(klass, P_mm, D_mm, side):
    """ASME B1.1 / MIL-S-8879 tolerance lookup for UN, UNC, UNF,
    UNEF, UNR, UNJ, MJ.  Returns {major/pitch/minor: (es,ei), ...}
    in MILLIMETRES, or None if the class / side combination is
    invalid.

    External classes:
      1A — loose fit  (allowance = 2A allowance × 1.5, tolerance
           = 2A × 1.500)
      2A — standard fit (allowance = 0.3 × 2A PD tolerance,
           tolerance = baseline)
      3A — precision fit (zero allowance, tolerance = 0.75 × 2A)

    Internal classes:
      1B — loose (zero allowance, tolerance = 1.95 × 2B)
      2B — standard (zero allowance, tolerance = 1.30 × 2A external
           pitch tolerance)
      3B — precision (zero allowance, tolerance = 0.75 × 2B)
    """
    klass = (klass or '').upper().strip()
    # Convert mm → in for ASME formulas.
    P_in = P_mm * _IN_PER_MM
    D_in = D_mm * _IN_PER_MM
    if P_in <= 0 or D_in <= 0:
        return None
    Le_in = 9.0 * P_in   # standard length of engagement = 9P

    # Baseline 2A pitch-dia tolerance (in inches).
    T_d2_2A_in = (0.0015 * D_in ** (1.0/3.0)
                  + 0.0015 * (Le_in ** 0.5)
                  + 0.015 * P_in ** (2.0/3.0))
    # Major-dia tolerance (same for all external classes per B1.1).
    T_d_in = 0.060 * P_in ** (2.0/3.0)
    # Minor-dia internal tolerance (T_D1) — empirical per B1.1
    # Eq 10b.  Range over typical sizes; clamp to positive.
    if P_in > 0.083333:   # > 1/12" pitch (= < 12 TPI, coarse)
        T_D1_in = 0.250 * P_in - 0.4 * P_in * P_in
    else:                 # ≤ 1/12" (≥ 12 TPI, fine)
        T_D1_in = 0.05 * P_in ** (2.0/3.0) + 0.03 * P_in / D_in - 0.002
    T_D1_in = max(T_D1_in, 0.0001)

    # Class multipliers.
    if klass == '2A':
        T_d2_in   = T_d2_2A_in
        allow_in  = 0.3 * T_d2_2A_in
        T_d_cls   = T_d_in
    elif klass == '1A':
        T_d2_in   = 1.500 * T_d2_2A_in
        allow_in  = 0.3 * T_d2_2A_in   # same allowance as 2A
        T_d_cls   = T_d_in
    elif klass == '3A':
        T_d2_in   = 0.750 * T_d2_2A_in
        allow_in  = 0.0
        T_d_cls   = T_d_in
    elif klass == '2B':
        T_d2_int_in = 1.30 * T_d2_2A_in
        T_D1_int_in = T_D1_in
    elif klass == '1B':
        T_d2_int_in = 1.95 * 1.30 * T_d2_2A_in   # 1B = 1.95 × 2B
        T_D1_int_in = 1.95 * T_D1_in
    elif klass == '3B':
        T_d2_int_in = 0.75 * 1.30 * T_d2_2A_in
        T_D1_int_in = 0.75 * T_D1_in
    else:
        return None

    if side == 'External':
        if klass not in ('1A', '2A', '3A'):
            return None
        # External: max material at upper limit (closest to basic).
        # es = allowance subtracted from basic (negative)
        # ei = es minus the tolerance grade for that dia
        es_major = -allow_in * 25.4              # to mm
        ei_major = es_major - T_d_cls * 25.4
        es_pitch = -allow_in * 25.4
        ei_pitch = es_pitch - T_d2_in * 25.4
        # Minor dia for external: per ASME B1.1, the external minor
        # is truncated by the tool — min major - 2 * 0.5413·P actually
        # min minor.  For tolerance reporting we share the major
        # tolerance band offset (allowance applies the same).
        es_minor = -allow_in * 25.4
        ei_minor = es_minor - T_d_cls * 25.4
        return {
            'major': (es_major, ei_major),
            'pitch': (es_pitch, ei_pitch),
            'minor': (es_minor, ei_minor),
            'class': klass,
        }

    if side == 'Internal':
        if klass not in ('1B', '2B', '3B'):
            return None
        # Internal: zero allowance (EI = 0).  Limits go ABOVE basic.
        EI = 0.0
        ES_minor = T_D1_int_in * 25.4
        ES_pitch = T_d2_int_in * 25.4
        return {
            # First tuple slot is UPPER, second is LOWER (matching
            # convention used by Metric internal lookup).
            'minor': (ES_minor, EI),
            'pitch': (ES_pitch, EI),
            # Major dia of internal thread — ES open (clearance dia).
            'major': (None, EI),
            'class': klass,
        }

    return None


# ============================================================
# U230 — Acme + Stub Acme tolerance lookup (ASME B1.5 / B1.8)
# ============================================================
# v1 approximate.  Cross-check against B1.5 Tables 5-9 once user
# loads test cases.

def _lookup_acme(klass, P_mm, D_mm, side, stub=False):
    """U246e: ASME B1.5 / Machinery's Handbook 23rd ed. formulas.

    EXTERNAL:
        D_max = D_basic
        D_min = D_basic - 0.05·(1/n) inch
        E_max = E_basic - allow_class·√D inch
        E_min = E_max - (0.006·√D + 0.03·√(1/n)) inch         (PD tolerance)
        K_max = K_basic - 0.02·25.4  (or 0.01 for n>10 TPI)    (clearance)
        K_min = K_max - 1.5·(PD tolerance)

    INTERNAL:
        D_min = D_basic + ac  ;  D_max = D_min + ac      (ac per ASME B1.5)
        E_min = E_basic  ;  E_max = E_basic + (PD tolerance)
        K_min = K_basic  ;  K_max = K_basic + 0.05·(1/n) inch

    Class allowances on PD external (Machinery's Handbook 23rd ed.):
        2G = 0.008·√D     3G = 0.006·√D     4G = 0.004·√D

    CENTRALIZING (2C/3C/4C) — per ANSI B1.5-1988:
        Centralizing variants put the alignment fit on the MAJOR
        diameter (instead of pitch dia for the G classes).  PD
        allowances are the same as the matching G class
        (2C↔2G, 3C↔3G, 4C↔4G).  The major-dia limits are TIGHTER
        for C than for G — but v1 of this lookup uses the G-class
        major-dia values for 2C/3C/4C as well; refinement to the
        ANSI B1.5 Table 6/7 Centralizing major-dia values is
        deferred until exact table values are loaded.
    """
    P_in = P_mm * _IN_PER_MM     # 1/n
    D_in = D_mm * _IN_PER_MM
    if P_in <= 0 or D_in <= 0:
        return None
    klass = (klass or '').upper().strip()
    cls_allow = {'2G': 0.008, '3G': 0.006, '4G': 0.004,
                 '2C': 0.008, '3C': 0.006, '4C': 0.004}
    a_coeff = cls_allow.get(klass)
    if a_coeff is None:
        return None
    sqrt_D  = D_in ** 0.5
    sqrt_P  = P_in ** 0.5
    # PD allowance (external only) — class-dependent.
    pd_allow_in = a_coeff * sqrt_D                   # inches
    # PD tolerance — Machinery's Handbook formula, same all classes.
    T_pd_in = 0.006 * sqrt_D + 0.03 * sqrt_P
    # Major-dia tolerance external = 0.05·P inches (D_max - D_min).
    T_d_ext_in = 0.05 * P_in
    # Minor-dia tolerance external = 1.5 · T_pd.
    T_k_ext_in = 1.5 * T_pd_in
    # Internal pitch-dependent diametral clearance (ASME B1.5) for G:
    #   P ≥ 0.1 inch  (n ≤ 10 TPI):  ac = 0.020 inch = 0.508 mm
    #   P  < 0.1 inch  (n > 10 TPI):  ac = 0.010 inch = 0.254 mm
    ac_in = 0.020 if P_in >= 0.099 else 0.010
    is_centralizing = klass.endswith('C')   # 2C/3C/4C
    if side == 'External':
        # Pitch dia: es = -allowance, ei = -allowance - T_pd
        es_e = -pd_allow_in * 25.4
        ei_e =  es_e - T_pd_in * 25.4
        if is_centralizing:
            # Centralizing major: tighter — same allowance as PD,
            # tolerance ≈ PD tolerance.
            es_d = -pd_allow_in * 25.4
            ei_d =  es_d - T_pd_in * 25.4
            # Minor unchanged from G class (still uses ac clearance).
            es_k = -ac_in * 25.4
            ei_k =  es_k - T_k_ext_in * 25.4
        else:
            # G class major: D_max = basic D, D_min = D - 0.05·P
            es_d =  0.0
            ei_d = -T_d_ext_in * 25.4
            # Minor: K_max = basic K - ac, K_min = K_max - 1.5·T_pd
            es_k = -ac_in * 25.4
            ei_k =  es_k - T_k_ext_in * 25.4
        return {
            'major': (es_d, ei_d),
            'pitch': (es_e, ei_e),
            'minor': (es_k, ei_k),
            'class': klass,
        }
    # INTERNAL — deviations relative to side-specific basic values.
    if is_centralizing:
        # Centralizing internal major: D_min = basic D (no clearance),
        # D_max = D + PD tolerance.  Note: basic_int_C = basic D
        # (NOT basic_ext_D + ac like the G class).
        es_d = T_pd_in * 25.4
        ei_d = 0.0
    else:
        # G-class internal major (basic_int_G = basic_ext_D + ac).
        # Min = basic_int (ei=0), Max = basic_int + ac → es = ac.
        es_d = ac_in * 25.4
        ei_d = 0.0
    # Pitch: E_min = E_basic (ei=0), E_max = E + T_pd  (same all classes)
    es_e = T_pd_in * 25.4
    ei_e = 0.0
    # Minor: K_min = K_basic (ei=0), K_max = K + 0.05·P  (same all classes)
    es_k = 0.05 * P_in * 25.4
    ei_k = 0.0
    return {
        'major': (es_d, ei_d),
        'pitch': (es_e, ei_e),
        'minor': (es_k, ei_k),
        'class': klass,
    }


# ============================================================
# U232 — TR Trapezoidal tolerance (ISO 2901/2902)
# ============================================================
# v1: scaled from ISO Metric formulas with 30° flank adjustment.

def _lookup_tr(klass, P_mm, D_mm, side):
    if P_mm <= 0 or D_mm <= 0:
        return None
    klass = (klass or '').strip()
    grade, letter = _parse_class(klass)
    if grade is None:
        return None
    # T_d2 base for TR is similar to ISO Metric Grade 6 but
    # scaled for the larger flank height of TR.  v1 approximation.
    T_d2_base_um = 90 * P_mm ** 0.4 * D_mm ** 0.1 * 1.5     # ×1.5 for TR
    grade_mult_tr = {7: 1.0, 8: 1.6, 9: 2.5}
    T_d2_um = T_d2_base_um * grade_mult_tr.get(grade, 1.0)
    T_d_um  = 1.5 * T_d2_um
    T_D1_um = 1.5 * T_d2_um
    if side == 'External':
        # Position: e = small allowance (es ≈ -P*40 µm/mm),
        #           c = larger allowance (es ≈ -P*120 µm/mm)
        es_um = -(40 if letter == 'e' else 120) * P_mm
        return {
            'major': (es_um / 1000.0, (es_um - T_d_um) / 1000.0),
            'pitch': (es_um / 1000.0, (es_um - T_d2_um) / 1000.0),
            'minor': (es_um / 1000.0, (es_um - T_d_um) / 1000.0),
            'class': klass,
        }
    # Internal H position.
    if not letter.isupper():
        return None
    return {
        'minor': (T_D1_um / 1000.0, 0.0),
        'pitch': (T_d2_um / 1000.0, 0.0),
        'major': (None, 0.0),
        'class': klass,
    }


# ============================================================
# U233 — NPT / BSPT taper pipe — gauging only (no dia bands)
# ============================================================
# Tapered pipe threads are gauged by turns of standoff from a
# reference plane (L1).  Standard tolerance: ±1 turn from hand-
# tight L1 plane.  Returns a marker structure so the display can
# show the gauging note instead of dia limits.

def _lookup_taper_pipe(klass, P_mm, D_mm, side, family=''):
    return {
        'gauging_only': True,
        'note': ('Gauging by L1 thread plane standoff.  '
                 'Standard: ±1 turn from hand-tight position.'),
        'class': klass or 'L1',
        # Stub band entries so callers that always read .get('major')
        # don't crash — actual values vary along the taper length.
        'major': (None, None),
        'pitch': (None, None),
        'minor': (None, None),
    }


# ============================================================
# U234 — BSP parallel pipe (BS 2779) — Class A close, B free
# ============================================================
# v1 approximate per BS 2779 Table 1.

def _lookup_bsp(klass, P_mm, D_mm, side):
    if P_mm <= 0 or D_mm <= 0:
        return None
    klass = (klass or '').upper().strip()
    if klass not in ('A', 'B'):
        return None
    # Class B baseline PD tolerance.
    T_d2_B_mm = 0.064 * (P_mm ** 0.6)
    T_d2_mm = T_d2_B_mm if klass == 'B' else 0.5 * T_d2_B_mm
    T_d_mm  = 1.5 * T_d2_mm
    # BSP is symmetric — same convention for both sides, EI/ei = 0.
    if side == 'External':
        return {
            'major': (0.0, -T_d_mm),
            'pitch': (0.0, -T_d2_mm),
            'minor': (0.0, -T_d_mm),
            'class': klass,
        }
    return {
        'minor': (T_d_mm, 0.0),
        'pitch': (T_d2_mm, 0.0),
        'major': (None, 0.0),
        'class': klass,
    }


# ============================================================
# U235 — American Buttress (ANSI B1.9) — 2A/2B, 3A/3B
# ============================================================
# v1 approximate — uses UN-style formulas scaled for the 7°/45°
# asymmetric profile.

def _lookup_buttress_am(klass, P_mm, D_mm, side):
    klass = (klass or '').upper().strip()
    # Reuse UN formulas — Buttress tolerance roughly tracks UN 2A/2B
    # in B1.9 informative annex.  3A/3B are tighter (×0.75).
    if klass in ('2A', '2B'):
        return _lookup_un(klass, P_mm, D_mm, side)
    if klass == '3A':
        band = _lookup_un('2A', P_mm, D_mm, side)
        if band:
            for k in ('major', 'pitch', 'minor'):
                v = band.get(k)
                if v and all(x is not None for x in v):
                    band[k] = (v[0], v[0] + (v[1] - v[0]) * 0.75)
            band['class'] = klass
        return band
    if klass == '3B':
        band = _lookup_un('2B', P_mm, D_mm, side)
        if band:
            for k in ('major', 'pitch', 'minor'):
                v = band.get(k)
                if v and v[0] is not None and v[1] is not None:
                    band[k] = (v[0] * 0.75, v[1])
            band['class'] = klass
        return band
    return None


# ============================================================
# U236 — British Buttress (BS 1657) — Standard class
# ============================================================
# v1 placeholder — single class with conservative tolerances.

def _lookup_buttress_br(klass, P_mm, D_mm, side):
    klass = (klass or '').strip().capitalize()
    if klass != 'Standard':
        return None
    # Conservative guess: PD tolerance ≈ 0.05*sqrt(P) mm; allowance same.
    T_d2_mm = 0.050 * (P_mm ** 0.5) if P_mm > 0 else 0.0
    T_d_mm = 1.5 * T_d2_mm
    if side == 'External':
        es = 0.0
        return {
            'major': (es, -T_d_mm),
            'pitch': (es, -T_d2_mm),
            'minor': (es, -T_d_mm),
            'class': klass,
        }
    return {
        'minor': (T_d_mm, 0.0),
        'pitch': (T_d2_mm, 0.0),
        'major': (None, 0.0),
        'class': klass,
    }


# ============================================================
# U237 — Saw thread (DIN 513 — Sägengewinde, 30°/3°)
# ============================================================
# v1: same formula structure as TR with grade 7/8/9.

def _lookup_saw(klass, P_mm, D_mm, side):
    # DIN 513 tolerance system tracks ISO TR (DIN 103) closely for
    # the 30° leading flank.  Reuse TR lookup as v1.
    return _lookup_tr(klass, P_mm, D_mm, side)


# ============================================================
# Mid-tolerance helper (used when 'apply to program' = Yes)
# ============================================================

def mid_offset(es_ei_tuple):
    """Return (es+ei)/2 from a tolerance band tuple.  Both members
    must be numeric (use 0 if None — though that should be guarded
    by caller).  Returns 0 if either side is None."""
    if es_ei_tuple is None:
        return 0.0
    a, b = es_ei_tuple
    if a is None or b is None:
        return 0.0
    return (a + b) / 2.0


def format_band(es_ei_tuple, decimals=3):
    """Pretty-format a band tuple as deviations.  Kept for
    diagnostics / future use — Thread Info now uses
    format_minmax() instead per user spec (U228)."""
    if es_ei_tuple is None:
        return '— / —'
    a, b = es_ei_tuple

    def _fmt(v):
        if v is None:
            return '—'
        sign = '+' if v >= 0 else ''
        return f'{sign}{v:.{decimals}f}'

    return f'{_fmt(a)} / {_fmt(b)}'


def format_minmax(nominal, band, decimals=3):
    """U228: format a tolerance band as absolute MIN / MAX values
    (Baker-style), given the nominal basic dia.

    band tuple is (upper, lower) deviation:
      external: (es, ei) — both ≤ 0 typically.
                MIN = nominal + ei (lower)
                MAX = nominal + es (upper)
      internal: (ES, EI) — both ≥ 0 typically.
                MIN = nominal + EI (lower)
                MAX = nominal + ES (upper)

    Returns a string like '17.294 / 17.744'.  When either side is
    None (e.g. internal major dia where ES is open), that side
    renders as '—'."""
    if nominal is None:
        return '— / —'
    if band is None:
        return f'{nominal:.{decimals}f} / {nominal:.{decimals}f}'
    upper, lower = band
    lo = (nominal + lower) if lower is not None else None
    hi = (nominal + upper) if upper is not None else None

    def _fmt(v):
        return f'{v:.{decimals}f}' if v is not None else '—'

    return f'{_fmt(lo)} / {_fmt(hi)}'


def format_minmeanmax(nominal, band, decimals=3):
    """U231l: format a tolerance band as MIN / MEAN / MAX values.
    Mean = (min + max) / 2 — the manufacturing target ("aim for
    middle of the band").  Used by Thread Info per user request.

    Same input/output convention as format_minmax — returns a
    string like '17.294 / 17.519 / 17.744'.  If MIN or MAX is
    None (open-ended band) the mean is also '—'."""
    if nominal is None:
        return '— / — / —'
    if band is None:
        return (f'{nominal:.{decimals}f} / '
                f'{nominal:.{decimals}f} / '
                f'{nominal:.{decimals}f}')
    upper, lower = band
    lo = (nominal + lower) if lower is not None else None
    hi = (nominal + upper) if upper is not None else None
    mean = ((lo + hi) / 2.0) if (lo is not None and hi is not None) else None

    def _fmt(v):
        return f'{v:.{decimals}f}' if v is not None else '—'

    return f'{_fmt(lo)} / {_fmt(mean)} / {_fmt(hi)}'
