"""
Thread Library — comprehensive reference data for thread profiles.

Per thread, the library exposes these fields (all dims in mm, angles in degrees):

    family             - profile family code ('M', 'UNC', 'UNF', 'BSW', 'BSF',
                          'BSP', 'BSPT', 'NPT', 'NPTF', 'Acme', 'Stub_Acme',
                          'TR', 'Buttress')
    size               - human-readable size label ('M10', '1/2-13', '1/2"-14', ...)
    pitch              - axial pitch P (mm)
    major              - basic major diameter D (mm)
    minor_internal     - basic minor diameter D1 for internal thread (mm)
    minor_external     - basic minor diameter d3 for external thread (mm)
    pitch_dia          - basic pitch diameter D2 / d2 (mm)
    included_angle     - thread included angle (degrees, e.g., 60 for ISO M)
    flank_leading      - flank angle from RADIAL (= perpendicular to thread
                          axis), LEADING side (degrees).  This is the
                          STANDARD convention used by ISO 68-1, ANSI B1.1,
                          BS 84, etc. — the "flank angle" of ISO M is 30°
                          (each side of the radial line at the pitch dia).
    flank_trailing     - flank angle from RADIAL, TRAILING side (degrees)
                          For symmetric profiles both equal half-included.
                          BS Buttress: leading=7°, trailing=45° (from radial).
                          API Buttress: leading=3°, trailing=10° (from radial).
                          Sum of (leading + trailing) = included_angle.
                          To convert "from radial" → "from axis":  flank_axis
                          = 90° − flank_radial  (e.g., ISO M = 60° from axis).
    height_basic       - H, basic theoretical thread height (mm) = sin(half) · P
                          / 2 — for V-threads = √3/2 · P for 60°.  For
                          Acme / TR / Buttress, height = 0.5·P (basic).
    height_internal    - actual thread depth used to cut INTERNAL bore
                         (= (D − D1)/2) (mm)
    height_external    - actual thread depth used to cut EXTERNAL screw
                         (= (D − d3)/2) (mm)
    crest_truncation   - axial crest flat width or radius (mm).  Positive
                          number = flat (truncation depth); 'r=…' format
                          could be added later for rounded crest.
    root_radius        - root rounded radius (mm).  0 if root is a flat.
    taper_per_side     - taper from centreline (deg per side).  0 for
                          parallel; ≈ 1.7899 for NPT/BSPT (1:16).
    helix_angle        - lead helix angle at pitch diameter (deg)
                          = atan(lead / (π · pitch_dia)).  Note: for
                          single-start, lead = pitch.
    standard           - reference standard ('ISO 261', 'ANSI B1.1', etc.)
    series             - 'coarse' | 'fine' | 'extra_fine' | 'general' | …

Sources:
    - ISO Metric:   ISO 261, ISO 68-1
    - UN / UNF:     ANSI/ASME B1.1
    - BSW / BSF:    BS 84 (Whitworth)
    - BSP (G):      ISO 228-1
    - BSPT (R):     ISO 7-1
    - NPT / NPTF:   ANSI/ASME B1.20.1, B1.20.3
    - Acme:         ANSI/ASME B1.5
    - Stub Acme:    ANSI/ASME B1.8
    - TR (Metric):  DIN 103, ISO 2901
    - Buttress:     ANSI B1.9, BS 1657

Schema is field-rich so partial data still fits — fields not applicable
to a profile (e.g., taper_per_side for ISO M) are 0; fields not yet
tabulated leave the slot at None.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict, field
from typing import Optional


# ---- helpers ----

def _helix_angle(pitch: float, pitch_dia: float, num_starts: int = 1) -> float:
    """Return lead-helix angle (deg) at pitch diameter for N starts."""
    if pitch_dia <= 0:
        return 0.0
    lead = pitch * num_starts
    return math.degrees(math.atan(lead / (math.pi * pitch_dia)))


def _iso_m_minor_ext(D: float, P: float) -> float:
    """ISO 68-1 / ISO 261 external thread d3 = D − 17/12·H, H = 0.866·P.
    Equivalent to D − 1.226·P."""
    return round(D - (17.0 / 12.0) * (math.sqrt(3) / 2.0) * P, 3)


def _iso_m_minor_int(D: float, P: float) -> float:
    """ISO 68-1 internal thread D1 (basic) = D − 5/4·H = D − 1.0825·P."""
    return round(D - (5.0 / 4.0) * (math.sqrt(3) / 2.0) * P, 3)


def _iso_m_pitch_dia(D: float, P: float) -> float:
    """ISO 68-1 basic pitch dia D2 = D − 3/4·H = D − 0.6495·P."""
    return round(D - (3.0 / 4.0) * (math.sqrt(3) / 2.0) * P, 3)


def _whit_minor(D: float, P: float, factor: float = 0.6403) -> float:
    """Whitworth / BSP minor: minor = D − 2·factor·P, factor=0.6403 for
    100%-engagement basic depth (Whitworth).  Operator drill is usually
    a different value (less depth = bigger minor)."""
    return round(D - 2.0 * factor * P, 3)


def _whit_pitch_dia(D: float, P: float, factor: float = 0.6403) -> float:
    """Whitworth basic pitch dia D2 = D − factor·P (centerline of profile)."""
    return round(D - factor * P, 3)


def _acme_minor_int(D: float, P: float, clearance: float = 0.25) -> float:
    """Acme/TR internal minor = D − P − 2·clearance.  Clearance per side
    on radius (default 0.25 mm).  Total dia removal = P + 2·clearance."""
    return round(D - P - 2.0 * clearance, 3)


def _acme_pitch_dia(D: float, P: float) -> float:
    """Acme/TR basic pitch dia = D − P/2 (P/2 thread height symmetric)."""
    return round(D - P / 2.0, 3)


# ---- record type ----

@dataclass
class ThreadSpec:
    family: str
    size: str
    pitch: float
    major: float
    minor_internal: Optional[float] = None
    minor_external: Optional[float] = None
    pitch_dia: Optional[float] = None
    included_angle: float = 60.0
    flank_leading: float = 30.0
    flank_trailing: float = 30.0
    height_basic: Optional[float] = None
    height_internal: Optional[float] = None
    height_external: Optional[float] = None
    crest_truncation: Optional[float] = None
    root_radius: Optional[float] = None
    # U166: root flat width (mm) — for FLAT-rooted profiles (Acme, Stub
    # Acme, Trapezoidal, Buttress) where the root is a flat face rather
    # than a radius.  None = profile has no root flat (rounded or
    # sharp-V root).  Displayed in the Thread Info tab next to root
    # radius so operators see whichever is relevant for the profile.
    root_flat: Optional[float] = None
    taper_per_side: float = 0.0
    helix_angle: Optional[float] = None
    standard: str = ''
    series: str = ''
    notes: str = ''

    def asdict(self) -> dict:
        return asdict(self)

    def fill_derived(self) -> 'ThreadSpec':
        """Compute helix angle and any missing depths that can be derived."""
        if self.pitch_dia and self.helix_angle is None:
            self.helix_angle = round(_helix_angle(self.pitch, self.pitch_dia), 3)
        if (self.height_internal is None and self.minor_internal is not None
                and self.major):
            self.height_internal = round((self.major - self.minor_internal) / 2.0, 3)
        if (self.height_external is None and self.minor_external is not None
                and self.major):
            self.height_external = round((self.major - self.minor_external) / 2.0, 3)
        return self


# ---- builders ----

def make_iso_m(D: float, P: float, label: str = None,
               series: str = 'coarse') -> ThreadSpec:
    """Build an ISO Metric thread record (60° symmetric, ISO 68-1 / ISO 261)."""
    if label is None:
        label = f'M{D:g}' + (f'×{P:g}' if series != 'coarse' else '')
    H = round((math.sqrt(3) / 2.0) * P, 4)         # 0.866·P
    spec = ThreadSpec(
        family='M',
        size=label,
        pitch=P,
        major=D,
        minor_internal=_iso_m_minor_int(D, P),
        minor_external=_iso_m_minor_ext(D, P),
        pitch_dia=_iso_m_pitch_dia(D, P),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=H,
        crest_truncation=round(H / 8.0, 4),         # 0.108·P axial flat (crest)
        root_radius=round(H / 6.0, 4),              # ≈ 0.144·P (max for ext)
        taper_per_side=0.0,
        standard='ISO 68-1 / ISO 261',
        series=series,
    )
    return spec.fill_derived()


def make_un(label: str, tpi: float, D_inch: float,
            series: str = 'UNC') -> ThreadSpec:
    """Build a Unified Inch thread record (60° symmetric, ANSI B1.1)."""
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    H = round((math.sqrt(3) / 2.0) * P, 4)
    spec = ThreadSpec(
        family=series,
        size=label,
        pitch=P,
        major=D_mm,
        # UN basic minor for INTERNAL = D − 1.0825·P (same formula as ISO M)
        minor_internal=round(D_mm - 1.0825 * P, 3),
        # UN basic minor for EXTERNAL = D − 1.2268·P (truncated 17/24 H)
        minor_external=round(D_mm - 1.2268 * P, 3),
        pitch_dia=round(D_mm - (3.0 / 4.0) * H, 3),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=H,
        crest_truncation=round(H / 8.0, 4),
        root_radius=round(H / 6.0, 4),
        taper_per_side=0.0,
        standard='ANSI/ASME B1.1',
        series=series.lower(),
    )
    return spec.fill_derived()


def make_whit(label: str, tpi: float, D_inch: float,
              series: str = 'BSW') -> ThreadSpec:
    """Build a Whitworth (BSW/BSF) thread record (55° symmetric, BS 84).

    Whitworth has rounded crests AND rounded roots — both with the same
    radius r = 0.137329·P.  Thread height h = 0.640327·P (per side, basic).
    """
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    h = round(0.640327 * P, 4)
    r = round(0.137329 * P, 4)
    pd = round(D_mm - 0.640327 * P, 3)              # pitch dia basic
    spec = ThreadSpec(
        family=series,
        size=label,
        pitch=P,
        major=D_mm,
        minor_internal=round(D_mm - 2.0 * h, 3),
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=pd,
        included_angle=55.0,
        flank_leading=27.5, flank_trailing=27.5,
        height_basic=h,
        crest_truncation=r,                          # rounded (radius)
        root_radius=r,                               # rounded (radius)
        taper_per_side=0.0,
        standard='BS 84 (Whitworth)',
        series=series.lower(),
        notes='Crest and root both rounded with radius r=0.1373·P',
    )
    return spec.fill_derived()


def make_bsp(label: str, tpi: float, D_inch: float,
             tapered: bool = False) -> ThreadSpec:
    """ISO 228 (G, parallel pipe) or ISO 7-1 (R, BSPT tapered pipe).
    55° symmetric profile, identical to Whitworth profile (with rounded
    crests/roots).  BSPT adds 1:16 taper from centreline.
    """
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    h = round(0.640327 * P, 4)
    r = round(0.137329 * P, 4)
    pd = round(D_mm - 0.640327 * P, 3)
    family = 'BSPT' if tapered else 'BSP'
    standard = 'ISO 7-1' if tapered else 'ISO 228-1'
    spec = ThreadSpec(
        family=family,
        size=label,
        pitch=P,
        major=D_mm,
        minor_internal=round(D_mm - 2.0 * h, 3),
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=pd,
        included_angle=55.0,
        flank_leading=27.5, flank_trailing=27.5,
        height_basic=h,
        crest_truncation=r,
        root_radius=r,
        # 1:16 on diameter = ~3.5775° included taper, 1.7899° per side
        taper_per_side=(math.degrees(math.atan(1.0 / 32.0)) if tapered else 0.0),
        standard=standard,
        series='pipe',
    )
    return spec.fill_derived()


def make_npt(label: str, tpi: float, D_inch: float,
             dryseal: bool = False) -> ThreadSpec:
    """NPT (ANSI B1.20.1) or NPTF Dryseal (B1.20.3).
    60° symmetric, 1:16 taper (1.7899° per side), thread height = 0.8·P.
    Reference major (M_L1) is at the gage plane — operator places this
    at the workpiece position dictated by L1.
    """
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    h = round(0.8 * P, 4)
    family = 'NPTF' if dryseal else 'NPT'
    standard = 'ANSI/ASME B1.20.3' if dryseal else 'ANSI/ASME B1.20.1'
    pd = round(D_mm - 0.8 * P, 3)
    spec = ThreadSpec(
        family=family,
        size=label,
        pitch=P,
        major=D_mm,
        minor_internal=round(D_mm - 2.0 * h, 3),
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=pd,
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=h,
        crest_truncation=round(0.0640 * P, 4),        # truncation at crest/root
        root_radius=0.0,                              # NPT has flats, not radii
        taper_per_side=math.degrees(math.atan(1.0 / 32.0)),  # ≈ 1.7899°
        standard=standard,
        series='pipe',
        notes='Major at gage plane.  Face major shifts by L1·1/16.',
    )
    return spec.fill_derived()


def make_acme(label: str, tpi: float, D_inch: float,
              series: str = 'general') -> ThreadSpec:
    """Acme thread (ANSI B1.5).  29° included angle, symmetric.
    Thread height (basic) = 0.5·P + 0.25 mm clearance per side for fit
    (ANSI B1.5).  Crest flat = 0.3707·P (external screw, F_cs basic),
    root flat = 0.3707·P (basic, before allowance reduction).  The
    0.3707 factor comes from the 29° flank geometry at half-thread
    height: F = 0.5·P − 2·(h/2)·tan(14.5°) = 0.5·P × (1 − 0.5176)
    = 0.3707·P (where h = 0.5·P for standard Acme).
    """
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    spec = ThreadSpec(
        family='Acme',
        size=label,
        pitch=P,
        major=D_mm,
        minor_internal=_acme_minor_int(D_mm, P, clearance=0.254),
        minor_external=round(D_mm - P, 3),            # external minor (no clearance)
        pitch_dia=_acme_pitch_dia(D_mm, P),
        included_angle=29.0,
        flank_leading=14.5, flank_trailing=14.5,
        height_basic=round(0.5 * P, 4),
        crest_truncation=round(0.3707 * P, 4),        # F_cs basic (external)
        root_radius=0.0,
        # U166: Acme has a FLAT root (basic), not a radius.  Width same
        # as crest flat = 0.3707·P at the basic profile.  Real-world
        # Acme threads often add a small fillet at the root to reduce
        # stress concentration, but that's not in the basic ANSI B1.5
        # profile — it's an option per design.
        root_flat=round(0.3707 * P, 4),
        taper_per_side=0.0,
        standard='ANSI/ASME B1.5',
        series=series,
        notes='Internal minor includes 0.254 mm radial clearance per side.',
    )
    return spec.fill_derived()


def make_stub_acme(label: str, tpi: float, D_inch: float) -> ThreadSpec:
    """Stub Acme (ANSI B1.8).  Same flank as Acme (29°), height = 0.3·P
    instead of 0.5·P (= shorter, "stub" version).

    Crest flat values per ANSI B1.8 / ASME H-28:
      - F_cs basic (external/screw)  = 0.4224·P  ← used here
      - F_cn basic (internal/nut)    = 0.4030·P
    The two differ by ≈ 0.0194·P (the basic allowance).  We store the
    EXTERNAL value (0.4224·P) because it represents the full nominal
    tooth thickness at the crest line and is the more conservative
    figure when forming an internal thread (slight undercut of the
    groove rather than overcut — matches user's 'no overcut' rule).
    The 0.0194·P difference is < 0.05 mm at typical Stub Acme pitches
    and is below normal machining tolerance.

    Root flat (basic, before allowance) = 0.4030·P (internal/nut).
    Same factor as F_cn since the basic profile is symmetric about
    the pitch line and Stub Acme has no clearance at the root in the
    basic form.
    """
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    h = round(0.3 * P, 4)
    spec = ThreadSpec(
        family='Stub_Acme',
        size=label,
        pitch=P,
        major=D_mm,
        minor_internal=round(D_mm - 2.0 * h - 0.508, 3),  # +0.020"=0.508mm clearance
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=round(D_mm - h, 3),
        included_angle=29.0,
        flank_leading=14.5, flank_trailing=14.5,
        height_basic=h,
        crest_truncation=round(0.4224 * P, 4),    # F_cs basic = 0.4224·P
        root_radius=0.0,
        # U246j: Stub Acme basic profile is symmetric, so root_flat
        # = crest_flat = 0.4224·P per ANSI B1.8.  The 0.4030·P value
        # previously used was the F_cn (internal crest with allowance)
        # — that's a class-derived value, not the basic profile.
        # Class-narrowed root_flat at deepest cut is computed
        # downstream in populate_thread_info using ANSI B1.8 formulas
        # identical in form to ANSI B1.5 Acme.
        root_flat=round(0.4224 * P, 4),
        taper_per_side=0.0,
        standard='ANSI/ASME B1.8',
        series='stub',
    )
    return spec.fill_derived()


def make_tr(D: float, P: float, label: str = None) -> ThreadSpec:
    """Trapezoidal (TR) — DIN 103 / ISO 2901.  30° included angle,
    height basic = 0.5·P, internal minor = D − P − 0.5 (DIN 103 standard
    ac = 0.25 mm radial clearance per side for sizes 1.5 ≤ P ≤ 5,
    larger for bigger pitches but we use 0.25 as common case)."""
    if label is None:
        label = f'TR {D:g}×{P:g}'
    spec = ThreadSpec(
        family='TR',
        size=label,
        pitch=P,
        major=D,
        minor_internal=round(D - P - 0.5, 3),
        minor_external=round(D - P, 3),
        pitch_dia=round(D - P / 2.0, 3),
        included_angle=30.0,
        flank_leading=15.0, flank_trailing=15.0,
        height_basic=round(0.5 * P, 4),
        crest_truncation=round(0.366 * P, 4),     # 0.366·P crest flat
        root_radius=0.0,
        # U166: TR basic root flat = same factor as crest flat per
        # DIN 103 symmetric profile.  Real-world TR threads usually
        # add a small fillet at the root (Rmax = 0.5·ac per DIN 103
        # for sizes with ac=0.25mm clearance) but that's an option,
        # not the basic profile.
        root_flat=round(0.366 * P, 4),
        taper_per_side=0.0,
        standard='DIN 103 / ISO 2901',
        series='general',
        notes='Internal minor includes ac=0.25 mm radial clearance.',
    )
    return spec.fill_derived()


def make_api_rsc(label: str, D_pipe_inch: float, tpi: float,
                 ipf_taper: float, family_code: str = 'NC',
                 thread_form: str = 'V-0.040',
                 root_radius_in: float = 0.020) -> ThreadSpec:
    """API Rotary Shouldered Connection (RSC) — drill string threads.
    Used on drill pipe, drill collars, BHA components.  60° V profile
    with rounded crest AND root radius.  Heavy taper (IPF = inches per
    foot on diameter), e.g. 2 IPF = 1:6, 3 IPF = 1:4.
        family_code: 'NC' (Numbered Connection), 'REG' (Regular),
                     'IF' (Internal Flush), 'FH' (Full Hole), 'H' (Hughes)
        thread_form: 'V-0.040' / 'V-0.038R' / 'V-0.050' / 'V-0.055' / 'V-0.065'
        root_radius_in: crest/root rounding radius (inch)
    Reference: API Spec 7-1 / 7-2 / 7G — Drill String Components.
    """
    P = 25.4 / tpi
    D_mm = round(D_pipe_inch * 25.4, 4)
    r = round(root_radius_in * 25.4, 4)
    # Thread height for V-0.040: h = 0.0666" = 1.692 mm.
    # V-0.050: h = 0.0832" = 2.113 mm.  V-0.038R: h = 0.0633" = 1.608.
    height_lookup = {
        'V-0.040':  1.692,
        'V-0.038R': 1.608,
        'V-0.050':  2.113,
        'V-0.055':  2.291,
        'V-0.065':  2.769,
    }
    h = height_lookup.get(thread_form, round(0.866 * P - 2 * r, 3))
    # Taper per side (degrees from axis) = atan(IPF / 24) since IPF is
    # inches per foot on DIAMETER (= 2 sides, so per-side per-inch axial
    # = IPF/24).
    taper_per_side_deg = math.degrees(math.atan(ipf_taper / 24.0))
    spec = ThreadSpec(
        family=f'API_{family_code}',
        size=label,
        pitch=P, major=D_mm,
        minor_internal=round(D_mm - 2.0 * h, 3),
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=round(D_mm - h, 3),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=h,
        crest_truncation=r,            # rounded crest, radius
        root_radius=r,                  # rounded root, same radius
        taper_per_side=taper_per_side_deg,
        standard='API Spec 7-1 / 7-2 / 7G',
        series=f'rotary-shouldered-{thread_form}',
        notes=f'Form {thread_form}, taper {ipf_taper:g} IPF '
              f'({taper_per_side_deg:.2f}° per side).  '
              'Sealing is via TORQUE SHOULDER, not the threads — threads '
              'transmit torque only.',
    )
    return spec.fill_derived()


def make_mining_drillrod(label: str, D: float, P: float,
                        rod_type: str = 'T') -> ThreadSpec:
    """Mining percussion / rotary drill-rod threads.
        rod_type: 'T' (T-thread / Sandvik), 'R' (R-thread / Atlas Copco),
                  'ST' (special tube), 'GD' (Gardner-Denver)
    Used on top-hammer and DTH (down-the-hole) drill rods, shanks,
    coupling sleeves and bits in mining, quarrying, and exploration
    drilling.  Profile is generally a rounded-V (60° flank, large
    crest/root radii) with 0° taper — connections are coupled by
    sleeve nuts or torque-shoulder thread couplings.

    Manufacturer-specific dimensions: each maker (Sandvik / Atlas
    Copco / Mitsubishi / Furukawa / Boart Longyear) publishes the
    exact profile for their own brand of rods.  Common nominal
    diameters and pitches are dimensioned here from generic
    mining-supply tables; for any production job verify against the
    specific manufacturer's drawing."""
    h = round(0.5 * P, 4)            # rounded V, ~0.5·P working height
    r = round(0.10 * P, 4)
    spec = ThreadSpec(
        family=f'Mining_{rod_type}',
        size=label,
        pitch=P, major=D,
        minor_internal=round(D - 2.0 * h, 3),
        minor_external=round(D - 2.0 * h, 3),
        pitch_dia=round(D - h, 3),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=h,
        crest_truncation=r,
        root_radius=r,
        taper_per_side=0.0,
        standard='Manufacturer std (Sandvik / Atlas Copco / etc.)',
        series='mining-drill-rod',
        notes=f'Rod type {rod_type}.  Generic dimensions — verify '
              'against the specific manufacturer\'s spec sheet.',
    )
    return spec.fill_derived()


def make_din477(label: str, D: float, P: float, profile: str = '55W',
                hand: str = 'RH', gas: str = '') -> ThreadSpec:
    """DIN 477 — Gas cylinder valve outlet threads.  Standardised
    connection numbers each tied to a SPECIFIC gas service to prevent
    cross-connection (e.g., No. 1 = oxygen RH only; No. 3 = acetylene
    LH only).  Two profile families:
      '55W' = 55° Whitworth (used on W21.8, W24.32 etc.)
      '60M' = 60° ISO Metric (used on M14×1.5 etc.)
      '55G' = 55° BSP parallel (used on G3/4, G3/8 etc.)
    Hand: 'RH' (oxidising/inert gases) or 'LH' (fuel gases — left-hand
    thread is a safety convention so fuel fittings can't accidentally
    connect to oxidiser regulators)."""
    if profile == '55W' or profile == '55G':
        h = round(0.640327 * P, 4)
        r = round(0.137329 * P, 4)
        included = 55.0
        flank = 27.5
        crest_t, root_r = r, r
    else:   # '60M' (ISO Metric)
        H = round((math.sqrt(3) / 2.0) * P, 4)
        h = H
        crest_t = round(H / 8.0, 4)
        root_r = round(H / 6.0, 4)
        included = 60.0
        flank = 30.0
    minor = round(D - 2.0 * h, 3)
    pd = round(D - h, 3)
    spec = ThreadSpec(
        family='DIN_477',
        size=label + (' LH' if hand == 'LH' else ''),
        pitch=P, major=D,
        minor_internal=minor, minor_external=minor,
        pitch_dia=pd,
        included_angle=included,
        flank_leading=flank, flank_trailing=flank,
        height_basic=h,
        crest_truncation=crest_t,
        root_radius=root_r,
        taper_per_side=0.0,
        standard='DIN 477-1 — Gas cylinder valve outlet connections',
        series='gas-cylinder',
        notes=f'Gas service: {gas}.  Hand: {hand}.  Profile: {profile}.',
    )
    return spec.fill_derived()


def make_anpt(label: str, tpi: float, D_inch: float) -> ThreadSpec:
    """ANPT — Aeronautical National Pipe Taper (SAE AS71051, formerly
    MIL-P-7105).  SAME basic dimensions and 60°/1:16 profile as NPT,
    but with TIGHTER tolerances (pitch dia controlled to Class 3 fit)
    and STRICTER inspection (functional + functional-pitch-dia gauges
    that read the THREAD form, not just crest).  Used for aerospace
    fuel, hydraulic, pneumatic and oxygen systems where reliability
    and leak-free performance are critical."""
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    h = round(0.8 * P, 4)
    spec = ThreadSpec(
        family='ANPT',
        size=label,
        pitch=P, major=D_mm,
        minor_internal=round(D_mm - 2.0 * h, 3),
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=round(D_mm - 0.8 * P, 3),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=h,
        crest_truncation=round(0.0640 * P, 4),
        root_radius=0.0,
        taper_per_side=math.degrees(math.atan(1.0 / 32.0)),  # 1:16
        standard='SAE AS71051 (formerly MIL-P-7105)',
        series='aerospace-pipe-taper',
        notes='Same profile as NPT but with Class-3-fit pitch-dia tolerance '
              'and functional-thread-gauge inspection.  For aerospace fluid '
              'systems (fuel, hydraulic, pneumatic, oxygen).',
    )
    return spec.fill_derived()


def make_npsm(label: str, tpi: float, D_inch: float,
              variant: str = 'NPSM') -> ThreadSpec:
    """NPSM / NPSL / NPSC / NPSF — American Straight Pipe Mechanical
    threads (ANSI B1.20.1).  Same 60° V profile as NPT, same pitch and
    same basic dia, but PARALLEL (no taper).  Used for mechanical
    fittings, locknuts, fuel/grease fittings, etc."""
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    h = round(0.8 * P, 4)
    spec = ThreadSpec(
        family=variant,
        size=label,
        pitch=P, major=D_mm,
        minor_internal=round(D_mm - 2.0 * h, 3),
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=round(D_mm - 0.8 * P, 3),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=h,
        crest_truncation=round(0.0640 * P, 4),
        root_radius=0.0,
        taper_per_side=0.0,                          # parallel
        standard='ANSI/ASME B1.20.1',
        series='pipe-straight',
        notes=f'{variant}: parallel pipe thread (no taper).',
    )
    return spec.fill_derived()


def make_pg(label: str, P: float, D: float) -> ThreadSpec:
    """PG (Panzer-Gewinde, DIN 40430) — electrical conduit thread.
    80° included angle, asymmetric flanks (each 40° from axis), with
    rounded crest and root.  Used for cable glands and conduit fittings.
    Discontinued in IEC but still widely used in industry."""
    h = round(0.8 * P, 4)
    spec = ThreadSpec(
        family='PG',
        size=label,
        pitch=P, major=D,
        minor_internal=round(D - 2.0 * h, 3),
        minor_external=round(D - 2.0 * h, 3),
        pitch_dia=round(D - h, 3),
        included_angle=80.0,
        flank_leading=40.0, flank_trailing=40.0,
        height_basic=h,
        crest_truncation=round(0.092 * P, 4),         # rounded crest
        root_radius=round(0.092 * P, 4),
        taper_per_side=0.0,
        standard='DIN 40430',
        series='conduit',
        notes='Electrical conduit thread.  Crest and root rounded.',
    )
    return spec.fill_derived()


def make_edison(label: str, D: float, P: float) -> ThreadSpec:
    """Edison Screw (E10, E14, E27, E40) — IEC 60061-1 lamp bases.
    60° included angle (similar V profile), specific dia/pitch per size."""
    H = round((math.sqrt(3) / 2.0) * P, 4)
    spec = ThreadSpec(
        family='Edison',
        size=label,
        pitch=P, major=D,
        minor_internal=_iso_m_minor_int(D, P),
        minor_external=_iso_m_minor_ext(D, P),
        pitch_dia=_iso_m_pitch_dia(D, P),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=H,
        crest_truncation=round(H / 8.0, 4),
        root_radius=round(H / 6.0, 4),
        taper_per_side=0.0,
        standard='IEC 60061-1',
        series='lamp-base',
    )
    return spec.fill_derived()


def make_unj(label: str, tpi: float, D_inch: float,
             series: str = 'UNJ') -> ThreadSpec:
    """UNJ — Aerospace inch thread with controlled root radius (rolled).
    60° V profile like UN, but root must be rounded (radius 0.15011·P
    minimum).  Higher fatigue strength.  Used in aerospace/military."""
    P = 25.4 / tpi
    D_mm = round(D_inch * 25.4, 4)
    H = round((math.sqrt(3) / 2.0) * P, 4)
    spec = ThreadSpec(
        family=series,
        size=label,
        pitch=P, major=D_mm,
        # UNJ external minor is slightly larger than UN (rounded root,
        # not flat).  Basic d3 ≈ D − 1.085·P for 0.15·P root radius.
        minor_internal=round(D_mm - 1.0825 * P, 3),
        minor_external=round(D_mm - 1.085 * P, 3),
        pitch_dia=round(D_mm - (3.0 / 4.0) * H, 3),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=H,
        crest_truncation=round(H / 8.0, 4),
        root_radius=round(0.15011 * P, 4),            # MIN per spec
        taper_per_side=0.0,
        standard='ANSI/ASME B1.15 / MIL-S-8879',
        series=series.lower(),
        notes='Aerospace controlled-root-radius thread.',
    )
    return spec.fill_derived()


def make_mj(D: float, P: float, label: str = None) -> ThreadSpec:
    """MJ — Aerospace metric thread with controlled root radius (rolled).
    60° V profile like ISO M, but root must be rounded (radius 0.15011·P
    min).  ISO 5855 / MIL-S-8879 (metric variant)."""
    if label is None:
        label = f'MJ{D:g}×{P:g}'
    H = round((math.sqrt(3) / 2.0) * P, 4)
    spec = ThreadSpec(
        family='MJ',
        size=label,
        pitch=P, major=D,
        minor_internal=_iso_m_minor_int(D, P),
        minor_external=round(D - 1.085 * P, 3),
        pitch_dia=_iso_m_pitch_dia(D, P),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=H,
        crest_truncation=round(H / 8.0, 4),
        root_radius=round(0.15011 * P, 4),
        taper_per_side=0.0,
        standard='ISO 5855 / MIL-S-8879',
        series='aerospace',
        notes='Aerospace metric controlled-root-radius thread.',
    )
    return spec.fill_derived()


def make_round(label: str, P: float, D: float) -> ThreadSpec:
    """Rd — Round thread (DIN 405).  30° included angle (15° flanks),
    fully rounded crests AND roots.  Used for railroad couplings,
    glass jars, hose fittings, fire-hose couplings.  Also seen in
    light-duty applications where dirt resistance matters."""
    h = round(0.5 * P, 4)
    r = round(0.2316 * P, 4)
    spec = ThreadSpec(
        family='Rd',
        size=label,
        pitch=P, major=D,
        minor_internal=round(D - 2.0 * h, 3),
        minor_external=round(D - 2.0 * h, 3),
        pitch_dia=round(D - h, 3),
        included_angle=30.0,
        flank_leading=15.0, flank_trailing=15.0,
        height_basic=h,
        crest_truncation=r,                            # rounded
        root_radius=r,
        taper_per_side=0.0,
        standard='DIN 405',
        series='round',
        notes='Round thread.  Crest and root both rounded (radius 0.232·P).',
    )
    return spec.fill_derived()


def make_saw(label: str, P: float, D: float) -> ThreadSpec:
    """Saw thread (S-Gewinde) — DIN 513.  30° asymmetric: 0° load flank
    (perpendicular to axis), 30° trailing flank.  Heavy axial load in
    one direction (similar to Buttress but more aggressive load side)."""
    h = round(0.7 * P, 4)
    spec = ThreadSpec(
        family='Saw',
        size=label,
        pitch=P, major=D,
        minor_internal=round(D - 2.0 * h, 3),
        minor_external=round(D - 2.0 * h, 3),
        pitch_dia=round(D - h, 3),
        included_angle=30.0,
        flank_leading=0.0,                             # vertical / load side
        flank_trailing=30.0,                           # back side
        height_basic=h,
        crest_truncation=round(0.124 * P, 4),
        root_radius=round(0.124 * P, 4),
        taper_per_side=0.0,
        standard='DIN 513',
        series='asymmetric',
        notes='Asymmetric: leading flank vertical, trailing 30° back.',
    )
    return spec.fill_derived()


def make_api_round(label: str, tpi: float, D_pipe_inch: float,
                   variant: str = 'API_Round') -> ThreadSpec:
    """API 5B Round Thread — 8-Round (casing STC/LC) and 10-Round
    (tubing EUE/NUE).  60° V profile, taper 1:16 on diameter (1.7899°
    per side).  Standard API casing/tubing connection."""
    P = 25.4 / tpi
    D_mm = round(D_pipe_inch * 25.4, 4)
    # API 5B: thread height differs by round count.
    if abs(tpi - 8) < 0.1:
        h = round(0.07568 * 25.4, 4)        # 1.922 mm
    elif abs(tpi - 10) < 0.1:
        h = round(0.0625 * 25.4, 4)         # 1.587 mm
    else:
        h = round(0.605 * P, 4)             # fallback
    spec = ThreadSpec(
        family=variant,
        size=label,
        pitch=P, major=D_mm,
        minor_internal=round(D_mm - 2.0 * h, 3),
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=round(D_mm - h, 3),
        included_angle=60.0,
        flank_leading=30.0, flank_trailing=30.0,
        height_basic=h,
        crest_truncation=round(0.033 * P, 4),         # API B1 truncation
        root_radius=0.0,
        taper_per_side=math.degrees(math.atan(1.0 / 32.0)),  # 1:16 ≈ 1.7899°
        standard='API 5B',
        series='oilfield-casing-tubing',
        notes='API Round thread.  STC/LC = casing; EUE/NUE = tubing.',
    )
    return spec.fill_derived()


def make_api_buttress(label: str, D_pipe_inch: float) -> ThreadSpec:
    """API 5B Buttress (BC) — Casing buttress thread.  Asymmetric:
    load flank 3° from radial, stab flank 10° from radial.
    Pitch = 1/5" = 5.08 mm.  Taper 1:16 on dia for sizes ≥ 4½",
    3/4" per foot (=1:16) below."""
    P = 25.4 / 5.0                                  # = 5.08 mm
    D_mm = round(D_pipe_inch * 25.4, 4)
    h = round(0.062 * 25.4, 4)                      # 1.575 mm
    spec = ThreadSpec(
        family='API_Buttress',
        size=label,
        pitch=P, major=D_mm,
        minor_internal=round(D_mm - 2.0 * h, 3),
        minor_external=round(D_mm - 2.0 * h, 3),
        pitch_dia=round(D_mm - h, 3),
        included_angle=13.0,                        # = 3° + 10°
        flank_leading=3.0,                          # load flank from radial
        flank_trailing=10.0,                        # stab flank from radial
        height_basic=h,
        crest_truncation=round(0.0625 * 25.4, 4),   # 1.588 mm crest flat
        root_radius=0.0,
        taper_per_side=math.degrees(math.atan(1.0 / 32.0)),
        standard='API 5B',
        series='oilfield-casing',
        notes='API Buttress.  Both flank angles measured from radial '
              '(= perpendicular to thread axis).  Equivalent in axis '
              'frame: load=87°, stab=80° from axis.',
    )
    return spec.fill_derived()


def make_buttress(label: str, P: float, D: float) -> ThreadSpec:
    """Buttress thread (BS 1657 / DIN 513).  Asymmetric: leading flank 7°
    from axis (load-bearing), trailing 45°.  Used for high axial loads
    in one direction (jacks, screw-presses).  Height = 0.75·P typical
    (some standards use 0.66·P).  Crest flat = 0.139·P."""
    h = round(0.75 * P, 4)
    spec = ThreadSpec(
        family='Buttress',
        size=label,
        pitch=P,
        major=D,
        minor_internal=round(D - 2.0 * h, 3),
        minor_external=round(D - 2.0 * h, 3),
        pitch_dia=round(D - h, 3),
        included_angle=52.0,                       # 7° + 45°
        flank_leading=7.0,                         # load side (vertical-ish)
        flank_trailing=45.0,                       # back side
        height_basic=h,
        crest_truncation=round(0.139 * P, 4),
        root_radius=round(0.124 * P, 4),
        taper_per_side=0.0,
        standard='BS 1657 / DIN 513',
        series='asymmetric',
        notes='Asymmetric: leading flank 7° (load), trailing 45° (back).',
    )
    return spec.fill_derived()


def make_buttress_us(label: str, P: float, D: float) -> ThreadSpec:
    """American Buttress thread (ANSI B1.9-1973).  Asymmetric: 7° leading
    flank (load), 45° trailing flank (back).  Used in hydraulic ram
    pistons, screw clamps, ordnance breech screws.

    Per ANSI B1.9 basic profile:
        h_basic     = 0.66271·P   (basic thread height)
        h_s (sharp) = 0.89064·P   (height of sharp V)
        crest flat  = 0.16271·P   (basic flat at crest AND root)
        root radius = 0.07141·P   (= 0.5 × crest flat, idealised)
        working dia engagement = 0.6·P (= D - 1.2·P at internal max minor)

    For Thread Info we use the BASIC profile:
        Minor (basic) = D − 2·h_basic = D − 1.32542·P
    Catalog/inch practice often rounds to D − 1.2·P (= 0.6·P engagement)
    which is the assembled fit, not the basic-cut value.
    """
    h_basic = round(0.66271 * P, 4)
    spec = ThreadSpec(
        family='Buttress_US',
        size=label,
        pitch=P,
        major=D,
        minor_internal=round(D - 2.0 * h_basic, 3),
        minor_external=round(D - 2.0 * h_basic, 3),
        pitch_dia=round(D - h_basic, 3),
        included_angle=52.0,                       # 7° + 45°
        flank_leading=7.0,                         # load side (near-radial)
        flank_trailing=45.0,                       # back side
        height_basic=h_basic,
        crest_truncation=round(0.16271 * P, 4),
        root_radius=round(0.07141 * P, 4),
        taper_per_side=0.0,
        standard='ANSI B1.9-1973',
        series='asymmetric',
        notes='American Buttress: leading flank 7° (load), trailing 45° '
              '(back).  h_basic = 0.66271·P.',
    )
    return spec.fill_derived()


def make_buttress_br(label: str, P: float, D: float) -> ThreadSpec:
    """British Buttress thread (BS 1657:1950).  Asymmetric: 7° leading,
    45° trailing.  UK/Commonwealth equivalent of ANSI B1.9, with
    slightly different basic-profile constants.

    Per BS 1657:
        h_basic     = 0.4*P + 2·s  where s ≈ 0.13733·P (approx)
                    ≈ 0.69052·P    (basic depth between flat crest and flat root)
        crest flat  = 0.16271·P (often quoted same as B1.9)
        root radius = 0.12055·P  (BS 1657 specifies fillet at root)

    For Thread Info we use h_basic = 0.69052·P.
    """
    h_basic = round(0.69052 * P, 4)
    spec = ThreadSpec(
        family='Buttress_BR',
        size=label,
        pitch=P,
        major=D,
        minor_internal=round(D - 2.0 * h_basic, 3),
        minor_external=round(D - 2.0 * h_basic, 3),
        pitch_dia=round(D - h_basic, 3),
        included_angle=52.0,                       # 7° + 45°
        flank_leading=7.0,
        flank_trailing=45.0,
        height_basic=h_basic,
        crest_truncation=round(0.16271 * P, 4),
        root_radius=round(0.12055 * P, 4),
        taper_per_side=0.0,
        standard='BS 1657:1950',
        series='asymmetric',
        notes='British Buttress: leading flank 7° (load), trailing 45° '
              '(back).  h_basic = 0.69052·P.',
    )
    return spec.fill_derived()


# =============================================================================
# DATA — populate the library.  Add more sizes here as needed.
# =============================================================================

# ----- ISO Metric coarse pitch (ISO 261 preferred sizes) -----
# (D, P) pairs, basic dia mm, coarse pitch mm.
_ISO_M_COARSE = [
    (1.0, 0.25), (1.2, 0.25), (1.6, 0.35), (2.0, 0.4), (2.5, 0.45),
    (3.0, 0.5),  (3.5, 0.6),  (4.0, 0.7),  (5.0, 0.8), (6.0, 1.0),
    (7.0, 1.0),  (8.0, 1.25), (9.0, 1.25),                        # U166: M9 added
    (10.0, 1.5), (12.0, 1.75),
    (14.0, 2.0), (16.0, 2.0), (18.0, 2.5), (20.0, 2.5),
    (22.0, 2.5), (24.0, 3.0), (27.0, 3.0), (30.0, 3.5),
    (33.0, 3.5), (36.0, 4.0), (39.0, 4.0), (42.0, 4.5),
    (45.0, 4.5), (48.0, 5.0), (50.0, 5.0),                        # U166: M50 added
    (52.0, 5.0), (55.0, 5.0),                                     # U166: M55 added
    (56.0, 5.5),
    (60.0, 5.5), (64.0, 6.0), (65.0, 5.0),                        # U166: M65 added
    (68.0, 6.0), (70.0, 6.0),                                     # U166: M70 added
    (72.0, 6.0),
    (75.0, 6.0),                                                  # U166: M75 added
    (76.0, 6.0), (80.0, 6.0),
    (85.0, 6.0),                                                  # U166: M85 added
    (90.0, 6.0),
    (95.0, 6.0),                                                  # U166: M95 added
    (100.0, 6.0),
]

# ----- ISO Metric fine pitch (ISO 261, common fine series) -----
# (D, P, label)
_ISO_M_FINE = [
    (8.0, 1.0,  'M8×1'),
    (10.0, 1.25, 'M10×1.25'), (10.0, 1.0,  'M10×1'),
    (10.0, 0.75, 'M10×0.75'),                                       # U166
    (12.0, 1.5,  'M12×1.5'),  (12.0, 1.25, 'M12×1.25'),
    (12.0, 1.0,  'M12×1'),                                          # U166
    (14.0, 1.5,  'M14×1.5'),
    (14.0, 1.25, 'M14×1.25'), (14.0, 1.0,  'M14×1'),                # U166
    (16.0, 1.5,  'M16×1.5'),
    (16.0, 1.0,  'M16×1'),                                          # U166
    (18.0, 2.0,  'M18×2'),    (18.0, 1.5,  'M18×1.5'),
    (18.0, 1.0,  'M18×1'),                                          # U166
    (20.0, 2.0,  'M20×2'),    (20.0, 1.5,  'M20×1.5'),
    (20.0, 1.0,  'M20×1'),                                          # U166
    (22.0, 2.0,  'M22×2'),    (22.0, 1.5,  'M22×1.5'),
    (22.0, 1.0,  'M22×1'),                                          # U166
    (24.0, 2.0,  'M24×2'),    (24.0, 1.5,  'M24×1.5'),
    (24.0, 1.0,  'M24×1'),                                          # U166
    (27.0, 2.0,  'M27×2'),
    (27.0, 1.5,  'M27×1.5'),  (27.0, 1.0,  'M27×1'),                # U166
    (30.0, 2.0,  'M30×2'),    (30.0, 1.5,  'M30×1.5'),
    (30.0, 1.0,  'M30×1'),                                          # U166
    (33.0, 2.0,  'M33×2'),
    (33.0, 1.5,  'M33×1.5'),  (33.0, 1.0,  'M33×1'),                # U166
    (36.0, 3.0,  'M36×3'),    (36.0, 2.0,  'M36×2'),
    (36.0, 1.5,  'M36×1.5'),                                        # U166
    (39.0, 3.0,  'M39×3'),
    (39.0, 2.0,  'M39×2'),    (39.0, 1.5,  'M39×1.5'),              # U166
    (42.0, 4.0,  'M42×4'),                                          # U166
    (42.0, 3.0,  'M42×3'),    (42.0, 2.0,  'M42×2'),
    (42.0, 1.5,  'M42×1.5'),                                        # U166
    (45.0, 4.0,  'M45×4'),                                          # U166
    (45.0, 3.0,  'M45×3'),    (45.0, 2.0,  'M45×2'),
    (45.0, 1.5,  'M45×1.5'),                                        # U166
    (48.0, 4.0,  'M48×4'),                                          # U166
    (48.0, 3.0,  'M48×3'),    (48.0, 2.0,  'M48×2'),
    (48.0, 1.5,  'M48×1.5'),                                        # U166
    (52.0, 4.0,  'M52×4'),                                          # U166
    (52.0, 3.0,  'M52×3'),
    (52.0, 2.0,  'M52×2'),    (52.0, 1.5,  'M52×1.5'),              # U166
    (56.0, 4.0,  'M56×4'),    (56.0, 3.0,  'M56×3'),
    (56.0, 2.0,  'M56×2'),    (56.0, 1.5,  'M56×1.5'),              # U166
    (60.0, 4.0,  'M60×4'),    (60.0, 3.0,  'M60×3'),
    (60.0, 2.0,  'M60×2'),    (60.0, 1.5,  'M60×1.5'),              # U166
    (64.0, 4.0,  'M64×4'),    (64.0, 3.0,  'M64×3'),
    (64.0, 2.0,  'M64×2'),    (64.0, 1.5,  'M64×1.5'),              # U166
    # U166: full fine series for M68 through M100
    (68.0, 4.0,  'M68×4'),    (68.0, 3.0,  'M68×3'),
    (68.0, 2.0,  'M68×2'),    (68.0, 1.5,  'M68×1.5'),
    (72.0, 4.0,  'M72×4'),    (72.0, 3.0,  'M72×3'),
    (72.0, 2.0,  'M72×2'),    (72.0, 1.5,  'M72×1.5'),
    (76.0, 4.0,  'M76×4'),    (76.0, 3.0,  'M76×3'),
    (76.0, 2.0,  'M76×2'),    (76.0, 1.5,  'M76×1.5'),
    (80.0, 4.0,  'M80×4'),    (80.0, 3.0,  'M80×3'),
    (80.0, 2.0,  'M80×2'),    (80.0, 1.5,  'M80×1.5'),
    (85.0, 4.0,  'M85×4'),    (85.0, 3.0,  'M85×3'),
    (85.0, 2.0,  'M85×2'),
    (90.0, 4.0,  'M90×4'),    (90.0, 3.0,  'M90×3'),
    (90.0, 2.0,  'M90×2'),
    (95.0, 4.0,  'M95×4'),    (95.0, 3.0,  'M95×3'),
    (95.0, 2.0,  'M95×2'),
    (100.0, 4.0, 'M100×4'),   (100.0, 3.0, 'M100×3'),
    (100.0, 2.0, 'M100×2'),
]

# ----- UN — Unified Coarse (UNC) per ANSI B1.1 -----
# (label, tpi, D_inch)
_UNC = [
    ('#0-80',  80, 0.0600),
    ('#1-64',  64, 0.0730),  ('#2-56', 56, 0.0860),
    ('#3-48',  48, 0.0990),  ('#4-40', 40, 0.1120),
    ('#5-40',  40, 0.1250),  ('#6-32', 32, 0.1380),
    ('#8-32',  32, 0.1640),  ('#10-24', 24, 0.1900),
    ('#12-24', 24, 0.2160),
    ('1/4-20', 20, 0.250),   ('5/16-18', 18, 0.3125),
    ('3/8-16', 16, 0.375),   ('7/16-14', 14, 0.4375),
    ('1/2-13', 13, 0.500),   ('9/16-12', 12, 0.5625),
    ('5/8-11', 11, 0.625),   ('3/4-10', 10, 0.750),
    ('7/8-9',   9, 0.875),   ('1-8',     8, 1.000),
    ('1 1/8-7', 7, 1.125),   ('1 1/4-7', 7, 1.250),
    ('1 3/8-6', 6, 1.375),   ('1 1/2-6', 6, 1.500),
    ('1 3/4-5', 5, 1.750),   ('2-4 1/2',  4.5, 2.000),
    ('2 1/4-4 1/2', 4.5, 2.250),
    ('2 1/2-4', 4, 2.500),   ('2 3/4-4',  4, 2.750),
    ('3-4',     4, 3.000),   ('3 1/4-4',  4, 3.250),
    ('3 1/2-4', 4, 3.500),   ('3 3/4-4',  4, 3.750),
    ('4-4',     4, 4.000),
]

# ----- UN — Unified Fine (UNF) per ANSI B1.1 -----
_UNF = [
    ('#0-80',  80, 0.0600),
    ('#1-72',  72, 0.0730),  ('#2-64', 64, 0.0860),
    ('#3-56',  56, 0.0990),  ('#4-48', 48, 0.1120),
    ('#5-44',  44, 0.1250),  ('#6-40', 40, 0.1380),
    ('#8-36',  36, 0.1640),  ('#10-32', 32, 0.1900),
    ('#12-28', 28, 0.2160),
    ('1/4-28', 28, 0.250),   ('5/16-24', 24, 0.3125),
    ('3/8-24', 24, 0.375),   ('7/16-20', 20, 0.4375),
    ('1/2-20', 20, 0.500),   ('9/16-18', 18, 0.5625),
    ('5/8-18', 18, 0.625),   ('3/4-16', 16, 0.750),
    ('7/8-14', 14, 0.875),   ('1-12',   12, 1.000),
    ('1 1/8-12', 12, 1.125), ('1 1/4-12', 12, 1.250),
    ('1 3/8-12', 12, 1.375), ('1 1/2-12', 12, 1.500),
]

# ----- UNEF — Extra Fine -----
_UNEF = [
    ('#12-32',   32, 0.2160),
    ('1/4-32',   32, 0.250),  ('5/16-32',   32, 0.3125),
    ('3/8-32',   32, 0.375),  ('7/16-28',   28, 0.4375),
    ('1/2-28',   28, 0.500),  ('9/16-24',   24, 0.5625),
    ('5/8-24',   24, 0.625),  ('11/16-24',  24, 0.6875),
    ('3/4-20',   20, 0.750),  ('13/16-20',  20, 0.8125),
    ('7/8-20',   20, 0.875),  ('15/16-20',  20, 0.9375),
    ('1-20',     20, 1.000),  ('1 1/16-18', 18, 1.0625),
    ('1 1/8-18', 18, 1.125),  ('1 3/16-18', 18, 1.1875),
    ('1 1/4-18', 18, 1.250),  ('1 1/2-18',  18, 1.500),
    ('1 11/16-16', 16, 1.6875), ('1 3/4-16', 16, 1.750),
    ('2-16',     16, 2.000),
]

# ----- BSW — British Standard Whitworth (BS 84) -----
_BSW = [
    ('1/16',  60, 0.0625),  ('3/32', 48, 0.09375),
    ('1/8',   40, 0.125),   ('5/32', 32, 0.15625),
    ('3/16',  24, 0.1875),  ('7/32', 24, 0.21875),
    ('1/4',   20, 0.250),   ('5/16', 18, 0.3125),
    ('3/8',   16, 0.375),   ('7/16', 14, 0.4375),
    ('1/2',   12, 0.500),   ('9/16', 12, 0.5625),
    ('5/8',   11, 0.625),   ('3/4',  10, 0.750),
    ('7/8',    9, 0.875),   ('1',     8, 1.000),
    ('1 1/8',  7, 1.125),   ('1 1/4', 7, 1.250),
    ('1 1/2',  6, 1.500),   ('1 3/4', 5, 1.750),
    ('2',    4.5, 2.000),
]

# ----- BSF — British Standard Fine (BS 84) -----
_BSF = [
    ('3/16', 32, 0.1875),  ('7/32', 28, 0.21875),
    ('1/4',  26, 0.250),   ('9/32', 26, 0.28125),
    ('5/16', 22, 0.3125),  ('3/8',  20, 0.375),
    ('7/16', 18, 0.4375),  ('1/2',  16, 0.500),
    ('9/16', 16, 0.5625),  ('5/8',  14, 0.625),
    ('11/16',14, 0.6875),  ('3/4',  12, 0.750),
    ('13/16',12, 0.8125),  ('7/8',  11, 0.875),
    ('1',    10, 1.000),   ('1 1/8', 9, 1.125),
    ('1 1/4', 9, 1.250),   ('1 1/2', 8, 1.500),
]

# ----- BSP (G) parallel pipe per ISO 228 -----
# (label, tpi, D_inch_basic)  — D_inch is the BASIC pipe major
_BSP = [
    ('1/16', 28, 0.3043),  ('1/8',  28, 0.3826),
    ('1/4',  19, 0.5180),  ('3/8',  19, 0.6562),
    ('1/2',  14, 0.8255),  ('5/8',  14, 0.9024),
    ('3/4',  14, 1.0410),  ('7/8',  14, 1.1810),
    ('1',    11, 1.3094),  ('1 1/8', 11, 1.4488),
    ('1 1/4', 11, 1.6500), ('1 1/2', 11, 1.8819),
    ('1 3/4', 11, 2.1063), ('2',     11, 2.3469),
    ('2 1/4', 11, 2.5867), ('2 1/2', 11, 2.9606),
    ('3',     11, 3.4606), ('4',     11, 4.4606),
    ('5',     11, 5.4488), ('6',     11, 6.4488),
]

# ----- Acme General Purpose (ANSI B1.5) -----
_ACME = [
    ('1/4-16',    16, 0.250),  ('5/16-14',   14, 0.3125),
    ('3/8-12',    12, 0.375),  ('7/16-12',   12, 0.4375),
    ('1/2-10',    10, 0.500),  ('5/8-8',      8, 0.625),
    ('3/4-6',      6, 0.750),  ('7/8-6',      6, 0.875),
    ('1-5',        5, 1.000),  ('1 1/8-5',    5, 1.125),
    ('1 1/4-5',    5, 1.250),  ('1 3/8-4',    4, 1.375),
    ('1 1/2-4',    4, 1.500),  ('1 3/4-4',    4, 1.750),
    ('2-4',        4, 2.000),  ('2 1/4-3',    3, 2.250),
    ('2 1/2-3',    3, 2.500),  ('2 3/4-3',    3, 2.750),
    ('3-2',        2, 3.000),  ('3 1/2-2',    2, 3.500),
    ('4-2',        2, 4.000),  ('4 1/2-2',    2, 4.500),
    ('5-2',        2, 5.000),
]

# ----- Trapezoidal (TR) per DIN 103 -----
# (D, P)
_TR = [
    (8, 1.5),  (10, 2.0), (12, 3.0), (14, 3.0), (16, 4.0),
    (18, 4.0), (20, 4.0), (22, 5.0), (24, 5.0), (26, 5.0),
    (28, 5.0), (30, 6.0), (32, 6.0), (34, 6.0), (36, 6.0),
    (38, 7.0), (40, 7.0), (42, 7.0), (44, 7.0), (46, 8.0),
    (48, 8.0), (50, 8.0), (52, 8.0), (55, 9.0), (60, 9.0),
    (65, 10.0),(70, 10.0),(75, 10.0),(80, 10.0),(90, 12.0),
    (100, 12.0),(110, 12.0),(120, 14.0),(130, 14.0),(140, 14.0),
    (150, 16.0),(160, 16.0),(170, 16.0),(180, 18.0),(190, 18.0),
    (200, 18.0),
]

# ----- NPT (ANSI B1.20.1) -----
_NPT = [
    ('1/16',  27, 5/16),    ('1/8',  27, 27/64),
    ('1/4',   18, 17/32),   ('3/8',  18, 21/32),
    ('1/2',   14, 27/32),   ('3/4',  14, 1+1/16),
    ('1',     11.5, 1+5/16),
    ('1 1/4', 11.5, 1+21/32),
    ('1 1/2', 11.5, 1+29/32),
    ('2',     11.5, 2+3/8),
    ('2 1/2',  8, 2+27/32),
    ('3',      8, 3+1/2),
    ('4',      8, 4+1/2),
    ('5',      8, 5+9/16),
    ('6',      8, 6+5/8),
]

# ----- Buttress (BS 1657 sample sizes) -----
# (label, P, D)
_BUTTRESS = [
    ('B 16×3',   3.0,   16.0), ('B 20×4',   4.0,   20.0),
    ('B 24×5',   5.0,   24.0), ('B 30×6',   6.0,   30.0),
    ('B 40×7',   7.0,   40.0), ('B 50×8',   8.0,   50.0),
    ('B 60×9',   9.0,   60.0), ('B 80×10', 10.0,   80.0),
    ('B 100×12',12.0, 100.0), ('B 120×14', 14.0, 120.0),
    ('B 160×16', 16.0, 160.0), ('B 200×18', 18.0, 200.0),
]

# ----- NPSM / NPSL / NPSC / NPSF — straight pipe threads -----
# Same TPI and basic dia as NPT.
_NPSM = _NPT[:]   # NPSM uses same sizes as NPT
_NPSL = _NPT[:]
_NPSC = _NPT[:]

# ----- PG (Panzer Gewinde) — DIN 40430 conduit thread -----
# (label, P, D)
_PG = [
    ('PG7',     1.0, 12.5),  ('PG9',     1.0, 15.2),
    ('PG11',  1.5, 18.6),    ('PG13.5', 1.5, 20.4),
    ('PG16',  1.5, 22.5),    ('PG21',   1.5, 28.3),
    ('PG29',  1.5, 37.0),    ('PG36',   1.5, 47.0),
    ('PG42',  1.5, 54.0),    ('PG48',   1.5, 59.3),
]

# ----- Edison Screw (lamp bases) — IEC 60061-1 -----
# (label, D, P)  D = nominal lamp base major dia
_EDISON = [
    ('E10', 10.0, 1.27),    ('E12', 12.0, 1.27),
    ('E14', 14.0, 1.27),    ('E17', 17.0, 1.27),
    ('E26', 26.0, 3.629),   ('E27', 27.0, 3.629),
    ('E40', 40.0, 6.350),
]

# ----- UNJ (aerospace inch, controlled root radius) -----
# Uses same sizes as UNF.  Sample subset.
_UNJ = [
    ('1/4-28',   28, 0.250),    ('5/16-24',   24, 0.3125),
    ('3/8-24',   24, 0.375),    ('7/16-20',   20, 0.4375),
    ('1/2-20',   20, 0.500),    ('9/16-18',   18, 0.5625),
    ('5/8-18',   18, 0.625),    ('3/4-16',    16, 0.750),
    ('7/8-14',   14, 0.875),    ('1-12',      12, 1.000),
    ('1 1/8-12', 12, 1.125),    ('1 1/4-12',  12, 1.250),
]

# ----- MJ (aerospace metric, controlled root radius) -----
# (D, P) — common aerospace metric sizes
_MJ = [
    (3.0, 0.5),  (4.0, 0.7),   (5.0, 0.8),   (6.0, 1.0),
    (8.0, 1.0),  (8.0, 1.25),  (10.0, 1.0),  (10.0, 1.5),
    (12.0, 1.5), (12.0, 1.75), (14.0, 1.5),  (16.0, 1.5),
    (18.0, 1.5), (20.0, 1.5),  (22.0, 1.5),  (24.0, 2.0),
]

# ----- Round thread (Rd) — DIN 405 -----
# (label, P, D)
_ROUND = [
    ('Rd 8×2.54',   2.54,  8.0),   ('Rd 10×2.54',  2.54, 10.0),
    ('Rd 12×2.54',  2.54, 12.0),   ('Rd 16×3.175', 3.175, 16.0),
    ('Rd 20×4.233', 4.233, 20.0),  ('Rd 24×5.08',  5.08, 24.0),
    ('Rd 30×6.35',  6.35, 30.0),   ('Rd 40×8.466', 8.466, 40.0),
    ('Rd 50×8.466', 8.466, 50.0),  ('Rd 60×10.16', 10.16, 60.0),
    ('Rd 80×10.16', 10.16, 80.0),  ('Rd 100×12.7', 12.7, 100.0),
]

# ----- Saw thread (S-Gewinde) — DIN 513 -----
# (label, P, D)  asymmetric, 0°/30°
_SAW = [
    ('S 16×3',   3.0,   16.0),   ('S 20×4',   4.0,   20.0),
    ('S 24×5',   5.0,   24.0),   ('S 30×6',   6.0,   30.0),
    ('S 40×7',   7.0,   40.0),   ('S 50×8',   8.0,   50.0),
    ('S 60×9',   9.0,   60.0),   ('S 80×10', 10.0,   80.0),
    ('S 100×12',12.0, 100.0),    ('S 120×14',14.0, 120.0),
]

# ----- API Round (API 5B / 5CT) -----
# 8-Round = casing (STC, LC).  10-Round = tubing (EUE, NUE).
# (label, tpi, D_pipe_inch_basic).  Pipe OD basic.
_API_ROUND_8 = [
    ('4 1/2 STC',    8, 4.500),  ('4 1/2 LC',     8, 4.500),
    ('5 STC',        8, 5.000),  ('5 LC',         8, 5.000),
    ('5 1/2 STC',    8, 5.500),  ('5 1/2 LC',     8, 5.500),
    ('6 5/8 STC',    8, 6.625),  ('6 5/8 LC',     8, 6.625),
    ('7 STC',        8, 7.000),  ('7 LC',         8, 7.000),
    ('7 5/8 STC',    8, 7.625),  ('7 5/8 LC',     8, 7.625),
    ('8 5/8 STC',    8, 8.625),  ('8 5/8 LC',     8, 8.625),
    ('9 5/8 STC',    8, 9.625),  ('9 5/8 LC',     8, 9.625),
    ('10 3/4 STC',   8, 10.750), ('10 3/4 LC',    8, 10.750),
    ('11 3/4 STC',   8, 11.750), ('11 3/4 LC',    8, 11.750),
    ('13 3/8 STC',   8, 13.375), ('13 3/8 LC',    8, 13.375),
    ('16 STC',       8, 16.000), ('16 LC',        8, 16.000),
    ('18 5/8 STC',   8, 18.625), ('20 STC',       8, 20.000),
]

_API_ROUND_10 = [
    ('1.050 EUE',  10, 1.050),  ('1.050 NUE',  10, 1.050),
    ('1.315 EUE',  10, 1.315),  ('1.315 NUE',  10, 1.315),
    ('1.660 EUE',  10, 1.660),  ('1.660 NUE',  10, 1.660),
    ('1.900 EUE',  10, 1.900),  ('1.900 NUE',  10, 1.900),
    ('2 3/8 EUE',  10, 2.375),  ('2 3/8 NUE',  10, 2.375),
    ('2 7/8 EUE',  10, 2.875),  ('2 7/8 NUE',  10, 2.875),
    ('3 1/2 EUE',  10, 3.500),  ('3 1/2 NUE',  10, 3.500),
    ('4 EUE',      10, 4.000),  ('4 NUE',      10, 4.000),
    ('4 1/2 EUE',  10, 4.500),  ('4 1/2 NUE',  10, 4.500),
]

# ----- API Buttress (BC) — API 5B -----
_API_BUTTRESS = [
    ('4 1/2 BC',  4.500),  ('5 BC',     5.000),  ('5 1/2 BC',  5.500),
    ('6 5/8 BC',  6.625),  ('7 BC',     7.000),  ('7 5/8 BC',  7.625),
    ('8 5/8 BC',  8.625),  ('9 5/8 BC', 9.625),  ('10 3/4 BC', 10.750),
    ('11 3/4 BC',11.750),  ('13 3/8 BC',13.375), ('16 BC',     16.000),
    ('18 5/8 BC',18.625),  ('20 BC',    20.000),
]

# ----- API Rotary Shouldered Connections (drill string) — API 7-1 / 7G -----
# (label, pin_OD_inch, tpi, ipf_taper, family_code, thread_form, root_rad_in)
# Pin OD = the outer diameter of the male (pin) end at the shoulder.
# Note: drill-string connection sizes refer to the BOX OD typically.
_API_RSC = [
    # NC (Numbered Connections) — most common drill-pipe / collar threads
    ('NC23',   3.00, 4, 2, 'NC', 'V-0.040', 0.020),
    ('NC26',   3.375, 4, 2, 'NC', 'V-0.040', 0.020),    # = 2 3/8 IF
    ('NC31',   4.125, 4, 2, 'NC', 'V-0.040', 0.020),    # = 2 7/8 IF
    ('NC35',   4.500, 4, 2, 'NC', 'V-0.038R', 0.038),
    ('NC38',   4.750, 4, 2, 'NC', 'V-0.038R', 0.038),   # = 3 1/2 IF
    ('NC40',   5.000, 4, 2, 'NC', 'V-0.038R', 0.038),
    ('NC44',   5.250, 4, 2, 'NC', 'V-0.038R', 0.038),
    ('NC46',   6.000, 4, 2, 'NC', 'V-0.038R', 0.038),   # = 4 IF
    ('NC50',   6.625, 4, 2, 'NC', 'V-0.038R', 0.038),   # = 4 1/2 IF, common
    ('NC56',   7.000, 4, 2, 'NC', 'V-0.050', 0.025),
    ('NC61',   8.000, 4, 2, 'NC', 'V-0.050', 0.025),
    ('NC70',   9.000, 4, 2, 'NC', 'V-0.050', 0.025),
    ('NC77',  10.000, 4, 2, 'NC', 'V-0.050', 0.025),
    # REG (Regular) — heavier oilfield connections
    ('2 3/8 REG',  3.125, 5, 3, 'REG', 'V-0.040', 0.020),
    ('2 7/8 REG',  3.750, 5, 3, 'REG', 'V-0.040', 0.020),
    ('3 1/2 REG',  4.750, 5, 3, 'REG', 'V-0.040', 0.020),
    ('4 1/2 REG',  6.250, 5, 3, 'REG', 'V-0.050', 0.025),
    ('5 1/2 REG',  7.250, 5, 3, 'REG', 'V-0.050', 0.025),
    ('6 5/8 REG',  8.500, 4, 2, 'REG', 'V-0.050', 0.025),
    ('7 5/8 REG',  9.500, 4, 2, 'REG', 'V-0.050', 0.025),
    ('8 5/8 REG', 11.000, 4, 2, 'REG', 'V-0.050', 0.025),
    # FH (Full Hole) — older spec, for drill collars
    ('4 FH',       6.250, 4, 2, 'FH',  'V-0.040', 0.020),
    ('4 1/2 FH',   6.500, 4, 2, 'FH',  'V-0.050', 0.025),
    # H-90 — Hughes connections (heavy-duty)
    ('5 1/2 H-90', 7.500, 4, 2, 'H',   'V-0.050', 0.025),
    ('7 5/8 H-90',10.000, 4, 2, 'H',   'V-0.050', 0.025),
]

# ----- API Macaroni Tubing (small-OD oilfield production tubing) -----
# (label, OD_inch, tpi, ipf, family, form, root_rad)
_API_MACARONI = [
    # MT, AMT, AMMT — V-0.055 form, used on slim production tubing.
    ('MT 1.050',     1.050, 6, 1.5, 'MT', 'V-0.055', 0.025),
    ('MT 1.315',     1.315, 6, 1.5, 'MT', 'V-0.055', 0.025),
    ('MT 1.660',     1.660, 6, 1.5, 'MT', 'V-0.055', 0.025),
    ('MT 1.900',     1.900, 6, 1.5, 'MT', 'V-0.055', 0.025),
    ('AMMT 1.315',   1.315, 6, 1.5, 'AMMT', 'V-0.055', 0.025),
    ('AMMT 1.660',   1.660, 6, 1.5, 'AMMT', 'V-0.055', 0.025),
    ('AMMT 1.900',   1.900, 6, 1.5, 'AMMT', 'V-0.055', 0.025),
]

# ----- Mining percussion / rotary drill-rod threads -----
# (label, D_mm, P_mm, rod_type)  Generic table — verify against
# the maker's drawing for production work.
_MINING_RODS = [
    # R-thread (Atlas Copco / Epiroc) — top-hammer, small-medium holes
    ('R25',  25.0,  6.35, 'R'),    # 1/4" pitch, common shank thread
    ('R28',  28.0,  6.35, 'R'),
    ('R32',  32.0,  6.35, 'R'),    # 1-1/4" rod, very common
    ('R38',  38.0,  6.35, 'R'),
    # T-thread (Sandvik / Mitsubishi) — top-hammer, larger holes
    ('T38',  38.0,  6.35, 'T'),
    ('T45',  45.0,  6.35, 'T'),
    ('T51',  51.0,  6.35, 'T'),
    ('T60',  60.0,  6.35, 'T'),    # GT60, large bench drilling
    # ST tube-rod system (Sandvik special) — long-hole drilling
    ('ST58', 58.0,  6.35, 'ST'),
    ('ST68', 68.0,  6.35, 'ST'),
    # GD (Gardner-Denver) — older mining thread, still in service
    ('GD-1', 31.0,  4.233, 'GD'),
    ('GD-2', 35.0,  4.233, 'GD'),
]

# ----- DIN 477 — gas cylinder valve outlet connections -----
# Each connection number is RESERVED for a specific gas service to
# prevent fuel/oxidiser cross-connection.  RH/LH is part of the safety
# coding: fuel gases use LH threads, oxidisers use RH.
# (label, D, P, profile, hand, gas service)
_DIN_477 = [
    # No. 1 - Oxygen, compressed air, breathing air (most common)
    ('No.1 W21.8×1/14"', 21.8, 25.4/14.0, '55W', 'RH',
     'Oxygen / compressed breathing air'),
    # No. 2 - Compressed air (industrial)
    ('No.2 G3/4"', 26.441, 25.4/14.0, '55G', 'RH',
     'Compressed industrial air'),
    # No. 3 - Acetylene + most fuel gases (LH safety coding)
    ('No.3 W21.8×1/14" LH', 21.8, 25.4/14.0, '55W', 'LH',
     'Acetylene, propane, methane, hydrogen (fuel gases)'),
    # No. 4 - Inert gases (Argon, Nitrogen, Helium, CO2)
    ('No.4 G5/8"', 22.911, 25.4/14.0, '55G', 'RH',
     'Argon / Nitrogen / Helium / Carbon Dioxide (inert)'),
    # No. 5 - Hydrogen (LH coding)
    ('No.5 G3/8" LH', 16.662, 25.4/19.0, '55G', 'LH',
     'Hydrogen (some variants)'),
    # No. 6 - CO2, N2O (medical), special chemistries
    ('No.6 W24.32×1/14"', 24.32, 25.4/14.0, '55W', 'RH',
     'Carbon dioxide / Nitrous oxide / specialty'),
    # No. 7 - Specialty (medical / instrument gases)
    ('No.7 M14×1.5', 14.0, 1.5, '60M', 'RH',
     'Specialty / instrument gases'),
    # No. 8 - Halogenated gases / refrigerants
    ('No.8 G1/2"', 20.955, 25.4/14.0, '55G', 'RH',
     'Halogenated gases / refrigerants'),
    # No. 9 - Variant for medical oxygen
    ('No.9 W21.8×1/14"', 21.8, 25.4/14.0, '55W', 'RH',
     'Medical oxygen variant (No.1 dimensions, different markings)'),
    # No. 10 - Fuel gas LH variant
    ('No.10 G5/8" LH', 22.911, 25.4/14.0, '55G', 'LH',
     'Fuel gas variant'),
    # No. 11 - Toxic / corrosive gases LH
    ('No.11 G3/4" LH', 26.441, 25.4/14.0, '55G', 'LH',
     'Toxic / corrosive fuel gases'),
    # No. 12 - Larger metric specialty
    ('No.12 M16×1.5', 16.0, 1.5, '60M', 'RH',
     'Specialty / larger valves'),
    # No. 13 - Metric LH specialty
    ('No.13 M14×1.5 LH', 14.0, 1.5, '60M', 'LH',
     'Specialty fuel'),
    # No. 14 - Larger metric (e.g., bulk supply valves)
    ('No.14 M22×1.5', 22.0, 1.5, '60M', 'RH',
     'Larger / bulk-supply valves'),
]


# =============================================================================
# PROPRIETARY THREADS — names listed but profile data NOT published.
# =============================================================================
#
# The threads below are PATENTED / TRADEMARKED proprietary connections.
# Their detailed profile geometry (exact flank angles, root/crest radii,
# torque shoulder, helical taper, sealing surfaces, makeup criteria) is
# protected by the manufacturer's intellectual property and is only
# available through:
#   - The manufacturer's licensed CAM/calculation software
#   - A paid technical license / data sheet from the manufacturer
#   - The manufacturer's authorized service shops
#
# Distributing these dimensions in open-source or third-party software
# would violate the patent / trade-secret rights of the holder.  We list
# the connection by name so operators recognize what they're machining,
# but they MUST source dimensions from the manufacturer for the actual
# program.

PROPRIETARY_THREADS = [
    # --- VAM family (Vallourec) — premium oil & gas connections ---
    {
        'name': 'VAM TOP', 'manufacturer': 'Vallourec',
        'category': 'oilfield-premium-casing-tubing',
        'description': 'Premium semi-flush casing/tubing connection with metal-to-metal seal and torque shoulder.  Industry-leading gas-tight performance for HP/HT wells.',
    },
    {
        'name': 'VAM 21', 'manufacturer': 'Vallourec',
        'category': 'oilfield-premium',
        'description': 'High-collapse premium connection for deep / sour service wells.',
    },
    {
        'name': 'NEW VAM', 'manufacturer': 'Vallourec',
        'category': 'oilfield-premium',
        'description': 'Earlier-generation premium VAM connection, still widely deployed.',
    },
    {
        'name': 'VAM SLIJ-II', 'manufacturer': 'Vallourec',
        'category': 'oilfield-premium-flush',
        'description': 'Slim-line semi-flush connection for tight-clearance applications.',
    },

    # --- TenarisHydril Wedge family ---
    {
        'name': 'Wedge 521', 'manufacturer': 'TenarisHydril',
        'category': 'oilfield-premium-wedge',
        'description': 'Wedge-thread casing connection — interlocking thread profile that increases makeup torque progressively.  Very high tension/compression rating.',
    },
    {
        'name': 'Wedge 533', 'manufacturer': 'TenarisHydril',
        'category': 'oilfield-premium-wedge',
        'description': 'Premium wedge connection with elastomer / metal-to-metal seal options.',
    },
    {
        'name': 'BLUE', 'manufacturer': 'TenarisHydril',
        'category': 'oilfield-premium',
        'description': 'Premium gas-tight integral connection for casing and tubing.',
    },
    {
        'name': 'BLUE DOCK', 'manufacturer': 'TenarisHydril',
        'category': 'oilfield-premium-flush',
        'description': 'Flush integral premium connection.',
    },

    # --- Hunting Energy proprietary ---
    {
        'name': 'Seal-Lock', 'manufacturer': 'Hunting Energy',
        'category': 'oilfield-premium',
        'description': 'Premium semi-flush connection with metal-to-metal seal.',
    },
    {
        'name': 'TKC', 'manufacturer': 'Hunting Energy',
        'category': 'oilfield-premium-flush',
        'description': 'Premium flush connection.',
    },

    # --- Other oilfield premium ---
    {
        'name': 'JFE BEAR', 'manufacturer': 'JFE Steel',
        'category': 'oilfield-premium',
        'description': 'Japanese premium casing connection.',
    },
    {
        'name': 'GRANT TFW HT', 'manufacturer': 'Grant Prideco / NOV',
        'category': 'oilfield-premium-tubing',
        'description': 'High-torque premium tubing connection.',
    },

    # --- Fastener / mechanical proprietary self-locking threads ---
    {
        'name': 'Stanley Self-Locking', 'manufacturer': 'Stanley Fastening Systems',
        'category': 'self-locking-fastener',
        'description': 'Self-locking thread variant — one flank (typically the load side) is modified to grip and resist back-out under vibration.',
    },
    {
        'name': 'Spiralock', 'manufacturer': 'Stanley Engineered Fastening',
        'category': 'self-locking-fastener',
        'description': '30° wedge ramp at the root of the internal thread mates against the crest of a standard external thread, preventing loosening under shock/vibration without separate locking elements.',
    },
    {
        'name': 'Detroit Tool / Tap-Lok', 'manufacturer': 'various',
        'category': 'self-locking-fastener',
        'description': 'Locking thread profile with deformed crest.',
    },

    # --- Thread inserts (proprietary form, but installation widely documented) ---
    {
        'name': 'Heli-Coil', 'manufacturer': 'Stanley Engineered Fastening',
        'category': 'thread-insert',
        'description': 'Helical wire coil insert — installs in an oversized tapped hole and presents a standard internal thread.  Tap dimensions are public; insert profile is proprietary.',
    },
    {
        'name': 'Time-Sert', 'manufacturer': 'Time Fasteners',
        'category': 'thread-insert',
        'description': 'Solid-bushing thread insert with internal thread, expanded into a tapped hole.  Public installation dims; insert geometry proprietary.',
    },
    {
        'name': 'KEENSERT', 'manufacturer': 'Alcoa Fastening Systems',
        'category': 'thread-insert',
        'description': 'Solid bushing insert with locking keys driven into the parent material.  Keys positively prevent rotation.',
    },
    {
        'name': 'EZ-LOK', 'manufacturer': 'EZ-LOK',
        'category': 'thread-insert',
        'description': 'Thin-wall solid threaded insert for soft materials.',
    },

    # --- Special-purpose patented ---
    {
        'name': 'Power-Lok', 'manufacturer': 'various',
        'category': 'self-locking',
        'description': 'Family of locking thread profiles (asymmetric or modified-flank) for specific applications.',
    },
    {
        'name': 'Eaton WAM (Walter Air Mining)', 'manufacturer': 'Eaton (legacy)',
        'category': 'oilfield / specialty',
        'description': 'Proprietary connection used in specific oilfield/mining drilling tools.  Profile and torque criteria are proprietary to the manufacturer.',
    },
]


def proprietary_threads() -> list:
    """Return the list of proprietary threads (name + description only).
    Profile dimensions are NOT included — see the docstring at the top
    of the proprietary section."""
    return list(PROPRIETARY_THREADS)


def proprietary_info(name: str) -> Optional[dict]:
    """Look up a proprietary thread by name (case-insensitive substring)."""
    name_lower = name.lower()
    for entry in PROPRIETARY_THREADS:
        if name_lower in entry['name'].lower():
            return dict(entry, dimensions=(
                'PROPRIETARY — profile dimensions are protected by the '
                'manufacturer\'s patent / trade secret.  Obtain from the '
                'manufacturer\'s licensed CAM software or technical data sheet.'
            ))
    return None


# =============================================================================
# REFERENCE CITATIONS — full publication titles per family.
# =============================================================================

REFERENCES = {
    'M_coarse':     'ISO 261:1998 — ISO general purpose metric screw threads — General plan; ISO 68-1:1998 — Basic profile; ISO 965-1:2013 — Tolerances.',
    'M_fine':       'ISO 261:1998; ISO 68-1:1998 — Basic profile.',
    'UNC':          'ANSI/ASME B1.1-2003 (R2018) — Unified Inch Screw Threads (UN and UNR Thread Form).',
    'UNF':          'ANSI/ASME B1.1-2003 (R2018) — Unified Inch Screw Threads.',
    'UNEF':         'ANSI/ASME B1.1-2003 (R2018) — Unified Inch Screw Threads.',
    'UNJ':          'ANSI/ASME B1.15-2004 — Unified Inch Screw Threads, UNJ Form (with controlled root radius); MIL-S-8879C.',
    'MJ':           'ISO 5855-1:1999 — Aerospace — MJ threads — Part 1: General requirements; ISO 5855-2:1999 — Limit dimensions.',
    'BSW':          'BS 84:2007 — Parallel screw threads of Whitworth form.',
    'BSF':          'BS 84:2007 — Parallel screw threads of Whitworth form (fine).',
    'BSP':          'ISO 228-1:2000 — Pipe threads where pressure-tight joints are not made on the threads — Part 1: Dimensions, tolerances and designation.',
    'BSPT':         'ISO 7-1:1994 — Pipe threads where pressure-tight joints are made on the threads — Part 1: Dimensions, tolerances and designation.',
    'NPT':          'ANSI/ASME B1.20.1-2013 — Pipe Threads, General Purpose, Inch.  Reference dimensions also from Baker Hughes "American National Standard Taper Pipe Threads" technical reference.',
    'NPTF':         'ANSI/ASME B1.20.3-1976 (R2013) — Dryseal Pipe Threads (Inch).',
    'ANPT':         'SAE AS71051 (formerly MIL-P-7105) — Aeronautical National Pipe Taper.  Same basic profile as NPT (B1.20.1) but with tighter pitch-dia tolerance and functional-thread-gauge inspection for aerospace fluid systems.',
    'NPSM':         'ANSI/ASME B1.20.1-2013 — straight mechanical pipe thread.',
    'NPSL':         'ANSI/ASME B1.20.1-2013 — straight locknut pipe thread.',
    'NPSC':         'ANSI/ASME B1.20.1-2013 — straight pipe thread for couplings.',
    'Acme':         'ANSI/ASME B1.5-1997 (R2014) — Acme Screw Threads.',
    'Stub_Acme':    'ANSI/ASME B1.8-1988 (R2011) — Stub Acme Screw Threads.',
    'TR':           'DIN 103-1:1977 — Metric ISO trapezoidal screw threads — Profiles; ISO 2901:1993 — Basic and design profiles.',
    'Buttress':     'BS 1657:1950 — Buttress threads; DIN 513:1985 — Buttress threads (German equivalent).',
    'Saw':          'DIN 513:1985 — Sägengewinde (saw thread).',
    'Round':        'DIN 405:1997 — Rundgewinde (round thread).',
    'PG':           'DIN 40430:1971 — Panzer-Gewinde (electrical conduit thread).  Largely superseded by IEC 60423 metric threads but still in industrial use.',
    'DIN_477':      'DIN 477-1:2017 — Gas cylinder valves — Outlet connections.  Connection numbers are GAS-SPECIFIC for safety: oxidisers use RH threads, fuel gases use LH threads.  Always verify the assigned connection number against current ISO/EN standards (ISO 5145 / EN ISO 11363) for the target gas service.',
    'Edison':       'IEC 60061-1:2017 — Lamp caps and holders — Part 1: Lamp caps.',
    'API_Round_8':  'API Spec 5B (16th Edition, 2017) — Specification for Threading, Gauging, and Thread Inspection of Casing, Tubing, and Line Pipe Threads (8-Round).',
    'API_Round_10': 'API Spec 5B (16th Edition, 2017) — 10-Round (used for tubing EUE/NUE).',
    'API_Buttress': 'API Spec 5B (16th Edition, 2017) — Casing Buttress (BC).',
    'API_RSC':      'API Spec 7-1 / 7-2 / 7G — Rotary Shouldered Connections for drill-string components (NC, REG, FH, H-90).',
    'API_Macaroni': 'API Spec 5B / 5CT — Macaroni tubing (MT, AMT, AMMT) for slim-OD oilfield production tubing.',
    'Mining':       'Manufacturer-specific (Sandvik / Epiroc-Atlas Copco / Mitsubishi / Furukawa / Boart Longyear).  Cross-checked against ISO 1722 (mining drill rods) where applicable.  No single international standard.',
}


# =============================================================================
# FUNCTIONALITY / USE-CASE — what is the thread profile for and where used.
# =============================================================================

USE_CASES = {
    'M_coarse': {
        'function': 'General-purpose fastening with high engagement strength per unit length.  60° symmetric V-thread distributes load evenly between flanks; coarse pitch trades a small loss in tension capacity for fast assembly and tolerance to dirt/burrs.',
        'where_used': 'Default thread for industrial fasteners worldwide outside the inch market — bolts, studs, machine screws, structural members, automotive, machinery, appliances, civil structures.',
        'when_to_choose': 'Whenever a metric fastener is required without a specific reason for fine pitch.',
    },
    'M_fine': {
        'function': 'Same 60° V profile but smaller pitch.  Higher tensile area, finer adjustment, better resistance to vibration loosening (more turns per mm), but more sensitive to galling and damage.',
        'where_used': 'Aerospace fittings, hydraulic/pneumatic adjustment screws, instrument fittings, thin-wall tube nuts, bolts loaded near tensile limit, vibration-critical joints (engines, rotating equipment).',
        'when_to_choose': 'Need higher pre-load, fine adjustment, or vibration resistance.  Avoid for blind holes in soft materials (galling risk).',
    },
    'UNC': {
        'function': 'Unified Inch Coarse — imperial equivalent of ISO M_coarse.  60° symmetric V, general-purpose inch thread.',
        'where_used': 'North American manufacturing — construction, automotive (legacy), agriculture, plumbing, hand-tool fasteners.',
        'when_to_choose': 'Default inch fastener; matches American/Canadian inventory and tooling.',
    },
    'UNF': {
        'function': 'Unified Inch Fine.  Higher tensile area, better vibration resistance.',
        'where_used': 'Aerospace, automotive (engines, drivetrains), precision adjustment, fluid-system fittings, racing components.',
        'when_to_choose': 'Inch fastener requiring higher strength or vibration resistance.',
    },
    'UNEF': {
        'function': 'Unified Inch Extra-Fine — very fine pitch.  Used where wall thickness, length of engagement, or fine adjustment is critical.',
        'where_used': 'Sheet-metal locknuts, instrument adjusters, optical equipment, thin-wall tubing nuts, aerospace bearings.',
        'when_to_choose': 'Thin sections or where UNF pitch is still too coarse.',
    },
    'UNJ': {
        'function': 'UN with mandatory rounded root radius.  Eliminates root stress concentration → significantly better fatigue life.  Cannot be cut by a standard UN tap.',
        'where_used': 'Aerospace airframe and engine fasteners, military, high-cycle-fatigue parts (turbine bolts, helicopter dynamic components).',
        'when_to_choose': 'Spec-mandated for aerospace; or when fatigue is the limiting design factor.',
    },
    'MJ': {
        'function': 'Metric counterpart of UNJ — controlled rounded root for fatigue performance.',
        'where_used': 'Metric aerospace fasteners (Airbus, Embraer, ESA), military aerospace where metric tooling is preferred.',
        'when_to_choose': 'Metric aerospace fastener spec.',
    },
    'BSW': {
        'function': 'Whitworth coarse — 55° rounded crests AND roots, gentle thread form.  Lower stress concentration than V-thread, more tolerant of dirt and damage.',
        'where_used': 'Legacy British engineering, vintage machinery restoration, plumbing, scaffolding, marine, India and former Commonwealth countries that retain BSW for structural use.',
        'when_to_choose': 'Repair/replacement of existing BSW components.  Rarely chosen for new design.',
    },
    'BSF': {
        'function': 'Whitworth Fine.',
        'where_used': 'Vintage British automotive, motorcycle, instrument and machine-tool components.',
        'when_to_choose': 'Restoration / spares for legacy BSF fittings.',
    },
    'BSP': {
        'function': 'Parallel pipe thread (G).  Sealing is achieved by a SEPARATE element (O-ring, bonded washer, flat gasket) — NOT by the threads.  Threads only provide mechanical engagement.',
        'where_used': 'Hydraulics, pneumatics, fluid-power fittings worldwide outside North America.  Adapter fittings, bulkhead unions, hose tails, valves, lubrication.',
        'when_to_choose': 'Threaded port that uses an O-ring or face seal.',
    },
    'BSPT': {
        'function': 'Tapered pipe thread (R / Rc).  55° profile with 1:16 taper.  Threads themselves form the seal as the male wedges into the female (often with PTFE tape or sealant).',
        'where_used': 'Plumbing (water, gas), low/medium-pressure pipe fittings, gauges, drain plugs in countries using BS/ISO 7-1.',
        'when_to_choose': 'Pipe joint that must be sealed by the thread itself, in a country using BSP convention.',
    },
    'NPT': {
        'function': 'American tapered pipe thread.  60° profile with 1:16 taper.  Threads seal as male wedges into female with sealant (PTFE tape, pipe dope).',
        'where_used': 'Plumbing, gas, hydraulic, pneumatic, instrumentation pipe fittings throughout North America.',
        'when_to_choose': 'Threaded pipe joint sealed by the thread, North-American convention.',
    },
    'NPTF': {
        'function': 'NPT Dryseal — controlled crest/root interference creates metal-to-metal seal WITHOUT sealant.',
        'where_used': 'Hydraulic systems on aerospace and military equipment, fuel-injection, oxygen, breathing-air, food/pharma plumbing, refrigeration.',
        'when_to_choose': 'Sealed pipe joint that must not introduce thread sealant into the system.',
    },
    'ANPT': {
        'function': 'Aeronautical NPT — same dimensions as NPT but with Class-3 pitch-dia tolerance and functional-thread-gauge inspection.  Higher reliability than commercial NPT.',
        'where_used': 'Aerospace fluid systems: aircraft fuel, hydraulic, pneumatic, oxygen lines.  All major airframe and engine OEMs.',
        'when_to_choose': 'Aviation-spec drawing calls out ANPT or AS71051.',
    },
    'NPSM': {
        'function': 'Straight (parallel) NPT-form pipe thread for MECHANICAL fittings.  No taper — sealing via separate gasket or O-ring.',
        'where_used': 'Locknuts, bushings, mechanical pipe joints that don\'t need pressure seal at the thread.',
        'when_to_choose': 'Lock-nut application, or where the thread is purely structural.',
    },
    'NPSL': {
        'function': 'Straight pipe thread for locknuts (slightly larger than NPSM).  Mates with the back-end of an NPT fitting.',
        'where_used': 'Locknuts on bulkhead penetrations, panel-mount NPT fittings.',
        'when_to_choose': 'Bulkhead or panel-mount NPT fittings requiring a back-side locknut.',
    },
    'NPSC': {
        'function': 'Straight pipe thread for COUPLINGS.',
        'where_used': 'Inside diameter of pipe couplings.',
        'when_to_choose': 'Coupling internal thread.',
    },
    'Acme': {
        'function': '29° symmetric trapezoidal thread.  Larger flank area than V-thread → higher load capacity, lower friction, easier to cut/repair.  Designed for translating motion.',
        'where_used': 'Lead-screws on lathes, machine tools, vises, jacks, valve stems, linear actuators, screw-presses, vehicle steering boxes.',
        'when_to_choose': 'Power transmission or linear motion.  When the screw needs to MOVE a load along its axis.',
    },
    'Stub_Acme': {
        'function': 'Acme with shortened thread height (0.3·P).  Used where there isn\'t enough wall thickness for full-depth Acme.',
        'where_used': 'Thin-wall lead-screws, light-duty actuators, valve stems on small valves.',
        'when_to_choose': 'Need Acme but limited by wall thickness or weight.',
    },
    'TR': {
        'function': 'Metric trapezoidal — equivalent to Acme but with 30° included angle.  Same use-case: power transmission and linear motion.',
        'where_used': 'European machine tools, jacks, presses, valve stems, leadscrews, screw-jacks for height adjustment.',
        'when_to_choose': 'Metric power-screw or linear-motion application.',
    },
    'Buttress': {
        'function': 'Asymmetric (BS 1657: 7° load flank, 45° back flank).  Carries axial load in ONE direction with very high efficiency.  Load flank is nearly perpendicular to axis → minimal radial separation force.',
        'where_used': 'Hydraulic press rams, screw-jacks, vise screws, breech blocks on artillery, cap closures (jars, PET bottles), heavy lifting screws.',
        'when_to_choose': 'Axial load is one-directional and high.',
    },
    'API_Buttress': {
        'function': 'Modified buttress for oilfield casing (API 5B BC).  Load 3° from radial, stab 10° from radial.  Provides high tensile and burst strength with quick makeup.',
        'where_used': 'Oil and gas casing connections (OCTG) — surface, intermediate, and production casing strings in conventional wells.',
        'when_to_choose': 'Standard casing connection where premium/gas-tight connections aren\'t required.',
    },
    'API_Round_8': {
        'function': '60° V-thread, 8 TPI, 1:16 taper (8-Round STC/LC).  Sealing via thread compound — no metal-to-metal seal.',
        'where_used': 'Surface and intermediate oil/gas well casing.  Lowest-cost casing connection.  Common in vertical wells and low-pressure production.',
        'when_to_choose': 'Cost-driven casing selection where premium performance not required.',
    },
    'API_Round_10': {
        'function': '60° V-thread, 10 TPI, 1:16 taper.  Tubing connection — EUE (External Upset End) or NUE (Non-Upset End).',
        'where_used': 'Production tubing strings (the inner pipe carrying produced fluids to surface).',
        'when_to_choose': 'Standard tubing connection.  EUE preferred for deeper/higher-pressure wells.',
    },
    'API_RSC': {
        'function': 'Rotary Shouldered Connection — sealing AND torque transmission via a TORQUE SHOULDER (not the threads).  Threads are 60° rounded V with heavy taper (1:6 or 1:4) and connect by stab-and-make-up.',
        'where_used': 'Drill string connections — drill pipe tool joints, drill collars, kellys, BHA components, bits.  Rotary drilling for oil, gas, geothermal, and large mineral exploration.  Sizes from NC23 (small core) to NC77 (very large drill collars).',
        'when_to_choose': 'Anywhere torque must be transmitted through the connection to a downhole tool.',
    },
    'API_Macaroni': {
        'function': 'Slim-OD oilfield connection.  Same V-0.055 thread form as small API rounds, on smaller pipe.  Allows production tubing to be run inside existing tubing/casing for workovers and slim-hole completions.',
        'where_used': 'Through-tubing rework / fishing string runs, gas-lift mandrels, capillary injection lines, slim-completion strings, slim-hole mining exploration tubing.',
        'when_to_choose': 'OD-restricted oilfield/mining application requiring a threaded tubular connection.',
    },
    'Mining': {
        'function': 'Drill-rod thread for percussion (top-hammer) and rotary mining drills.  Robust rounded-V (60°, large root radius) cut on hexagonal or round rods of high-toughness alloy steel.  Threads must withstand impact loading thousands of times per second from the hammer.',
        'where_used': 'R-thread (R25/R28/R32/R38) and T-thread (T38/T45/T51/T60) on top-hammer drilling.  ST tube-rod threads on long-hole production drilling.  GD and Boart-Longyear threads on diamond core exploration.  Quarrying, blast-hole drilling, ground anchoring, geothermal exploration.',
        'when_to_choose': 'Drill-rod, shank, sleeve, or bit thread for a specific drill manufacturer.  Always verify exact spec from the drill maker.',
    },
    'Saw': {
        'function': 'Asymmetric — vertical (0°) leading flank, 30° trailing flank.  Most aggressive load-bearing geometry.  Almost no radial separation force.',
        'where_used': 'Heavy industrial presses, mining equipment, large lifting screws, shipbuilding rigging.',
        'when_to_choose': 'Extreme one-directional axial load where Buttress isn\'t enough.',
    },
    'Round': {
        'function': 'Fully rounded crest AND root, 30° included.  Tolerates extreme dirt, scale, paint, sand.  Self-clearing.',
        'where_used': 'Railroad coupling screws, fire-hose couplings, hydrant outlets, glass jar lids (Mason jars), hose threading (fire/garden), some agricultural implements.',
        'when_to_choose': 'Field environment where the thread will encounter dirt, ice, paint, or rust frequently.',
    },
    'PG': {
        'function': '80° conduit thread with rounded crest and root.  Designed for repeated assembly and weather sealing.',
        'where_used': 'Cable glands, conduit fittings, lighting fixtures, motor terminal boxes — older and current European electrical installations.',
        'when_to_choose': 'Replacing or matching existing PG-spec electrical fittings.',
    },
    'Edison': {
        'function': 'Lamp-base thread for screw-in light bulbs.  60° V form with specific dia/pitch for each cap size.',
        'where_used': 'Light bulbs and lampholders — E10 (torches, indicator lamps), E14 (chandeliers, candle bulbs), E27 (standard household), E40 (industrial / street lighting).',
        'when_to_choose': 'Lamp socket or bulb base manufacture.',
    },
    'DIN_477': {
        'function': 'Gas-cylinder valve outlet thread.  Each NUMBERED connection is reserved for a specific gas service.  Hand of thread (RH or LH) is part of the safety coding to prevent dangerous mis-connection between fuel gases and oxidisers.',
        'where_used': 'Industrial gas cylinders worldwide using the DIN/ISO connection system — oxygen, acetylene, propane, LPG, hydrogen, nitrogen, argon, helium, CO2, refrigerants, medical gases.',
        'when_to_choose': 'Manufacture/repair of gas cylinder valves or pressure regulators.  ALWAYS verify against current ISO 5145 / EN ISO 11363 for the target gas — connection assignments occasionally change for safety harmonisation.',
    },
}


# U225: family aliases — thread builders sometimes set spec.family to a
# bare group name ('M', 'NPT', etc) rather than the specific series code
# ('M_coarse', 'NPT', ...).  Map back to the dict keys used by REFERENCES
# and USE_CASES so the Thread Info tab gets populated either way.
_FAMILY_ALIASES = {
    'M':            'M_coarse',     # bare 'M' from make_iso_m()
    'M_metric':     'M_coarse',
    'Metric':       'M_coarse',
    'UN':           'UNC',
    'Whitworth':    'BSW',
    # Specific series families (UNC, UNF, BSP, BSPT, NPT, etc) already
    # match the dict keys directly — no alias needed.
}


def _resolve_family_key(family: str) -> str:
    """Resolve aliases (e.g. 'M' → 'M_coarse') so REFERENCES /
    USE_CASES lookups don't miss when the spec carries a bare group
    name."""
    if not family:
        return family
    if family in REFERENCES or family in USE_CASES:
        return family
    return _FAMILY_ALIASES.get(family, family)


def use_case(family: str) -> dict:
    """Return FUNCTIONALITY / USE-CASE info for a thread family.
    Keys: 'function' (what the profile does mechanically),
          'where_used' (typical industries and applications),
          'when_to_choose' (decision guidance for the engineer)."""
    key = _resolve_family_key(family)
    return USE_CASES.get(key, {
        'function': '(no use-case info recorded for this family)',
        'where_used': '',
        'when_to_choose': '',
    })


def reference_for(family: str) -> str:
    """Return the publication-level reference citation for a thread family."""
    key = _resolve_family_key(family)
    return REFERENCES.get(key, 'No reference recorded for this family.')


# =============================================================================
# 2D PROFILE GENERATION (SVG) — visualises the thread cross-section.
# =============================================================================

def iso_basic_profile_svg(spec: ThreadSpec, width_px: int = 600,
                          height_px: int = 360, n_teeth: int = 2) -> str:
    """U228h: Canonical ISO 68-1 / ISO 261 basic-profile reference
    diagram for 60° symmetric V threads (Metric, UN, MJ, UNJ).

    Shows the single basic profile (truncated V) as the boundary
    between internal-thread material (top) and external-thread
    material (bottom).  Tinted zones distinguish internal (subtle
    blue) from external (subtle orange).  All standard dimension
    labels:
        Horizontal: P, P/2, P/4, P/8
        Vertical:   H, H/8, 3H/8, 5H/8, H/4
        Angles:     60° (apex), 30° (half-flank), 90° (axis)
    Diameter symbols (D/d, D2/d2, D1/d1) on the left margin point
    to the corresponding horizontal reference (no numerical values
    — those live in the Thread Info text panel below).

    U228n: width_px / height_px arguments are ignored — the SVG canvas
    is sized to match the V's natural aspect ratio (width = n_teeth·P,
    height = H plus material-zone padding).  The renderer then scales
    this fixed-aspect SVG to fit whatever widget area is available
    while preserving the geometry.  This is the only reliable way to
    keep the 60° apex looking like a real 60° regardless of how Qt or
    the SVG renderer is configured to handle aspect ratio.
    """
    P = spec.pitch
    H = math.sqrt(3) / 2.0 * P              # 0.866 P, full sharp height
    if P <= 0 or H <= 0:
        return profile_svg(spec, width_px, height_px, n_teeth=n_teeth)

    # U231c: pixel-based canvas, NOT mm-based.  This way for very
    # small pitches (e.g. M100×0.3 where H ≈ 0.26 mm) the canvas
    # doesn't shrink and force the renderer to magnify everything
    # (which used to make text labels appear giant).
    #
    # The canvas size is taken DIRECTLY from the widget.  Inside,
    # the V geometry is scaled to fit the available area while
    # keeping isotropic proportions (60° apex stays 60°).  Padding
    # and label sizes are in fixed pixels so they look the same
    # regardless of pitch.
    if width_px <= 0 or height_px <= 0:
        width_px, height_px = 1200, 400
    pad_x_left  = 130           # left gutter for D / D2 / D1 labels (px)
    pad_x_right = 80            # right gutter for H dimension (px)
    # U231d: title + footer text removed at user request → pad shrunk
    # so the V profile expands into the freed vertical space.
    pad_top     = 22            # top gutter for the P dimension only (px)
    pad_bot     = 28            # bottom gutter for axis line + 90° label (px)
    avail_w = max(50, width_px - pad_x_left - pad_x_right)
    avail_h = max(50, height_px - pad_top - pad_bot)

    # World-coordinate key levels (y = mm above sharp valley):
    sharp_peak    = H                       # tip of sharp triangle
    ext_crest     = 7 * H / 8.0             # external crest = D, internal root
    pitch_y       = H / 2.0                 # pitch line / D2 (= d2)
    ext_root      = H / 4.0                 # external root = d1, internal crest
    sharp_valley  = 0.0
    # Tooth widths at each level (centred on the V apex).
    half_top = P * (1.0 / 8.0) / 2.0        # P/8 wide flat at peak
    half_bot = P * (1.0 / 4.0) / 2.0        # P/4 wide flat at valley

    # World-coordinate (mm) span of the drawn region.
    # U231h: anchor the drawn span to the TRUNCATED V (ext_root to
    # ext_crest) instead of the SHARP V (sharp_valley to sharp_peak).
    # This eliminates the H/8 above-crest and H/4 below-root empty
    # bands that were dominating the previous canvas — the V profile
    # now occupies ~83% of the drawn area instead of ~52%.
    v_height_mm = ext_crest - ext_root           # = 5H/8 (cut depth)
    extra_zone_mm = v_height_mm * 0.08           # 8% extra above/below for labels
    top_y_world    = ext_crest + extra_zone_mm
    bottom_y_world = ext_root  - extra_zone_mm
    span_y_mm = top_y_world - bottom_y_world     # ≈ 1.16 × v_height

    # Pick n_teeth (2-3) so each tooth is wide enough to read
    # comfortably.  User asked: 3 teeth is OK, prefer fewer-but-
    # bigger teeth over many-but-small.
    s_height_limited = avail_h / span_y_mm if span_y_mm > 0 else 100.0
    teeth_target = avail_w / (P * s_height_limited) if P > 0 else 2.0
    n_teeth = max(2, min(3, int(round(teeth_target))))

    span_x_mm = n_teeth * P
    # Final isotropic scale that fits both axes (use the smaller).
    scale = min(avail_w / span_x_mm if span_x_mm > 0 else 1,
                avail_h / span_y_mm if span_y_mm > 0 else 1)

    # Canvas layout — pixel-based now.  scale (px-per-mm) varies
    # with pitch so the V always fills the available area.  Padding
    # and label sizes stay fixed in pixels.
    span_x_world = span_x_mm
    span_y_world = span_y_mm
    scale_x = scale_y = scale

    # Pixel anchors.
    cx = pad_x_left + avail_w / 2
    drawn_w = span_x_world * scale
    drawn_h = span_y_world * scale
    x_origin = cx - drawn_w / 2.0
    cy = pad_top + avail_h / 2.0
    # U231h: anchor y_axis_zero so the world midpoint of the drawn
    # span maps to the screen centre.  Keeps the V vertically
    # centred between the thin INTERNAL/EXTERNAL THREAD margins.
    cy_world = (top_y_world + bottom_y_world) / 2.0
    y_axis_zero = cy + cy_world * scale

    def W(xw, yw):
        sx = x_origin + (xw + n_teeth * P / 2.0) * scale
        sy = y_axis_zero - yw * scale
        return sx, sy

    # ============= Basic profile path (truncated V, repeated) =============
    # U228q: rebuilt with explicit valley-flat segments at the start
    # and end so the leading and trailing flanks have the same 30°
    # slope as the interior flanks.  The previous code skipped the
    # leading valley flat which made the first flank visually
    # shallower than the rest.
    #
    # Geometry of one tooth period (P) — origin at valley CENTRE:
    #     -half_bot to +half_bot   : valley flat
    #     +half_bot to +half_bot+flank_dx  : rising flank
    #     ... peak flat 2*half_top wide ...
    #     down the falling flank
    #     ends at +P-half_bot, ready to enter next valley flat.
    flank_dx = (ext_crest - ext_root) * math.tan(math.radians(30.0))
    path_pts = []
    x_left = -n_teeth * P / 2.0          # leading half-valley centre
    # Leading half-valley: start from left edge at root level.
    path_pts.append((x_left, ext_root))
    for k in range(n_teeth):
        vc = x_left + k * P              # valley centre to the LEFT of tooth k
        # Right edge of valley flat = left base of rising flank.
        path_pts.append((vc + half_bot, ext_root))
        # Top of rising flank = left edge of peak flat.
        path_pts.append((vc + half_bot + flank_dx, ext_crest))
        # Right edge of peak flat.
        path_pts.append((vc + half_bot + flank_dx + 2 * half_top, ext_crest))
        # Bottom of falling flank = left edge of NEXT valley flat.
        path_pts.append((vc + P - half_bot, ext_root))
    # Trailing half-valley: extend at root level to right edge.
    path_pts.append((x_left + n_teeth * P, ext_root))

    # SVG path from points.
    pts_svg = []
    for i, (xw, yw) in enumerate(path_pts):
        sx, sy = W(xw, yw)
        pts_svg.append(f'{"M" if i == 0 else "L"} {sx:.2f},{sy:.2f}')
    profile_path = ' '.join(pts_svg)

    # ============= Hatched / tinted zones =============
    # U228k: extend zones across the FULL panel width (not just the
    # profile span) so isotropic scaling doesn't leave bare side
    # gutters.  Internal zone: from canvas top down to the profile.
    # External zone: profile down to canvas bottom.
    top_y    = pad_top
    bot_y    = pad_top + avail_h
    canvas_left  = pad_x_left
    canvas_right = width_px - pad_x_right
    # First profile point is at left of profile span (ext_root);
    # last is at right.  We extend horizontally from the profile's
    # ends to the canvas edges at the SAME y (ext_root level) so
    # the zone fill continues outside the drawn V's.
    first_sx, first_sy = W(path_pts[0][0], path_pts[0][1])
    last_sx,  last_sy  = W(path_pts[-1][0], path_pts[-1][1])
    int_poly = (
        f'M {canvas_left:.2f},{top_y} '
        f'L {canvas_left:.2f},{first_sy:.2f} '
        + ' '.join(f'L {W(xw, yw)[0]:.2f},{W(xw, yw)[1]:.2f}'
                   for xw, yw in path_pts)
        + f' L {canvas_right:.2f},{last_sy:.2f} '
        f'L {canvas_right:.2f},{top_y} Z'
    )
    ext_poly = (
        f'M {canvas_left:.2f},{bot_y} '
        f'L {canvas_left:.2f},{first_sy:.2f} '
        + ' '.join(f'L {W(xw, yw)[0]:.2f},{W(xw, yw)[1]:.2f}'
                   for xw, yw in path_pts)
        + f' L {canvas_right:.2f},{last_sy:.2f} '
        f'L {canvas_right:.2f},{bot_y} Z'
    )

    # ============= Reference lines =============
    # U228k: span the full canvas width so dia labels (left) connect
    # to dimension column (right) regardless of the profile's
    # centred position.
    refs = []
    def hline(yw, color='#888', dash=''):
        _, sy = W(0, yw)
        d = f'stroke-dasharray="{dash}"' if dash else ''
        refs.append(
            f'<line x1="{canvas_left:.2f}" y1="{sy:.2f}" '
            f'x2="{canvas_right:.2f}" y2="{sy:.2f}" '
            f'stroke="{color}" stroke-width="1" {d}/>')

    # U228r: removed sharp_peak / sharp_valley dashed references —
    # they're only meaningful when paired with H/8 and H/4 truncation
    # labels, which are no longer displayed.  Cleaner without them.
    hline(ext_crest,    '#444')          # crest line  (Major Dia ref)
    hline(pitch_y,      '#1F4E79', '6 4')# pitch line  (Pitch Dia ref)
    hline(ext_root,     '#444')          # root line   (Minor Dia ref)

    # ============= Axis line (workpiece centerline) =============
    # Below the drawing, dashed, with 90° marker.
    axis_y = pad_top + avail_h + 6
    axis_line = (
        f'<line x1="{pad_x_left}" y1="{axis_y}" '
        f'x2="{width_px - pad_x_right}" y2="{axis_y}" '
        f'stroke="#1F4E79" stroke-width="1" stroke-dasharray="6 3 1 3"/>'
    )

    # ============= Dimension labels =============
    labels = []
    fnt = 'font-family="Segoe UI, sans-serif"'
    sm  = f'{fnt} font-size="9" fill="#444"'
    md  = f'{fnt} font-size="10" fill="#1F4E79" font-weight="bold"'

    # ----- Right-side vertical dimension: actual thread height H -----
    # U228r: only ONE dimension on the right — the ACTUAL thread
    # height, measured from Major Dia (crest line) to Minor Dia
    # (root line).  No theoretical-V truncations (H/8, 3H/8, H/4,
    # 5H/8) — those were noise.  Just label "H" with arrows; the
    # numerical value is read from the text panel below.
    rx = width_px - pad_x_right + 10       # right column x
    sx_cr, sy_cr = W(0, ext_crest)
    sx_rt, sy_rt = W(0, ext_root)
    labels.append(
        f'<line x1="{rx}" y1="{sy_cr:.2f}" x2="{rx}" y2="{sy_rt:.2f}" '
        f'stroke="#444" stroke-width="1" '
        f'marker-start="url(#arrow)" marker-end="url(#arrow)"/>'
    )
    # Short ticks at endpoints aligned with crest/root lines.
    labels.append(
        f'<line x1="{rx - 6}" y1="{sy_cr:.2f}" '
        f'x2="{rx + 4}" y2="{sy_cr:.2f}" '
        f'stroke="#444" stroke-width="0.5"/>'
    )
    labels.append(
        f'<line x1="{rx - 6}" y1="{sy_rt:.2f}" '
        f'x2="{rx + 4}" y2="{sy_rt:.2f}" '
        f'stroke="#444" stroke-width="0.5"/>'
    )
    labels.append(
        f'<text x="{rx + 6}" y="{(sy_cr + sy_rt)/2 + 4:.2f}" {md}>H</text>'
    )

    # ----- Top horizontal dimensions: P (between peak centres), P/2, P/4, P/8 -----
    # P spanning the first full tooth: peak-centre to next peak-centre.
    p_y_top = pad_top + 8
    sx_p1, _ = W(-n_teeth * P / 2.0 + P / 2.0, ext_crest)
    sx_p2, _ = W(-n_teeth * P / 2.0 + 3 * P / 2.0, ext_crest) if n_teeth > 1 else (sx_p1 + P * scale_x, 0)
    labels.append(
        f'<line x1="{sx_p1:.2f}" y1="{p_y_top}" x2="{sx_p2:.2f}" y2="{p_y_top}" '
        f'stroke="#1F4E79" stroke-width="1" '
        f'marker-start="url(#arrow)" marker-end="url(#arrow)"/>'
    )
    labels.append(
        f'<text x="{(sx_p1 + sx_p2)/2:.2f}" y="{p_y_top - 3}" '
        f'text-anchor="middle" {md}>P</text>'
    )

    # P/8 across the truncated peak of the FIRST tooth (the tooth on the left).
    cx0_w = -n_teeth * P / 2.0 + P / 2.0
    sx_e1, sy_e1 = W(cx0_w - half_top, ext_crest)
    sx_e2, sy_e2 = W(cx0_w + half_top, ext_crest)
    p8_y = sy_e1 - 8
    labels.append(
        f'<line x1="{sx_e1:.2f}" y1="{p8_y}" x2="{sx_e2:.2f}" y2="{p8_y}" '
        f'stroke="#444" stroke-width="0.8" '
        f'marker-start="url(#arrow)" marker-end="url(#arrow)"/>'
    )
    labels.append(
        f'<text x="{(sx_e1 + sx_e2)/2:.2f}" y="{p8_y - 3}" '
        f'text-anchor="middle" {sm}>P/8</text>'
    )

    # P/4 across the truncated valley between teeth.
    val_x_w = -n_teeth * P / 2.0 + P     # midpoint between teeth 0 & 1
    sx_v1, sy_v1 = W(val_x_w - half_bot, ext_root)
    sx_v2, sy_v2 = W(val_x_w + half_bot, ext_root)
    p4_y = sy_v1 + 14
    labels.append(
        f'<line x1="{sx_v1:.2f}" y1="{p4_y}" x2="{sx_v2:.2f}" y2="{p4_y}" '
        f'stroke="#444" stroke-width="0.8" '
        f'marker-start="url(#arrow)" marker-end="url(#arrow)"/>'
    )
    labels.append(
        f'<text x="{(sx_v1 + sx_v2)/2:.2f}" y="{p4_y + 11}" '
        f'text-anchor="middle" {sm}>P/4</text>'
    )

    # ----- Left-side diameter labels (Major / Pitch / Minor Dia) -----
    # U228r: changed from "D / d" symbols to plain-English labels.
    # All point to the SAME horizontal reference because internal &
    # external threads share the basic profile.
    lx_text = 6
    lx_arrow = pad_x_left - 8
    def left_dim(yw, sym):
        _, sy = W(0, yw)
        labels.append(
            f'<line x1="{lx_arrow}" y1="{sy:.2f}" '
            f'x2="{lx_arrow + 8}" y2="{sy:.2f}" '
            f'stroke="#1F4E79" stroke-width="0.8"/>'
        )
        labels.append(
            f'<text x="{lx_text}" y="{sy + 4:.2f}" {md}>{sym}</text>'
        )
    left_dim(ext_crest, 'Major Dia')
    left_dim(pitch_y,   'Pitch Dia')
    left_dim(ext_root,  'Minor Dia')

    # ----- Angle markers -----
    # U228r: show TWO 30° markers (one each side of a vertical
    # centerline through the apex) instead of one 60° at the apex.
    # This matches the user's reference sketch and reads as
    # "flank angle from centerline" — same convention machinists
    # use when grinding tools.
    md_red = (f'{fnt} font-size="10" fill="#C62828" '
              f'font-weight="bold"')   # red bold, no duplicate fill
    cx0_w = -n_teeth * P / 2.0 + P / 2.0    # first tooth apex (peak centre)
    sx_apex, sy_apex = W(cx0_w, ext_crest)
    sx_root_apex, sy_root_apex = W(cx0_w, ext_root)
    # The IMPLIED SHARP apex is one truncation (H/8) above the
    # truncated peak — it's where the flanks would meet if extended.
    # Place the angle-marker arc centre there so the arc sweeps from
    # the vertical centreline outward to the flank line.
    sx_sharp, sy_sharp = W(cx0_w, ext_crest + H / 8.0)
    # Vertical centerline through the apex, dashed red, extending
    # from the apex down through the axis line for clarity.
    labels.append(
        f'<line x1="{sx_sharp:.2f}" y1="{sy_sharp:.2f}" '
        f'x2="{sx_sharp:.2f}" y2="{axis_y:.2f}" '
        f'stroke="#C62828" stroke-width="0.8" '
        f'stroke-dasharray="4 3"/>'
    )
    # U228w/U228y: angle arcs INSIDE the V.  Per user sketch:
    #   - Arrows START on the centreline (lower position inside the V)
    #   - Arrows END on the FLANK (arrow heads land on each flank)
    #   - 30° labels sit BELOW each arc — well clear of the arrow head
    #     which is now at the upper-outer end of the arc.
    # arc_radius pushed to 0.70 so the arc sits low enough that the
    # label has room beneath it.
    arc_radius = (sy_root_apex - sy_sharp) * 0.70
    sin30 = 0.5
    cos30 = math.cos(math.radians(30.0))
    centre_pt = (sx_sharp, sy_sharp + arc_radius)         # on centreline
    left_pt   = (sx_sharp - arc_radius * sin30,
                 sy_sharp + arc_radius * cos30)           # on left flank
    right_pt  = (sx_sharp + arc_radius * sin30,
                 sy_sharp + arc_radius * cos30)           # on right flank

    # U230b: explicit symmetry — both arc endpoints are exact mirror
    # images of each other about the centreline (sx_sharp).  Both
    # labels sit at the SAME vertical coordinate, equidistant from
    # the centreline.  No subtle x/y offset that could make one side
    # look heavier than the other.
    label_off_x = 6                              # px each side of centre
    label_off_y = 14                             # px below centre_pt
    label_y = centre_pt[1] + label_off_y

    # Left-side arc — centreline → LEFT flank.  Sweep CW in SVG.
    labels.append(
        f'<path d="M {centre_pt[0]:.2f},{centre_pt[1]:.2f} '
        f'A {arc_radius:.2f} {arc_radius:.2f} 0 0 1 '
        f'{left_pt[0]:.2f},{left_pt[1]:.2f}" '
        f'stroke="#C62828" stroke-width="0.9" fill="none" '
        f'marker-end="url(#arrow_red)"/>'
    )
    labels.append(
        f'<text x="{centre_pt[0] - label_off_x:.2f}" '
        f'y="{label_y:.2f}" '
        f'text-anchor="end" dominant-baseline="middle" '
        f'{md_red}>30°</text>'
    )

    # Right-side arc — centreline → RIGHT flank.  Sweep CCW in SVG
    # (mirror of left arc — endpoints, sweep direction, label
    # offsets all symmetric).
    labels.append(
        f'<path d="M {centre_pt[0]:.2f},{centre_pt[1]:.2f} '
        f'A {arc_radius:.2f} {arc_radius:.2f} 0 0 0 '
        f'{right_pt[0]:.2f},{right_pt[1]:.2f}" '
        f'stroke="#C62828" stroke-width="0.9" fill="none" '
        f'marker-end="url(#arrow_red)"/>'
    )
    labels.append(
        f'<text x="{centre_pt[0] + label_off_x:.2f}" '
        f'y="{label_y:.2f}" '
        f'text-anchor="start" dominant-baseline="middle" '
        f'{md_red}>30°</text>'
    )
    # 90° at axis line (kept — useful reference for the workpiece axis).
    labels.append(
        f'<text x="{pad_x_left + 14}" y="{axis_y - 3}" {md}>90°</text>'
    )

    # ----- Zone tags (no title — removed per user request U231d) -----
    title = ''   # title text suppressed; size/family info is in the data panel below
    # Zone tags inside hatched material areas.
    int_tag = (
        f'<text x="{cx + 30}" y="{pad_top + 16}" '
        f'{fnt} font-size="11" font-weight="bold" fill="#1F4E79" '
        f'opacity="0.75">INTERNAL THREAD</text>'
    )
    ext_tag = (
        f'<text x="{cx + 30}" y="{pad_top + avail_h - 12}" '
        f'{fnt} font-size="11" font-weight="bold" fill="#A65900" '
        f'opacity="0.75">EXTERNAL THREAD</text>'
    )

    # ----- Footer -----
    # U231d: footer text removed at user request — H value is in the
    # data panel below; the SVG no longer needs to repeat it.
    footer = ''

    arrow_def = (
        '<defs>'
        '<marker id="arrow" markerWidth="6" markerHeight="6" '
        'refX="3" refY="3" orient="auto">'
        '<path d="M0,0 L6,3 L0,6 z" fill="#444"/></marker>'
        # U228r: red arrow for the 30° angle arcs.
        '<marker id="arrow_red" markerWidth="6" markerHeight="6" '
        'refX="3" refY="3" orient="auto">'
        '<path d="M0,0 L6,3 L0,6 z" fill="#C62828"/></marker>'
        '</defs>'
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" '
        f'height="{height_px}" viewBox="0 0 {width_px} {height_px}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'{arrow_def}'
        f'<rect width="{width_px}" height="{height_px}" fill="#fafafa"/>'
        # Tinted zones: internal (cool blue tint), external (warm orange tint).
        f'<path d="{int_poly}" fill="#1976D2" fill-opacity="0.10" '
        f'stroke="none"/>'
        f'<path d="{ext_poly}" fill="#E65100" fill-opacity="0.10" '
        f'stroke="none"/>'
        + ''.join(refs) +
        # The basic profile outline drawn LAST so it sits on top.
        f'<path d="{profile_path}" stroke="#000" stroke-width="2" '
        f'fill="none"/>'
        + axis_line
        + title + int_tag + ext_tag
        + ''.join(labels)
        + footer +
        '</svg>'
    )
    return svg


def profile_svg(spec: ThreadSpec, width_px: int = 600, height_px: int = 360,
                show_dims: bool = True, n_teeth: int = 3,
                side: str = 'External') -> str:
    """Return an SVG string drawing the 2D axial cross-section of a thread
    profile — TILED across `n_teeth` pitches so the user sees the
    repeating shape, not just one isolated tooth.  Renders flank angles,
    crest flat or radius, root flat or radius, and pitch line.  Handles
    symmetric profiles (ISO M, UN, Whitworth, Acme) AND asymmetric ones
    (Buttress 7°/45°, API Buttress 3°/10°, Saw 0°/30°).

    U228g: ``side`` selects which dia gets the 'Major / Pitch / Minor'
    labels.  External: crest = Major, root = Minor.  Internal: crest =
    Minor (bore wall), root = Major (deepest cut).  Labels Major Dia,
    Pitch Dia, Minor Dia, Pitch (P), and Height (h) are drawn on the
    diagram so the operator sees the engineering meaning of every line.
    """
    P = spec.pitch
    # Use the ACTUAL machined depth (height_external, fall back to
    # height_internal then height_basic).  height_basic is often the
    # theoretical sharp-V H = 0.866·P which makes teeth fill the
    # entire pitch — the truncated profile (flat crest + root) is
    # what we want to draw, so use the cut-depth value.
    h = (spec.height_external or spec.height_internal
         or spec.height_basic or (P * 0.5))
    fl = spec.flank_leading if spec.flank_leading is not None else 30.0
    ft = spec.flank_trailing if spec.flank_trailing is not None else 30.0
    crest_flat = spec.crest_truncation or 0.0
    root_rad   = spec.root_radius or 0.0

    # Per-tooth geometry in WORLD coordinates (mm), centred at x=0.
    # flank_dx = horizontal length of the flank from y=0 (root) up to y=h.
    # Convention: flank angle is "from RADIAL" — so flank line tilts
    # from vertical by `fl` degrees → horizontal extent over height h
    # = h * tan(fl).  (For ISO M fl=30°, dx = h * tan(30°) = h * 0.577.)
    flank_lead_dx  = h * math.tan(math.radians(fl))
    flank_trail_dx = h * math.tan(math.radians(ft))
    # Width of the crest (flat or zero for sharp peak).  For Whitworth /
    # round / API rounded threads the value is a radius, but treat it as
    # a flat for drawing purposes (the polyline approximation is fine).
    half_crest = crest_flat / 2.0
    # Half-width of the tooth at the root level (y=0).
    tooth_base_left  = -(half_crest + flank_lead_dx)
    tooth_base_right = +(half_crest + flank_trail_dx)
    tooth_base_width = tooth_base_right - tooth_base_left
    # Root flat width (= P − tooth base) — fills the gap between teeth.
    root_flat = P - tooth_base_width
    if root_flat < 0:
        # Tooth wider than pitch (shouldn't happen for valid threads,
        # but for asymmetric profiles with tiny pitch it could).  Clip
        # the trailing flank to fit.
        root_flat = 0.0

    # Drawing area: fit `n_teeth` pitches horizontally AND fill the
    # available vertical height fully — using INDEPENDENT X and Y scale
    # so the profile uses the full canvas without leaving big empty
    # margins.  This stretches the drawing slightly in the Y direction
    # (when the canvas aspect is wider than the natural thread aspect),
    # which is acceptable for visualisation — the angles shown are
    # SCHEMATIC, exact values are listed in the data table next to it.
    pad_x = 18            # tight horizontal margins
    pad_top = 50          # space for title/dims at top
    pad_bot = 28          # space for footer at bottom
    span_x_world = n_teeth * P
    span_y_world = h * 1.05      # near-zero vertical padding around tooth
    avail_w = width_px - 2 * pad_x
    avail_h = height_px - pad_top - pad_bot
    # Independent scales — fill both axes.
    scale_x = avail_w / span_x_world
    scale_y = avail_h / span_y_world if span_y_world > 0 else scale_x
    # Cap the Y stretch so the drawing doesn't get absurdly tall on
    # very wide canvases — ratio limited to 2.5× the natural scale_x.
    scale_y = min(scale_y, scale_x * 2.5)

    # World → SVG pixel coordinates.  X centred horizontally; Y baseline
    # at root line (= bottom of drawing area).
    cx = width_px / 2.0
    drawn_w = span_x_world * scale_x
    x_origin = cx - drawn_w / 2.0
    base_y = height_px - pad_bot - 8   # baseline = root line in image

    def W(x_world, y_world):
        return (x_origin + (x_world + n_teeth * P / 2.0) * scale_x,
                base_y - y_world * scale_y)
    # Keep `scale` (used in old code below for ticks/pitch_dim) = scale_x.
    scale = scale_x

    # Build SVG path tiling N teeth, with ARCS at root and (optional)
    # at crest when those are specified as radii rather than flats.
    # The root_radius field, when > 0, dips the path below the baseline
    # showing a rounded valley between teeth — clearly visible vs a
    # sharp-V root.  Same idea for crest if root-radius-style crest.
    path_cmds = []
    x_cursor = -n_teeth * P / 2.0
    sx0, sy0 = W(x_cursor, 0)
    path_cmds.append(f'M {sx0:.2f},{sy0:.2f}')

    # Helpers for arc commands.
    def line_to(x, y):
        sx, sy = W(x, y)
        path_cmds.append(f'L {sx:.2f},{sy:.2f}')

    def root_arc_to(x_end, y_end):
        # Draw a CONCAVE arc (rounded valley) from current point to
        # (x_end, y_end).  Arc radius scaled by Y axis (depth into
        # workpiece).  In SVG with Y-axis flipped, sweep-flag=1 makes
        # the arc bulge DOWN visually, which is the rounded root.
        sx, sy = W(x_end, y_end)
        # Use root_rad in WORLD units → screen pixels via scale_y.
        rs = max(2.0, root_rad * scale_y * 1.0)
        path_cmds.append(
            f'A {rs:.2f} {rs:.2f} 0 0 1 {sx:.2f},{sy:.2f}')

    def crest_arc_to(x_end, y_end):
        # Convex (rounded) crest — bulge UP.  sweep-flag=1 with arc
        # going right → upward.  Used when crest is rounded (Whitworth,
        # Round, etc.), but currently we keep crests as flats.
        sx, sy = W(x_end, y_end)
        rs = max(2.0, crest_flat * scale_y * 0.6)
        path_cmds.append(
            f'A {rs:.2f} {rs:.2f} 0 0 0 {sx:.2f},{sy:.2f}')

    # Determine if the family typically uses a rounded root.  Whitworth,
    # BSP, BSPT have radii at BOTH crest and root; UNJ/MJ/API_RSC have
    # rounded roots only; ISO M may have rounded roots in practice.
    family = (spec.family or '').lower()
    rounded_root_families = ('bsw', 'bsf', 'bsp', 'bspt', 'unj', 'mj',
                             'api_nc', 'api_reg', 'api_fh', 'api_h',
                             'mining_t', 'mining_r', 'mining_st',
                             'mining_gd', 'round')
    use_root_arc = (root_rad > 1e-6
                    and any(family.startswith(p) for p in rounded_root_families))

    for tooth_idx in range(n_teeth):
        center = x_cursor + P / 2.0
        x_root_l  = center + tooth_base_left
        x_crest_l = center - half_crest
        x_crest_r = center + half_crest
        x_root_r  = center + tooth_base_right

        # Approach this tooth's left base.
        # If a root flat exists (x_root_l > x_cursor) AND we're using
        # root arcs, draw a small arc at the root junction; otherwise
        # just draw a straight line along the root flat.
        if use_root_arc and tooth_idx > 0:
            # Replace the previous tooth's right base → this tooth's
            # left base with a concave arc (rounded valley).  Already
            # at (x_cursor + tooth_base_right_prev, 0) — that's where
            # the previous tooth's right flank ended.  The arc curves
            # down to a low point and back up to (x_root_l, 0).
            root_arc_to(x_root_l, 0)
        elif x_root_l > x_cursor:
            line_to(x_root_l, 0)

        # Up the left flank to crest-left
        line_to(x_crest_l, h)
        # Crest top — flat (or sharp peak if crest_flat=0)
        if x_crest_r > x_crest_l:
            line_to(x_crest_r, h)
        # Down the right flank to root-right
        line_to(x_root_r, 0)
        x_cursor += P

    # Tail: from last tooth's right base back to the canvas edge.
    line_to(x_cursor, 0)

    path_d = ' '.join(path_cmds)

    # Pitch line (horizontal dashed line at half height).
    pitch_y = base_y - (h * 0.5) * scale
    pitch_line = (f'<line x1="{pad_x}" y1="{pitch_y:.2f}" '
                  f'x2="{width_px - pad_x}" y2="{pitch_y:.2f}" '
                  f'stroke="#888" stroke-dasharray="6 4" stroke-width="1"/>')
    # Axis line (workpiece centreline) — at base_y (root level).
    axis_y = base_y
    axis_line = (f'<line x1="{pad_x}" y1="{axis_y}" '
                 f'x2="{width_px - pad_x}" y2="{axis_y}" '
                 f'stroke="#444" stroke-width="1.5"/>')

    # Pitch ruler: small vertical ticks at each tooth boundary.
    ticks = []
    for k in range(n_teeth + 1):
        wx = -n_teeth * P / 2.0 + k * P
        sx, sy = W(wx, 0)
        ticks.append(f'<line x1="{sx:.2f}" y1="{sy + 4}" '
                     f'x2="{sx:.2f}" y2="{sy + 12}" '
                     f'stroke="#888" stroke-width="1"/>')
    # Pitch span dimension between first two ticks.
    sx0, sy0 = W(-n_teeth * P / 2.0, 0)
    sx1, sy1 = W(-n_teeth * P / 2.0 + P, 0)
    p_dim_y = sy0 + 22
    pitch_dim = (f'<line x1="{sx0:.2f}" y1="{p_dim_y}" '
                 f'x2="{sx1:.2f}" y2="{p_dim_y}" '
                 f'stroke="#666" stroke-width="1" '
                 f'marker-start="url(#arrow)" marker-end="url(#arrow)"/>'
                 f'<text x="{(sx0+sx1)/2:.2f}" y="{p_dim_y + 14}" '
                 f'text-anchor="middle" font-family="Segoe UI, sans-serif" '
                 f'font-size="10" fill="#444">P = {P:g} mm</text>')

    # Header: family name + size + key dimensions.
    # U228g: side-aware dia labels for crest / pitch / root lines.
    # External: crest = Major Dia, root = Minor Dia (d1).
    # Internal: crest = Minor Dia (D1), root = Major Dia.
    side = (side or 'External')
    is_internal = side.lower().startswith('int')
    family = (spec.family or '').upper()
    is_metric = family.startswith('M') and not family.startswith('MIN')
    # Resolve nominal dia values per ISO 261 for Metric (basic D2/D1
    # are CONSTANTS — do not reuse spec.minor_internal which may have
    # been overridden by the operator's tap-drill size).
    if is_metric and P > 0 and spec.major:
        H_basic = (3 ** 0.5) / 2.0 * P
        d2_nom = round(spec.major - 0.75 * H_basic, 3)
        D1_nom = round(spec.major - 1.25 * H_basic, 3)
        d1_nom = D1_nom
        Major_nom = spec.major
    else:
        d2_nom = spec.pitch_dia
        D1_nom = spec.minor_internal
        d1_nom = spec.minor_external
        Major_nom = spec.major
    if is_internal:
        crest_label, crest_val = 'Minor Dia D1', D1_nom
        root_label,  root_val  = 'Major Dia D',  Major_nom
    else:
        crest_label, crest_val = 'Major Dia D',  Major_nom
        root_label,  root_val  = 'Minor Dia d1', d1_nom

    def _v(v, suffix=' mm'):
        return f'{v:g}{suffix}' if v is not None else '—'

    labels = []
    if show_dims:
        # Title.
        labels.append(
            f'<text x="{pad_x}" y="22" '
            f'font-family="Segoe UI, sans-serif" font-size="14" '
            f'font-weight="bold" fill="#222">'
            f'{spec.family}  {spec.size}'
            f'<tspan font-size="11" fill="#1F4E79"> &#160;'
            f'({"INTERNAL" if is_internal else "EXTERNAL"} thread)'
            f'</tspan></text>')
        labels.append(
            f'<text x="{pad_x}" y="40" '
            f'font-family="Segoe UI, sans-serif" font-size="11" fill="#555">'
            f'P={P:g} mm   D={spec.major:g} mm   '
            f'flanks (from radial) {fl:g}° / {ft:g}°   '
            f'incl={spec.included_angle:g}°   h={h:g} mm</text>')

        # Side-aware labels on crest line, pitch line, root line.
        # Place labels in the right margin so they sit next to the
        # relevant line without overlapping the tooth path.
        # Crest line label (at y = base_y - h*scale_y).
        crest_y = base_y - h * scale_y
        labels.append(
            f'<text x="{width_px - pad_x - 4}" y="{crest_y - 4:.2f}" '
            f'text-anchor="end" '
            f'font-family="Segoe UI, sans-serif" font-size="10" '
            f'fill="#1F4E79" font-weight="bold">'
            f'{crest_label} = {_v(crest_val)}</text>')
        # Pitch line label (already drawn dashed at h/2).
        labels.append(
            f'<text x="{width_px - pad_x - 4}" y="{pitch_y - 4:.2f}" '
            f'text-anchor="end" '
            f'font-family="Segoe UI, sans-serif" font-size="10" '
            f'fill="#1F4E79" font-weight="bold">'
            f'Pitch Dia D2 = {_v(d2_nom)}</text>')
        # Root line label (at base_y).
        labels.append(
            f'<text x="{width_px - pad_x - 4}" y="{base_y - 4:.2f}" '
            f'text-anchor="end" '
            f'font-family="Segoe UI, sans-serif" font-size="10" '
            f'fill="#1F4E79" font-weight="bold">'
            f'{root_label} = {_v(root_val)}</text>')

        # Vertical Height (h) dimension on the LEFT side.
        # Two short tick marks + a dimension line + text label.
        h_x = pad_x + 6
        labels.append(
            f'<line x1="{h_x}" y1="{crest_y:.2f}" '
            f'x2="{h_x + 6}" y2="{crest_y:.2f}" '
            f'stroke="#666" stroke-width="1"/>')
        labels.append(
            f'<line x1="{h_x}" y1="{base_y}" '
            f'x2="{h_x + 6}" y2="{base_y}" '
            f'stroke="#666" stroke-width="1"/>')
        labels.append(
            f'<line x1="{h_x + 3}" y1="{crest_y:.2f}" '
            f'x2="{h_x + 3}" y2="{base_y}" '
            f'stroke="#666" stroke-width="1" '
            f'marker-start="url(#arrow)" marker-end="url(#arrow)"/>')
        labels.append(
            f'<text x="{h_x + 10}" y="{(crest_y + base_y) / 2 + 4:.2f}" '
            f'font-family="Segoe UI, sans-serif" font-size="10" '
            f'fill="#444">h = {h:g} mm</text>')

        # Footer.
        labels.append(
            f'<text x="{pad_x}" y="{height_px - 12}" '
            f'font-family="Segoe UI, sans-serif" font-size="10" '
            f'fill="#888">{spec.standard}</text>')
        if spec.helix_angle is not None and spec.pitch_dia:
            labels.append(
                f'<text x="{width_px - pad_x}" y="{height_px - 12}" '
                f'text-anchor="end" '
                f'font-family="Segoe UI, sans-serif" font-size="10" '
                f'fill="#888">helix={spec.helix_angle:g}°  '
                f'pd={spec.pitch_dia:g} mm</text>')

    # Arrowhead marker for pitch dim line.
    arrow_def = ('<defs><marker id="arrow" markerWidth="6" markerHeight="6" '
                 'refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" '
                 'fill="#666"/></marker></defs>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}">
  {arrow_def}
  <rect width="{width_px}" height="{height_px}" fill="#fafafa"/>
  {axis_line}
  {pitch_line}
  <path d="{path_d}" stroke="#1976D2" stroke-width="2" fill="#90CAF9" fill-opacity="0.45"/>
  {''.join(ticks)}
  {pitch_dim}
  {''.join(labels)}
</svg>'''
    return svg


def save_profile_svg(spec: ThreadSpec, path: str,
                     width_px: int = 600, height_px: int = 360) -> str:
    """Save the 2D profile SVG to a file.  Returns the file path."""
    svg = profile_svg(spec, width_px, height_px)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(svg)
    return path


# =============================================================================
# Build the master library dict-of-lists keyed by family.
# =============================================================================

LIBRARY: dict = {}


def _build_library() -> None:
    LIBRARY.clear()
    LIBRARY['M_coarse'] = [make_iso_m(D, P, series='coarse') for (D, P) in _ISO_M_COARSE]
    LIBRARY['M_fine']   = [make_iso_m(D, P, label=lbl, series='fine')
                           for (D, P, lbl) in _ISO_M_FINE]
    LIBRARY['UNC']      = [make_un(lbl, tpi, D_in, series='UNC')
                           for (lbl, tpi, D_in) in _UNC]
    LIBRARY['UNF']      = [make_un(lbl, tpi, D_in, series='UNF')
                           for (lbl, tpi, D_in) in _UNF]
    LIBRARY['UNEF']     = [make_un(lbl, tpi, D_in, series='UNEF')
                           for (lbl, tpi, D_in) in _UNEF]
    LIBRARY['BSW']      = [make_whit(lbl, tpi, D_in, series='BSW')
                           for (lbl, tpi, D_in) in _BSW]
    LIBRARY['BSF']      = [make_whit(lbl, tpi, D_in, series='BSF')
                           for (lbl, tpi, D_in) in _BSF]
    LIBRARY['BSP']      = [make_bsp(lbl, tpi, D_in, tapered=False)
                           for (lbl, tpi, D_in) in _BSP]
    LIBRARY['BSPT']     = [make_bsp(lbl, tpi, D_in, tapered=True)
                           for (lbl, tpi, D_in) in _BSP]
    LIBRARY['NPT']      = [make_npt(lbl, tpi, D_in) for (lbl, tpi, D_in) in _NPT]
    LIBRARY['NPTF']     = [make_npt(lbl, tpi, D_in, dryseal=True)
                           for (lbl, tpi, D_in) in _NPT]
    # ANPT shares the same sizes as NPT.
    LIBRARY['ANPT']     = [make_anpt(lbl, tpi, D_in)
                           for (lbl, tpi, D_in) in _NPT]
    LIBRARY['NPSM']     = [make_npsm(lbl, tpi, D_in, variant='NPSM')
                           for (lbl, tpi, D_in) in _NPSM]
    LIBRARY['NPSL']     = [make_npsm(lbl, tpi, D_in, variant='NPSL')
                           for (lbl, tpi, D_in) in _NPSL]
    LIBRARY['NPSC']     = [make_npsm(lbl, tpi, D_in, variant='NPSC')
                           for (lbl, tpi, D_in) in _NPSC]
    LIBRARY['Acme']     = [make_acme(lbl, tpi, D_in) for (lbl, tpi, D_in) in _ACME]
    LIBRARY['Stub_Acme']= [make_stub_acme(lbl, tpi, D_in)
                           for (lbl, tpi, D_in) in _ACME]
    LIBRARY['TR']       = [make_tr(D, P) for (D, P) in _TR]
    LIBRARY['Buttress'] = [make_buttress(lbl, P, D) for (lbl, P, D) in _BUTTRESS]
    LIBRARY['Saw']      = [make_saw(lbl, P, D) for (lbl, P, D) in _SAW]
    LIBRARY['Round']    = [make_round(lbl, P, D) for (lbl, P, D) in _ROUND]
    LIBRARY['PG']       = [make_pg(lbl, P, D) for (lbl, P, D) in _PG]
    LIBRARY['Edison']   = [make_edison(lbl, D, P) for (lbl, D, P) in _EDISON]
    LIBRARY['UNJ']      = [make_unj(lbl, tpi, D_in) for (lbl, tpi, D_in) in _UNJ]
    LIBRARY['MJ']       = [make_mj(D, P) for (D, P) in _MJ]
    LIBRARY['API_Round_8']  = [make_api_round(lbl, tpi, D_in, 'API_Round_8')
                               for (lbl, tpi, D_in) in _API_ROUND_8]
    LIBRARY['API_Round_10'] = [make_api_round(lbl, tpi, D_in, 'API_Round_10')
                               for (lbl, tpi, D_in) in _API_ROUND_10]
    LIBRARY['API_Buttress'] = [make_api_buttress(lbl, D_in)
                               for (lbl, D_in) in _API_BUTTRESS]
    LIBRARY['DIN_477'] = [make_din477(lbl, D, P, profile, hand, gas)
                          for (lbl, D, P, profile, hand, gas) in _DIN_477]
    # API rotary shouldered drill-string connections.
    LIBRARY['API_RSC'] = [make_api_rsc(lbl, D_in, tpi, ipf, fc, form, rad)
                          for (lbl, D_in, tpi, ipf, fc, form, rad) in _API_RSC]
    LIBRARY['API_Macaroni'] = [make_api_rsc(lbl, D_in, tpi, ipf, fc, form, rad)
                               for (lbl, D_in, tpi, ipf, fc, form, rad)
                               in _API_MACARONI]
    # Mining percussion / rotary drill-rod threads.
    LIBRARY['Mining'] = [make_mining_drillrod(lbl, D, P, t)
                         for (lbl, D, P, t) in _MINING_RODS]


_build_library()


# =============================================================================
# Public API
# =============================================================================

def families() -> list:
    """Return the list of family codes available."""
    return list(LIBRARY.keys())


def list_sizes(family: str) -> list:
    """Return the size labels available for the given family."""
    return [t.size for t in LIBRARY.get(family, [])]


def lookup(family: str, size: str) -> Optional[ThreadSpec]:
    """Find a ThreadSpec by family + size label.  Returns None if not found."""
    for t in LIBRARY.get(family, []):
        if t.size == size:
            return t
    return None


def lookup_by_dia(family: str, target_major: float,
                  tolerance: float = 0.01) -> Optional[ThreadSpec]:
    """Find a ThreadSpec by family + major dia (within +/- tolerance mm)."""
    best = None
    best_diff = float('inf')
    for t in LIBRARY.get(family, []):
        diff = abs(t.major - target_major)
        if diff <= tolerance and diff < best_diff:
            best = t
            best_diff = diff
    return best


def stats() -> dict:
    """Return count of sizes per family."""
    return {f: len(threads) for f, threads in LIBRARY.items()}


if __name__ == '__main__':
    # Self-test: print stats, sample lookup, references, proprietary list.
    print("=" * 70)
    print("Thread library statistics")
    print("=" * 70)
    total = 0
    for f, n in stats().items():
        print(f"  {f:<16s}: {n:3d} sizes")
        total += n
    print(f"  {'TOTAL':<16s}: {total:3d} thread specs")
    print(f"  {'Proprietary':<16s}: {len(PROPRIETARY_THREADS):3d} listed (no dims)")
    print()
    print("=" * 70)
    print("Sample lookup — M_coarse / M10")
    print("=" * 70)
    t = lookup('M_coarse', 'M10')
    if t:
        for k, v in t.asdict().items():
            print(f"  {k:<22s}: {v}")
        print(f"  reference             : {reference_for('M_coarse')}")
    print()
    print("=" * 70)
    print("Sample 2D profile SVG generation")
    print("=" * 70)
    if t:
        svg = profile_svg(t, width_px=600, height_px=300)
        print(f"  SVG length: {len(svg)} bytes")
        # Save for visual inspection
        save_profile_svg(t, 'M10_profile.svg')
        print("  saved → M10_profile.svg (open in browser to view)")
    print()
    print("=" * 70)
    print("Proprietary threads (names listed, no dimensional data)")
    print("=" * 70)
    for entry in PROPRIETARY_THREADS[:5]:
        print(f"  {entry['name']:<22s} ({entry['manufacturer']})")
        print(f"    {entry['description'][:80]}...")
    print(f"  ... and {len(PROPRIETARY_THREADS) - 5} more.")
    print()
    print("All references:")
    for fam in sorted(REFERENCES.keys()):
        print(f"  {fam:<16s}: {REFERENCES[fam][:80]}")
