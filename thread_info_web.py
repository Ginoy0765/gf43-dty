"""Web thread-info shim — all families.
Ported from desktop main.py populate_thread_info. Uses the real
tolerance_data.py for exact bands and thread_library.py for the
spec-based families' basic dimensions.
family = thread_library family code (M_coarse / UNC / Acme / TR / BSP / BSW /
NPT / BSPT / Buttress US / ...). Metric/UN/Acme/Stub Acme/TR get inline
formulas (to match the desktop's display); everything else uses the library
spec.  Bands from tolerance_data (None -> nominal/—/— )."""
import math
import tolerance_data as td
try:
    import thread_library as tl
except Exception:
    tl = None


def _mmm(nominal, band, key):
    return td.format_minmeanmax(nominal, band.get(key) if band else None)


def _fam_group(fam):
    G = {
        'M_coarse': 'Metric', 'M_fine': 'Metric', 'M': 'Metric', 'MJ': 'Metric',
        'UNC': 'UN', 'UNF': 'UN', 'UNEF': 'UN', 'UNJ': 'UN', 'UN': 'UN',
        'BSW': 'Whitworth', 'BSF': 'Whitworth',
        'BSP': 'BSP', 'BSPT': 'BSPT', 'NPT': 'NPT', 'NPS': 'NPT',
        'Acme': 'Acme', 'Stub Acme': 'Stub Acme', 'Stub_Acme': 'Stub Acme',
        'TR': 'TR (Trapezoidal)', 'Buttress US': 'American Buttress (B1.9)',
        'Buttress BR': 'British Buttress (BS 1657)', 'Saw': 'Saw',
        'Rd': 'Round', 'Square': 'Square', 'Worm 14.5': 'Worm',
        'Worm 20': 'Worm', 'Worm 25': 'Worm',
    }
    return G.get(fam, fam)


def _std(fam):
    if fam.startswith('M') and not fam.startswith('MJ') and not fam.startswith('MIN'):
        return 'Metric, ISO 261 / ISO 965'
    if fam.startswith('UN') or fam == 'MJ':
        return 'UN, ANSI/ASME B1.1'
    if fam.startswith('Acme') or fam.startswith('Stub'):
        return 'Acme, ASME B1.5 / B1.8'
    if fam == 'TR':
        return 'Trapezoidal, ISO 2901/2903'
    if fam.startswith('BSPT') or fam.startswith('NPT'):
        return 'Taper pipe, ASME B1.20.1 / ISO 7'
    if fam.startswith('BSP') or fam.startswith('BSW') or fam.startswith('BSF'):
        return 'Whitworth / BSP, BS 84 / BS 2779'
    if fam.startswith('Buttress'):
        return 'Buttress, ANSI B1.9 / BS 1657'
    if fam.startswith('Square'):
        return 'Square, DIN 79 (parallel flank)'
    if fam.startswith('Worm'):
        return 'Worm, AGMA / DIN 3975'
    if fam.startswith('Round') or fam == 'Rd':
        return 'Round / Knuckle, DIN 405'
    if fam.startswith('Saw'):
        return 'Sawtooth, DIN 513'
    if fam.startswith('NPS'):
        return 'Straight pipe, ASME B1.20.1'
    return _fam_group(fam)


def _basic(fam, P, D, spec):
    """Return dict of basic dims: d2, D1(int minor), d1(ext minor),
    h_int, h_ext, major_ext, major_int, inc_ang."""
    H = math.sqrt(3) / 2.0 * P
    fu = fam.upper().replace(' ', '_')
    is_metric = fu.startswith('M') and not fu.startswith('MJ') and not fu.startswith('MIN')
    is_un = fu.startswith('UN') or fu == 'MJ'
    is_acme = fu.startswith('ACME')
    is_stub = fu.startswith('STUB')
    is_tr = fu == 'TR' or fu.startswith('TR_')
    is_square = fu.startswith('SQUARE')
    if is_square:
        # Parallel-flank square thread: depth 0.5P, flanks 0deg.
        d2 = round(D - 0.5 * P, 3); D1 = round(D - P, 3)
        return dict(d2=d2, D1=D1, d1=D1, major_ext=D, major_int=D,
                    h_ext=round(0.5 * P, 3), h_int=round(0.5 * P, 3), inc=0.0)
    if is_metric:
        d2 = round(D - 0.6495 * P, 3); D1 = round(D - 1.0825 * P, 3)
        return dict(d2=d2, D1=D1, d1=D1, major_ext=D, major_int=D,
                    h_ext=round(17.0 * H / 24.0, 3), h_int=round(0.5 * (D - D1), 3),
                    inc=60.0)
    if is_un:
        d2 = round(D - 0.6495 * P, 3); D1 = round(D - 1.0825 * P, 3)
        d1 = round(D - 17.0 * H / 12.0, 3)
        return dict(d2=d2, D1=D1, d1=d1, major_ext=D, major_int=D,
                    h_ext=round(17.0 * H / 24.0, 3), h_int=round(0.5 * (D - D1), 3),
                    inc=60.0)
    if is_acme:
        ac = 0.508 if P >= 2.540 else 0.254
        major_ext = D; major_int = round(D + ac, 3)
        d1 = round(D - P - ac, 3); D1 = round(D - P, 3); d2 = round(D - 0.5 * P, 3)
        return dict(d2=d2, D1=D1, d1=d1, major_ext=major_ext, major_int=major_int,
                    h_ext=round((major_ext - d1) / 2.0, 3),
                    h_int=round((major_int - D1) / 2.0, 3), inc=29.0)
    if is_stub:
        ac = 0.508 if P >= 2.540 else 0.254
        major_ext = D; major_int = round(D + ac, 3)
        d1 = round(D - 0.6 * P - ac, 3); D1 = round(D - 0.6 * P, 3); d2 = round(D - 0.3 * P, 3)
        return dict(d2=d2, D1=D1, d1=d1, major_ext=major_ext, major_int=major_int,
                    h_ext=round((major_ext - d1) / 2.0, 3),
                    h_int=round((major_int - D1) / 2.0, 3), inc=29.0)
    if is_tr:
        ac = 0.5
        major_ext = D; major_int = round(D + ac, 3)
        d1 = round(D - P - ac, 3); D1 = round(D - P, 3); d2 = round(D - 0.5 * P, 3)
        return dict(d2=d2, D1=D1, d1=d1, major_ext=major_ext, major_int=major_int,
                    h_ext=round((major_ext - d1) / 2.0, 3),
                    h_int=round((major_int - D1) / 2.0, 3), inc=30.0)
    # else — use the library spec
    if spec is not None:
        d = spec.asdict()
        try:
            inc = float(d.get('included_angle') or 0.0)
        except (TypeError, ValueError):
            inc = 0.0
        return dict(
            d2=d.get('pitch_dia'), D1=d.get('minor_internal'),
            d1=d.get('minor_external'),
            major_ext=d.get('major'), major_int=d.get('major'),
            h_ext=d.get('height_external'), h_int=d.get('height_internal'),
            inc=inc)
    # last-ditch fallback (unknown family, no spec)
    d2 = round(D - 0.6495 * P, 3); D1 = round(D - 1.0825 * P, 3)
    return dict(d2=d2, D1=D1, d1=D1, major_ext=D, major_int=D,
                h_ext=round(0.6134 * P, 3), h_int=round(0.5413 * P, 3), inc=60.0)


def _profile(inc, P, spec, is_flat):
    """Return (ext_prof, int_prof) rows [label,a_lo,a_hi,r_lo,r_hi,mean,status]."""
    H = math.sqrt(3) / 2.0 * P
    if abs(inc - 60.0) < 0.5:
        r_e_max = round(P * math.sqrt(3) / 12.0, 4); r_e_min = round(P * math.sqrt(3) / 16.0, 4)
        r_e_mean = round((r_e_min + r_e_max) / 2.0, 4)
        r_i_max = round(P * math.sqrt(3) / 24.0, 4); r_i_min = round(P * math.sqrt(3) / 32.0, 4)
        r_i_mean = round((r_i_min + r_i_max) / 2.0, 4)
        ext = [['Crest flat', round(P / 8.0, 4), round(P / 8.0, 4), None, None, None,
                'Mandatory (basic profile, ISO 68-1)'],
               ['Root flat', round(P / 4.0, 4), round(P / 4.0, 4), None, None, None,
                'Mandatory basic; may be radiused at root'],
               ['Root radius', 0.0, r_e_max, r_e_min, r_e_max, r_e_mean,
                'Allowed 0-0.144P; recommended 0.108-0.144P; mean 0.126P'],
               ['Crest radius', None, None, None, None, None, 'Not specified by ISO 68-1']]
        intr = [['Crest flat', round(P / 4.0, 4), round(P / 4.0, 4), None, None, None,
                 'Mandatory (basic profile, ISO 68-1)'],
                ['Root flat', round(P / 8.0, 4), None, None, None, None,
                 'Min mandatory; ES open per ISO 965-1'],
                ['Root radius', 0.0, r_i_max, r_i_min, r_i_max, r_i_mean,
                 'Allowed 0-0.072P; recommended 0.054-0.072P; mean 0.063P'],
                ['Crest radius', None, None, None, None, None, 'Not specified by ISO 68-1']]
        return ext, intr
    if abs(inc - 55.0) < 0.5:
        r_w = round(0.13733 * P, 4)
        row = ['', r_w, r_w, r_w, r_w, r_w, 'Mandatory (Whitworth profile, BS 84)']
        def mk(lbl):
            return [lbl] + row[1:]
        both = [mk('Crest radius'), mk('Root radius')]
        return both, [r[:] for r in both]
    # flat-root / other (Acme, TR, Buttress, Square, ...) — from spec if any
    ct = rr = None
    if spec is not None:
        d = spec.asdict()
        ct = d.get('crest_truncation'); rr = d.get('root_radius')
    ext = [['Crest flat', ct, ct, None, None, None, 'From standard'],
           ['Root flat', ct, ct, None, None, None, 'From standard'],
           ['Root radius', rr, None, None, None, None, 'From standard']]
    return ext, [r[:] for r in ext]


try:
    import npt_data as _npt
except Exception:
    _npt = None


def _compute_taper_pipe(fam, P, D, size, side):
    """NPT/BSPT taper pipe — dims at the gauge plane (L1) AND at the face
    (L0), from the Baker-verified npt_data table.  No tolerance bands."""
    K = 1.0 / 16.0
    internal = str(side).lower().startswith('int')
    row = _npt.lookup(str(size)) if (_npt and size) else None
    if row:
        M = row['M_L1']; m = row['m_L1']; L1 = row['L1']
        tpi = row['tpi']; Pn = row['pitch']
    else:
        # fallback for a custom size: D is the external face major
        M = D; m = round(D - 1.6 * P, 3); L1 = None
        tpi = round(25.4 / P, 3) if P else None; Pn = P
    pf = (M + m) / 2.0                 # pitch dia at E0 (external face)
    shift = (L1 * K) if L1 else 0.0
    if internal:                       # face=opening (large); gauge=L1 deeper (smaller)
        maj_f, pit_f, min_f = M + shift, pf + shift, m + shift
        maj_g, pit_g, min_g = M, pf, m
    else:                              # face=pipe end (small); gauge=L1 deeper (larger)
        maj_f, pit_f, min_f = M, pf, m
        maj_g, pit_g, min_g = M + shift, pf + shift, m + shift

    def r3(v):
        return None if v is None else round(v, 3)
    rows = [
        ['Major Dia', r3(maj_g), r3(maj_f)],
        ['Pitch Dia', r3(pit_g), r3(pit_f)],
        ['Minor Dia', r3(min_g), r3(min_f)],
    ]
    return {
        'taper_pipe': True,
        'standard': _std(fam),
        'group': _fam_group(fam),
        'tpi': tpi,
        'L1': r3(L1),
        'side': 'Internal' if internal else 'External',
        'rows': rows,
    }


def compute(family, ext_class, int_class, P, D, size=None, side='External'):
    P = float(P); D = float(D)
    fam = family or 'M_coarse'
    fu = fam.upper()
    if fu.startswith('NPT'):        # NPT / NPTF taper pipe (npt_data table)
        return _compute_taper_pipe(fam, P, D, size, side)
    spec = None
    if tl is not None and not (fam.upper().startswith('M') and not fam.upper().startswith('MJ')) \
            and not fam.upper().startswith('UN') and fam != 'MJ' \
            and not fam.upper().startswith(('ACME', 'STUB', 'TR', 'SQUARE')):
        try:
            spec = tl.lookup_by_dia(fam, D, tolerance=0.8)
        except Exception:
            spec = None
    b = _basic(fam, P, D, spec)
    ext_band = td.lookup(fam, ext_class, P, D, 'External') if ext_class else None
    int_band = td.lookup(fam, int_class, P, D, 'Internal') if int_class else None

    def side(band, major, minor, hval):
        return {'major': {'nom': major, 'mmm': _mmm(major, band, 'major')},
                'pitch': {'nom': b['d2'], 'mmm': _mmm(b['d2'], band, 'pitch')},
                'minor': {'nom': minor, 'mmm': _mmm(minor, band, 'minor')},
                'height': hval}

    is_flat = abs(b['inc'] - 60.0) >= 0.5 and abs(b['inc'] - 55.0) >= 0.5
    ext_prof, int_prof = _profile(b['inc'], P, spec, is_flat)
    return {
        'standard': _std(fam),
        'group': _fam_group(fam),
        'inc': b['inc'],
        'ext_class': ext_class, 'int_class': int_class,
        'ext': side(ext_band, b['major_ext'], b['d1'], b['h_ext']),
        'int': side(int_band, b['major_int'], b['D1'], b['h_int']),
        'ext_prof': ext_prof, 'int_prof': int_prof,
    }
