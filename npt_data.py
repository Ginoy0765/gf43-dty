"""
NPT (National Pipe Taper) thread data, cross-checked with Baker reference.

Table's M_L1 = Baker's MAJOR at E0 = major dia at SMALL END (external face)
Table's m_L1 = Baker's MINOR at E0 = minor dia at SMALL END

    External thread face D = M_L1                (directly from table)
    Internal thread face D = M_L1 + L1 * K       (widens toward opening)

    Sign of dia-diff at end of thread:
        Internal NPT: negative (dia decreases over thread length)
        External NPT: positive (dia increases over thread length)

Taper constant K (dia change per unit axial length) = 2 * tan(half-angle)
NPT standard is exactly 1:16 taper ratio, so K = 1/16 = 0.0625
(User's excel used tan(1.78°) giving 0.06215; Baker uses exact 0.0625.
We use the exact Baker value for best agreement with reference tables.)
"""

import math

K = 1.0 / 16.0           # 0.0625 - exact NPT 1:16 diametrical taper
HALF_ANGLE_DEG = math.degrees(math.atan(K / 2.0))   # 1.79°

# size_label, tpi, drill mm, L1 mm, M_L1 mm (= MAJOR at E0), m_L1 mm (= MINOR at E0)
# MAJOR/MINOR values verified against Baker American National Standard Taper Pipe Threads reference.
# (User's original NPT.xlsx had size-6 M_L1 = 163.73 which is the pitch dia, not major.
#  Corrected to Baker's 166.271 mm.)
NPT_SIZES = [
    ('1/16',  27,   6.14,   4.064,   7.641,   6.137),
    ('1/8',   27,   8.43,   4.102,   9.986,   8.481),
    ('1/4',   18,  11.12,   5.786,  13.254,  10.996),
    ('3/8',   18,  14.27,   6.096,  16.674,  14.417),
    ('1/2',   14,  17.85,   8.128,  20.715,  17.813),
    ('3/4',   14,  23.01,   8.611,  26.030,  23.127),
    ('1',    11.5, 28.98,  10.160,  32.593,  29.060),
    ('1-1/4',11.5, 37.69,  10.668,  41.318,  37.785),
    ('1-1/2',11.5, 43.66,  10.668,  47.388,  43.853),
    ('2',    11.5, 55.57,  11.074,  59.400,  55.867),
    ('2-1/2',  8,  66.26,  17.323,  71.616,  66.535),
    ('3',      8,  82.14,  19.456,  87.392,  82.311),
    ('3-1/2',  8,  None,   20.853, 100.013,  94.933),
    ('4',      8,  None,   21.438, 112.633, 107.554),
    ('5',      8,  None,   23.800, 139.465, 134.384),
    ('6',      8,  None,   24.333, 166.271, 161.191),   # fixed: was 163.73 (pitch)
]


def internal_face_D(M_L1, L1):
    """Internal NPT major dia at the face (pipe opening) = widest.
    Formula: at the gauging plane (L1 from face) dia = M_L1; face is L1 closer
    to the opening, so face dia = M_L1 + L1*K."""
    return M_L1 + L1 * K


def external_face_D(M_L1, L1=None):
    """External NPT major dia at the pipe face (small end).
    Equals M_L1 directly - this is Baker's MAJOR at E0 value.
    L1 arg kept for API symmetry but unused."""
    return M_L1


def internal_face_minor(m_L1, L1):
    return m_L1 + L1 * K


def external_face_minor(m_L1, L1=None):
    """Equals m_L1 directly (Baker MINOR at E0)."""
    return m_L1


def size_labels():
    return [row[0] for row in NPT_SIZES]


def lookup(size_label):
    """Return dict of computed values for the given size, or None."""
    for label, tpi, drill, L1, M_L1, m_L1 in NPT_SIZES:
        if label == size_label:
            return {
                'size':     label,
                'tpi':      tpi,
                'pitch':    25.4 / tpi,
                'drill':    drill,
                'L1':       L1,
                'M_L1':     M_L1,
                'm_L1':     m_L1,
                'int_face_D':     round(internal_face_D(M_L1, L1), 3),
                'ext_face_D':     round(external_face_D(M_L1, L1), 3),
                'int_face_minor': round(internal_face_minor(m_L1, L1), 3),
                'ext_face_minor': round(external_face_minor(m_L1, L1), 3),
            }
    return None


# --- L2: length of effective thread (ASME B1.20.1) -----------------------
# Nominal basic pipe OD (inches) per size, for the L2 formula.
_BASIC_OD_IN = {
    '1/16': 0.3125, '1/8': 0.405, '1/4': 0.540, '3/8': 0.675,
    '1/2': 0.840, '3/4': 1.050, '1': 1.315, '1-1/4': 1.660,
    '1-1/2': 1.900, '2': 2.375, '2-1/2': 2.875, '3': 3.500,
    '3-1/2': 4.000, '4': 4.500, '5': 5.563, '6': 6.625,
}


def effective_thread_L2(size_label):
    """Length of effective thread L2 in mm (ASME B1.20.1).
    L2 = (0.80*D + 6.8) / n  inches, D = basic OD (in), n = TPI."""
    od = _BASIC_OD_IN.get(size_label)
    tpi = next((row[1] for row in NPT_SIZES if row[0] == size_label), None)
    if od is None or not tpi:
        return None
    return (0.80 * od + 6.8) / float(tpi) * 25.4
