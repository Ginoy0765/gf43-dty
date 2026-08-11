"""face_mill.py — YANTRA face-milling cut generator.

Produces a Fanuc I&J base program (tool-centre coords, G94 mm/min, G40 —
computer compensation) that is then re-dialected by mill_post and offset by
webpost, exactly like thread_mill.  Mirrors the thread_mill API:

    generate(**params) -> str          # Fanuc-base program text
    cycle_time(**params) -> float      # seconds
    SAFE_Z                             # module global (set by webpost)
    fmt(v)                             # coord formatter

v1 scope: RASTER pattern (Both-ways / Climb / Conventional) over a rectangular
or circular machining area, with avoid zones (circle/rect) and do-not-cross
barriers respected by per-scanline interval clipping (tool centre kept a full
radius + clearance clear — never gouges).  CONTOUR pattern falls back to raster
in v1 (flagged).  Off-edge air plunge; straight or arc lead-in; even stepover;
multi Z-level roughing; optional one-way-climb finish skim.
"""
import math

SAFE_Z = 20.0
_EPS = 1e-6


def fmt(v):
    v = round(float(v), 4)
    if abs(v) < 5e-5:
        return "0.0"
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    if "." not in s:
        s += ".0"
    return s


def _ff(v):
    v = float(v)
    if abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
    return ("%.3f" % v).rstrip("0").rstrip(".")


# --------------------------------------------------------------------------- #
# geometry helpers
# --------------------------------------------------------------------------- #
def _rot(x, y, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c)


def _rect_corners(area):
    """World corners of a rectangle area, honouring ref (corner|center) + rot."""
    x, y = area["x"], area["y"]
    w, l = area["w"], area["l"]
    rot = area.get("rot", 0)
    if area.get("ref", "corner") == "center":
        x0, y0 = x - w / 2.0, y - l / 2.0
    else:
        x0, y0 = x, y
    pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + l), (x0, y0 + l)]
    out = []
    for px, py in pts:
        rx, ry = _rot(px - x, py - y, rot)
        out.append((x + rx, y + ry))
    return out


def _to_sf(x, y, th):
    """world -> sweep frame (rotate by -th so sweep runs along +x)."""
    a = math.radians(-th)
    c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c)


def _to_world(x, y, th):
    a = math.radians(th)
    c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c)


def _merge(iv):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + _EPS:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


# --------------------------------------------------------------------------- #
# main entry
# --------------------------------------------------------------------------- #
def _build(P):
    area = P["area"]
    avoids = P.get("avoid", []) or []
    barriers = P.get("noCross", []) or []
    D = float(P.get("D", 50.0))
    r = D / 2.0

    tS = P.get("toolSide", {}) or {}
    a_over = float((tS.get("area", {}) or {}).get("overhang", 0.0))
    av_clr = float((tS.get("avoid", {}) or {}).get("clearance", 0.0))

    pat = P.get("pattern", {}) or {}
    kind = pat.get("kind", "raster")
    direction = pat.get("direction", "bothWays")
    sweep = pat.get("sweepAngle", "auto")
    ext = float(pat.get("passExtension", 0.0))

    stp = P.get("stepover", {}) or {}
    if stp.get("mode", "pctDia") == "mm" and stp.get("mm"):
        step = float(stp["mm"])
    else:
        step = D * float(stp.get("pctDia", 70)) / 100.0
    step = max(0.1, step)
    even = stp.get("even", True)

    # ----- sweep angle -----
    if area["shape"] == "rect":
        base_rot = area.get("rot", 0)
        if sweep == "auto":
            th = base_rot + (0 if area["w"] >= area["l"] else 90)
        else:
            th = float(sweep)
        corners_sf = [_to_sf(px, py, th) for px, py in _rect_corners(area)]
        xs = [p[0] for p in corners_sf]
        ys = [p[1] for p in corners_sf]
        amin_x, amax_x = min(xs), max(xs)
        amin_y, amax_y = min(ys), max(ys)

        def rowspan(yy):
            if amin_y - _EPS <= yy <= amax_y + _EPS:
                return (amin_x, amax_x)
            return None
        y_lo, y_hi = amin_y, amax_y
    else:  # circle
        th = 0.0 if sweep == "auto" else float(sweep)
        cx, cy = _to_sf(area["x"], area["y"], th)
        cr = area["dia"] / 2.0
        amin_x, amax_x = cx - cr, cx + cr
        amin_y, amax_y = cy - cr, cy + cr

        def rowspan(yy):
            d = cr * cr - (yy - cy) ** 2
            if d < 0:
                return None
            hw = math.sqrt(d)
            return (cx - hw, cx + hw)
        y_lo, y_hi = amin_y, amax_y

    # ----- avoids / barriers into sweep frame -----
    av_sf = []
    for a in avoids:
        if a["shape"] == "circle":
            c = _to_sf(a["x"], a["y"], th)
            av_sf.append(("circle", c[0], c[1], a["dia"] / 2.0))
        else:
            cs = [_to_sf(px, py, th) for px, py in _rect_corners(a)]
            axs = [p[0] for p in cs]; ays = [p[1] for p in cs]
            av_sf.append(("rect", min(axs), min(ays), max(axs), max(ays)))
    bar_sf = []
    for b in barriers:
        pts = [_to_sf(px, py, th) for px, py in b["pts"]]
        segs = [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
                for i in range(len(pts) - 1)]
        bar_sf.append(segs)

    def blocked(yy):
        iv = []
        for a in av_sf:
            if a[0] == "circle":
                keep = a[3] + r + av_clr
                dy = abs(yy - a[2])
                if dy < keep:
                    dx = math.sqrt(keep * keep - dy * dy)
                    iv.append((a[1] - dx, a[1] + dx))
            else:  # rect (over-approx safe)
                keep = r + av_clr
                if a[2] - keep <= yy <= a[4] + keep:
                    iv.append((a[1] - keep, a[3] + keep))
        keepb = r + av_clr
        for segs in bar_sf:
            for (x1, y1, x2, y2) in segs:
                lo, hi = min(y1, y2) - keepb, max(y1, y2) + keepb
                if not (lo <= yy <= hi):
                    continue
                if abs(y2 - y1) < _EPS:
                    iv.append((min(x1, x2) - keepb, max(x1, x2) + keepb))
                else:
                    t = (yy - y1) / (y2 - y1)
                    if -_EPS <= t <= 1 + _EPS:
                        xc = x1 + t * (x2 - x1)
                        iv.append((xc - keepb, xc + keepb))
        return _merge(iv)

    # ----- rows (even stepover across the perpendicular extent) -----
    covW = y_hi - y_lo
    if covW <= _EPS:
        rows = [y_lo]
    else:
        n = max(1, int(math.ceil(covW / step - _EPS)))
        astep = covW / n
        if not even:
            n = max(1, int(math.floor(covW / step + _EPS)))
            astep = step
        rows = [y_lo + i * astep for i in range(n + 1)]

    result = {
        "th": th, "r": r, "step": step, "rows": rows, "rowspan": rowspan,
        "blocked": blocked, "ext": ext + r + a_over, "direction": direction,
        "bbox_sf": (amin_x, amax_x, amin_y, amax_y), "kind": kind,
    }
    return result


def _level_segments(G, direction=None):
    """List of ('cut'|'rapid', x1,y1,x2,y2) in sweep frame for one Z pass-set."""
    r, rows, rowspan, blocked = G["r"], G["rows"], G["rowspan"], G["blocked"]
    ext = G["ext"]
    direction = direction or G["direction"]
    segs = []
    prev = None
    for i, yy in enumerate(rows):
        span = rowspan(yy)
        if span is None:
            continue
        xs, xe = span[0] - ext, span[1] + ext
        if direction == "bothWays":
            ltr = (i % 2 == 0)
        else:
            ltr = (direction != "conventional")
        # blocked intervals clipped to [xs,xe]
        iv = []
        for a, b in blocked(yy):
            a, b = max(a, xs), min(b, xe)
            if b > a + _EPS:
                iv.append((a, b))
        iv = _merge(iv)
        # build L->R spans (cut) / gaps (rapid over island)
        pts = []
        pos = xs
        for a, b in iv:
            if a > pos + _EPS:
                pts.append((pos, a, "cut"))
            pts.append((max(a, pos), b, "rapid"))
            pos = max(pos, b)
        if pos < xe - _EPS:
            pts.append((pos, xe, "cut"))
        if not pts:
            continue
        if not ltr:
            pts = [(b, a, k) for (a, b, k) in reversed(pts)]
        start_x = pts[0][0]
        # inter-row link from previous end to this start
        if prev is not None:
            segs.append(("rapid", prev[0], prev[1], start_x, yy))
        for (a, b, k) in pts:
            segs.append((k, a, yy, b, yy))
        prev = (pts[-1][1], yy)
    return segs


def _emit_level(lines, G, segs, z, feed, plunge_feed, feed_plane):
    """Convert sweep-frame segments to G-code (world), with air-plunge + lifts."""
    th = G["th"]
    bx0, bx1, by0, by1 = G["bbox_sf"]

    def over_mat(x1, y1, x2, y2):
        # true if the straight link enters the area bbox (would ride material)
        for (px, py) in ((x1, y1), (x2, y2), ((x1 + x2) / 2, (y1 + y2) / 2)):
            if bx0 - _EPS <= px <= bx1 + _EPS and by0 - _EPS <= py <= by1 + _EPS:
                return True
        return False

    def W(x, y):
        wx, wy = _to_world(x, y, th)
        return "X" + fmt(wx) + " Y" + fmt(wy)

    if not segs:
        return
    # start of level: rapid above first point, drop in air to z
    fx, fy = segs[0][1], segs[0][2]
    lines.append("G00 " + W(fx, fy))
    lines.append("G00 Z" + fmt(feed_plane))
    lines.append("G01 Z" + fmt(z) + " F" + _ff(plunge_feed))
    for (k, x1, y1, x2, y2) in segs:
        if k == "cut":
            lines.append("G01 " + W(x2, y2) + " F" + _ff(feed))
        else:  # rapid link
            if over_mat(x1, y1, x2, y2):
                lines.append("G00 Z" + fmt(feed_plane))
                lines.append("G00 " + W(x2, y2))
                lines.append("G01 Z" + fmt(z) + " F" + _ff(plunge_feed))
            else:
                lines.append("G00 " + W(x2, y2))
    lines.append("G00 Z" + fmt(SAFE_Z))


def generate(**P):
    area = P["area"]
    D = float(P.get("D", 50.0))
    rpm = int(round(float(P.get("rpm", 1200))))
    feed = float(P.get("feed", 400))
    spindle = P.get("spindle", "M03")
    cool = P.get("coolant", "M08")

    entry = P.get("entry", {}) or {}
    heights = entry.get("heights", {}) or {}
    safez = float(heights.get("safeZ", P.get("safez", SAFE_Z)))
    globals()  # noqa
    feed_plane = float(heights.get("feedPlane", 2.0))
    plunge_feed = float(entry.get("plungeFeed", feed * 0.5))

    depth = P.get("depth", {}) or {}
    topZ = float(depth.get("topZ", 0.0))
    faceZ = float(depth.get("faceZ", -1.0))
    finishFloor = float(depth.get("finishFloorStock", 0.0))
    fin = P.get("finish", {}) or {}
    fin_on = bool(fin.get("enabled", False))
    if not fin_on:
        finishFloor = 0.0
    rough_depth = (topZ - faceZ) - finishFloor
    if rough_depth < 0:
        rough_depth = 0.0
    maxAp = float(depth.get("maxAp", max(0.5, rough_depth)))
    if depth.get("mode") == "nLevels":
        nlev = max(1, int(depth.get("nLevels", 1)))
    else:
        nlev = max(1, int(math.ceil(rough_depth / max(0.01, maxAp) - _EPS))) if rough_depth > _EPS else 1
    ap = rough_depth / nlev if nlev else rough_depth
    z_levels = [topZ - ap * (i + 1) for i in range(nlev)]
    if z_levels:
        z_levels[-1] = faceZ + finishFloor  # exact floor before finish

    G = _build(P)

    L = []
    L.append("%")
    shp = area["shape"]
    dims = ("%gx%g" % (area["w"], area["l"])) if shp == "rect" else ("DIA %g" % area["dia"])
    L.append("O0001 (FACE MILL %s D%g %s PASS)" % (dims, D, G["kind"].upper()))
    L.append("(--- SUMMARY ---)")
    L.append("(TOOL      = FACE MILL D%g)" % D)
    L.append("(PATTERN   = %s / %s)" % (G["kind"], G["direction"]))
    L.append("(STEPOVER  = %.3f MM   DOC = %.3f MM x %d LVL)" % (G["step"], ap, nlev))
    L.append("(TOP Z %s -> FACE Z %s)" % (fmt(topZ), fmt(faceZ)))
    L.append("G90 G40 G17 G94")
    L.append("G54")
    L.append("M06 T1")
    L.append("G43 H1 Z" + fmt(safez))
    L.append("S%d %s" % (rpm, spindle))
    if cool and cool != "None":
        L.append(cool)

    if G["kind"] == "contour":
        L.append("(NOTE: contour pattern not in v1 - raster used)")

    segs = _level_segments(G)
    for z in z_levels:
        L.append("(ROUGH LEVEL Z" + fmt(z) + ")")
        _emit_level(L, G, segs, z, feed, plunge_feed, feed_plane)

    # ----- finish skim -----
    if fin_on and finishFloor > _EPS:
        fstp = fin.get("stepover", {}) or {}
        Pf = dict(P)
        Pf = dict(P)
        pat2 = dict(P.get("pattern", {}) or {})
        pat2["direction"] = "climb"
        Pf["pattern"] = pat2
        Pf["stepover"] = {"mode": fstp.get("mode", "pctDia"),
                          "pctDia": fstp.get("pctDia", 50),
                          "mm": fstp.get("mm"), "even": True}
        Gf = _build(Pf)
        fsegs = _level_segments(Gf, direction="climb")
        f_rpm = int(round(float(fin.get("rpm", rpm * 1.5))))
        f_feed = float(fin.get("feed", feed * 0.3))
        L.append("(FINISH SKIM Z" + fmt(faceZ) + ")")
        L.append("S%d %s" % (f_rpm, spindle))
        passes = 1 + int(fin.get("springPasses", 0))
        for _ in range(passes):
            _emit_level(L, Gf, fsegs, faceZ, f_feed, f_feed, feed_plane)

    L.append("M09")
    L.append("M05")
    L.append("G91 G28 Z0.")
    L.append("G90")
    L.append("M30")
    L.append("%")
    return "\n".join(L)


def cycle_time(**P):
    """Rough estimate: feed path length / feed + rapids + level changes."""
    try:
        G = _build(P)
        segs = _level_segments(G)
        feed = float(P.get("feed", 400)) or 400.0
        depth = P.get("depth", {}) or {}
        topZ = float(depth.get("topZ", 0.0)); faceZ = float(depth.get("faceZ", -1.0))
        maxAp = float(depth.get("maxAp", 1.0)) or 1.0
        nlev = max(1, int(math.ceil(abs(topZ - faceZ) / maxAp)))
        cut_len = sum(math.hypot(x2 - x1, y2 - y1)
                      for (k, x1, y1, x2, y2) in segs if k == "cut")
        t_min = (cut_len * nlev) / feed
        return t_min * 60.0 + 6.0 * nlev
    except Exception:
        return 0.0
