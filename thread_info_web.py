"""Web thread-info shim — ISO Metric (60 deg V) full panel.
Ported from desktop main.py populate_thread_info metric path.
Uses the real tolerance_data.py for exact ISO 965 bands."""
import tolerance_data as td


def compute(family, ext_class, int_class, P, D):
    P = float(P); D = float(D)
    H = (3 ** 0.5) / 2.0 * P                       # 0.866*P
    d2 = round(D - 0.6495 * P, 3)                  # pitch dia basic
    D1 = round(D - 1.0825 * P, 3)                  # minor basic (int) = ext d1
    d1 = D1
    h_int = round(0.5 * (D - D1), 3)               # 0.5413*P
    h_ext = round(17.0 * H / 24.0, 3)              # 0.6134*P

    ext_band = td.lookup(family, ext_class, P, D, 'External') if ext_class else None
    int_band = td.lookup(family, int_class, P, D, 'Internal') if int_class else None

    def mmm(nominal, band, key):
        return td.format_minmeanmax(nominal, band.get(key) if band else None)

    def side_dims(band, major, minor, hval):
        return {
            'major': {'nom': major, 'mmm': mmm(major, band, 'major')},
            'pitch': {'nom': d2,    'mmm': mmm(d2,    band, 'pitch')},
            'minor': {'nom': minor, 'mmm': mmm(minor, band, 'minor')},
            'height': hval,
        }

    ext = side_dims(ext_band, D, d1, h_ext)
    intr = side_dims(int_band, D, D1, h_int)

    r_ext_max  = round(P * (3 ** 0.5) / 12.0, 4)   # H/6  0.144P
    r_ext_rmin = round(P * (3 ** 0.5) / 16.0, 4)   # H/8  0.108P
    r_ext_mean = round((r_ext_rmin + r_ext_max) / 2.0, 4)
    r_int_max  = round(P * (3 ** 0.5) / 24.0, 4)   # H/12 0.072P
    r_int_rmin = round(P * (3 ** 0.5) / 32.0, 4)   # H/16 0.054P
    r_int_mean = round((r_int_rmin + r_int_max) / 2.0, 4)

    ext_prof = [
        ['Crest flat', round(P/8.0,4), round(P/8.0,4), None, None, None,
         'Mandatory (basic profile, ISO 68-1)'],
        ['Root flat',  round(P/4.0,4), round(P/4.0,4), None, None, None,
         'Mandatory basic; may be radiused at root'],
        ['Root radius', 0.0, r_ext_max, r_ext_rmin, r_ext_max, r_ext_mean,
         'Allowed 0-0.144P (flat permitted); recommended 0.108-0.144P for fatigue; mean 0.126P'],
        ['Crest radius', None, None, None, None, None,
         'Not specified by ISO 68-1'],
    ]
    int_prof = [
        ['Crest flat', round(P/4.0,4), round(P/4.0,4), None, None, None,
         'Mandatory (basic profile, ISO 68-1)'],
        ['Root flat',  round(P/8.0,4), None, None, None, None,
         'Min mandatory; ES open per ISO 965-1'],
        ['Root radius', 0.0, r_int_max, r_int_rmin, r_int_max, r_int_mean,
         'Allowed 0-0.072P (flat permitted); recommended 0.054-0.072P for fatigue; mean 0.063P'],
        ['Crest radius', None, None, None, None, None,
         'Not specified by ISO 68-1'],
    ]
    return {
        'standard': 'Metric, ISO 261 / ISO 965',
        'H': round(H, 4),
        'ext_class': ext_class, 'int_class': int_class,
        'ext': ext, 'int': intr,
        'ext_prof': ext_prof, 'int_prof': int_prof,
    }
