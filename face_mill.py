"""face_mill.py — YANTRA face-milling cut generator.

Fanuc I&J base program (tool-centre coords, G94 mm/min, G40 computer comp),
re-dialected by mill_post + offset by webpost, exactly like thread_mill.

    generate(**P) -> str        # Fanuc-base program text
    cycle_time(**P) -> float    # seconds
    sim_moves(**P) -> list      # tool-centre moves for the simulator
    SAFE_Z, fmt(v)

v1 scope: RASTER pattern (Both-ways / Climb / Conventional) over a rectangular
or circular area, with avoid zones (circle/rect) and do-not-cross barriers
respected by per-scanline interval clipping (tool centre kept a full radius +
clearance clear — never gouges).  CONTOUR falls back to raster (flagged).
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
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c)


def _rect_corners(area):
    x, y = area["x"], area["y"]; w, l = area["w"], area["l"]; rot = area.get("rot", 0)
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
    a = math.radians(-th); c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c)


def _to_world(x, y, th):
    a = math.radians(th); c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c)


def _merge(iv):
    iv = sorted(iv); out = []
    for a, b in iv:
        if out and a <= out[-1][1] + _EPS:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


# --------------------------------------------------------------------------- #
# geometry build (sweep frame) + raster row segments
# --------------------------------------------------------------------------- #
def _build(P):
    area = P["area"]; avoids = P.get("avoid", []) or []; barriers = P.get("noCross", []) or []
    D = float(P.get("D", 50.0)); r = D / 2.0
    tS = P.get("toolSide", {}) or {}
    a_over = float((tS.get("area", {}) or {}).get("overhang", 0.0))
    av_clr = float((tS.get("avoid", {}) or {}).get("clearance", 0.0))
    pat = P.get("pattern", {}) or {}
    kind = pat.get("kind", "raster"); direction = pat.get("direction", "bothWays")
    sweep = pat.get("sweepAngle", "auto"); ext = float(pat.get("passExtension", 0.0))
    stp = P.get("stepover", {}) or {}
    if stp.get("mode", "pctDia") == "mm" and stp.get("mm"):
        step = float(stp["mm"])
    else:
        step = D * float(stp.get("pctDia", 70)) / 100.0
    step = max(0.1, step); even = stp.get("even", True)

    if area["shape"] == "rect":
        base_rot = area.get("rot", 0)
        th = (base_rot + (0 if area["w"] >= area["l"] else 90)) if sweep == "auto" else float(sweep)
        cs = [_to_sf(px, py, th) for px, py in _rect_corners(area)]
        xs = [p[0] for p in cs]; ys = [p[1] for p in cs]
        amin_x, amax_x, amin_y, amax_y = min(xs), max(xs), min(ys), max(ys)

        def rowspan(yy):
            return (amin_x, amax_x) if amin_y - _EPS <= yy <= amax_y + _EPS else None
        y_lo, y_hi = amin_y, amax_y
    else:
        th = 0.0 if sweep == "auto" else float(sweep)
        cx, cy = _to_sf(area["x"], area["y"], th); cr = area["dia"] / 2.0
        amin_x, amax_x, amin_y, amax_y = cx - cr, cx + cr, cy - cr, cy + cr

        def rowspan(yy):
            d = cr * cr - (yy - cy) ** 2
            if d < 0:
                return None
            hw = math.sqrt(d)
            return (cx - hw, cx + hw)
        y_lo, y_hi = amin_y, amax_y

    av_sf = []
    for a in avoids:
        if a["shape"] == "circle":
            c = _to_sf(a["x"], a["y"], th); av_sf.append(("circle", c[0], c[1], a["dia"] / 2.0))
        else:
            cc = [_to_sf(px, py, th) for px, py in _rect_corners(a)]
            axs = [p[0] for p in cc]; ays = [p[1] for p in cc]
            av_sf.append(("rect", min(axs), min(ays), max(axs), max(ays)))
    bar_sf = []
    for b in barriers:
        pts = [_to_sf(px, py, th) for px, py in b["pts"]]
        bar_sf.append([(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)])

    def blocked(yy):
        iv = []
        for a in av_sf:
            if a[0] == "circle":
                keep = a[3] + r + av_clr; dy = abs(yy - a[2])
                if dy < keep:
                    dx = math.sqrt(keep * keep - dy * dy); iv.append((a[1] - dx, a[1] + dx))
            else:
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
                        xc = x1 + t * (x2 - x1); iv.append((xc - keepb, xc + keepb))
        return _merge(iv)

    covW = y_hi - y_lo
    if covW <= _EPS:
        rows = [y_lo]
    else:
        n = max(1, int(math.ceil(covW / step - _EPS))); astep = covW / n
        if not even:
            n = max(1, int(math.floor(covW / step + _EPS))); astep = step
        rows = [y_lo + i * astep for i in range(n + 1)]

    return {"th": th, "r": r, "step": step, "rows": rows, "rowspan": rowspan,
            "blocked": blocked, "ext": ext + r + a_over, "direction": direction,
            "bbox_sf": (amin_x, amax_x, amin_y, amax_y), "kind": kind}


def _level_segments(G, direction=None):
    r, rows, rowspan, blocked = G["r"], G["rows"], G["rowspan"], G["blocked"]
    ext = G["ext"]; direction = direction or G["direction"]
    segs = []; prev = None
    for i, yy in enumerate(rows):
        span = rowspan(yy)
        if span is None:
            continue
        xs, xe = span[0] - ext, span[1] + ext
        ltr = (i % 2 == 0) if direction == "bothWays" else (direction != "conventional")
        iv = []
        for a, b in blocked(yy):
            a, b = max(a, xs), min(b, xe)
            if b > a + _EPS:
                iv.append((a, b))
        iv = _merge(iv)
        pts = []; pos = xs
        for a, b in iv:
            if a > pos + _EPS:
                pts.append((pos, a, "cut"))
            pts.append((max(a, pos), b, "rapid")); pos = max(pos, b)
        if pos < xe - _EPS:
            pts.append((pos, xe, "cut"))
        if not pts:
            continue
        if not ltr:
            pts = [(b, a, k) for (a, b, k) in reversed(pts)]
        start_x = pts[0][0]
        if prev is not None:
            segs.append(("rapid", prev[0], prev[1], start_x, yy))
        for (a, b, k) in pts:
            segs.append((k, a, yy, b, yy))
        prev = (pts[-1][1], yy)
    return segs


# --------------------------------------------------------------------------- #
# moves (shared by generate + sim) — tool-centre, world coords
# --------------------------------------------------------------------------- #
def _level_moves(G, segs, z, feed, plunge_feed, feed_plane):
    th = G["th"]; bx0, bx1, by0, by1 = G["bbox_sf"]

    def over_mat(x1, y1, x2, y2):
        for (px, py) in ((x1, y1), (x2, y2), ((x1 + x2) / 2, (y1 + y2) / 2)):
            if bx0 - _EPS <= px <= bx1 + _EPS and by0 - _EPS <= py <= by1 + _EPS:
                return True
        return False

    M = []
    if not segs:
        return M
    fx, fy = segs[0][1], segs[0][2]
    wx, wy = _to_world(fx, fy, th)
    M.append(("rapid", wx, wy, SAFE_Z, None))
    M.append(("rapid", wx, wy, feed_plane, None))
    M.append(("feed", wx, wy, z, plunge_feed))
    lwx, lwy = wx, wy
    for (k, x1, y1, x2, y2) in segs:
        wx, wy = _to_world(x2, y2, th)
        if k == "cut":
            M.append(("feed", wx, wy, z, feed))
        else:
            if over_mat(x1, y1, x2, y2):
                pwx, pwy = _to_world(x1, y1, th)
                M.append(("rapid", pwx, pwy, feed_plane, None))
                M.append(("rapid", wx, wy, feed_plane, None))
                M.append(("feed", wx, wy, z, plunge_feed))
            else:
                M.append(("rapid", wx, wy, z, None))
        lwx, lwy = wx, wy
    M.append(("rapid", lwx, lwy, SAFE_Z, None))
    return M


def _fmt_moves(M):
    lines = []; px = py = pz = None
    for (k, x, y, z, f) in M:
        parts = []
        if px is None or abs(x - px) > 5e-5:
            parts.append("X" + fmt(x))
        if py is None or abs(y - py) > 5e-5:
            parts.append("Y" + fmt(y))
        if pz is None or abs(z - pz) > 5e-5:
            parts.append("Z" + fmt(z))
        if parts:
            ln = ("G00 " if k == "rapid" else "G01 ") + " ".join(parts)
            if k == "feed" and f is not None:
                ln += " F" + _ff(f)
            lines.append(ln)
        px, py, pz = x, y, z
    return lines


def _plan(P):
    D = float(P.get("D", 50.0)); feed = float(P.get("feed", 400))
    entry = P.get("entry", {}) or {}; heights = entry.get("heights", {}) or {}
    feed_plane = float(heights.get("feedPlane", 2.0))
    plunge_feed = float(entry.get("plungeFeed", feed * 0.5))
    depth = P.get("depth", {}) or {}
    topZ = float(depth.get("topZ", 0.0)); faceZ = float(depth.get("faceZ", -1.0))
    fin = P.get("finish", {}) or {}; fin_on = bool(fin.get("enabled", False))
    finishFloor = float(depth.get("finishFloorStock", 0.0)) if fin_on else 0.0
    rough = max(0.0, (topZ - faceZ) - finishFloor)
    maxAp = float(depth.get("maxAp", max(0.5, rough))) or 0.5
    if depth.get("mode") == "nLevels":
        nlev = max(1, int(depth.get("nLevels", 1)))
    else:
        nlev = max(1, int(math.ceil(rough / max(0.01, maxAp) - _EPS))) if rough > _EPS else 1
    ap = rough / nlev if nlev else rough
    z_levels = [topZ - ap * (i + 1) for i in range(nlev)]
    if z_levels:
        z_levels[-1] = faceZ + finishFloor
    G = _build(P); segs = _level_segments(G)
    pl = {"G": G, "segs": segs, "z_levels": z_levels, "faceZ": faceZ, "topZ": topZ,
          "feed": feed, "plunge_feed": plunge_feed, "feed_plane": feed_plane,
          "ap": ap, "nlev": nlev, "fin_on": fin_on and finishFloor > _EPS}
    if pl["fin_on"]:
        fstp = fin.get("stepover", {}) or {}
        Pf = dict(P); pat2 = dict(P.get("pattern", {}) or {}); pat2["direction"] = "climb"
        Pf["pattern"] = pat2
        Pf["stepover"] = {"mode": fstp.get("mode", "pctDia"), "pctDia": fstp.get("pctDia", 50),
                          "mm": fstp.get("mm"), "even": True}
        pl["Gf"] = _build(Pf); pl["fsegs"] = _level_segments(pl["Gf"], direction="climb")
        pl["f_rpm"] = int(round(float(fin.get("rpm", float(P.get("rpm", 1200)) * 1.5))))
        pl["f_feed"] = float(fin.get("feed", feed * 0.3))
        pl["springs"] = int(fin.get("springPasses", 0))
    return pl


# --------------------------------------------------------------------------- #
# public
# --------------------------------------------------------------------------- #
def generate(**P):
    area = P["area"]; D = float(P.get("D", 50.0))
    rpm = int(round(float(P.get("rpm", 1200)))); feed = float(P.get("feed", 400))
    spindle = P.get("spindle", "M03"); cool = P.get("coolant", "M08")
    safez = float(P.get("safez", SAFE_Z))
    pl = _plan(P); G = pl["G"]

    L = ["%"]
    dims = ("%gx%g" % (area["w"], area["l"])) if area["shape"] == "rect" else ("DIA %g" % area["dia"])
    L.append("O0001 (FACE MILL %s D%g %s PASS)" % (dims, D, G["kind"].upper()))
    L.append("(--- SUMMARY ---)")
    L.append("(TOOL      = FACE MILL D%g)" % D)
    L.append("(PATTERN   = %s / %s)" % (G["kind"], G["direction"]))
    L.append("(STEPOVER  = %.3f MM   DOC = %.3f MM x %d LVL)" % (G["step"], pl["ap"], pl["nlev"]))
    L.append("(TOP Z %s -> FACE Z %s)" % (fmt(pl["topZ"]), fmt(pl["faceZ"])))
    L.append("G90 G40 G17 G94")
    L.append("G54")
    L.append("M06 T1")
    L.append("G43 H1 Z" + fmt(safez))
    L.append("S%d %s" % (rpm, spindle))
    if cool and cool != "None":
        L.append(cool)
    if G["kind"] == "contour":
        L.append("(NOTE: contour pattern not in v1 - raster used)")

    for z in pl["z_levels"]:
        L.append("(ROUGH LEVEL Z" + fmt(z) + ")")
        L.extend(_fmt_moves(_level_moves(G, pl["segs"], z, feed, pl["plunge_feed"], pl["feed_plane"])))

    if pl["fin_on"]:
        L.append("(FINISH SKIM Z" + fmt(pl["faceZ"]) + ")")
        L.append("S%d %s" % (pl["f_rpm"], spindle))
        for _ in range(1 + pl["springs"]):
            L.extend(_fmt_moves(_level_moves(pl["Gf"], pl["fsegs"], pl["faceZ"],
                                             pl["f_feed"], pl["f_feed"], pl["feed_plane"])))

    L += ["M09", "M05", "G91 G28 Z0.", "G90", "M30", "%"]
    return "\n".join(L)


def sim_moves(**P):
    """Tool-centre moves for the simulator: list of [kind, x, y, z] world coords.
    kind = 'rapid' | 'feed'.  Also returns the tool dia as first element meta."""
    pl = _plan(P); D = float(P.get("D", 50.0)); topZ = pl["topZ"]
    out = []
    for z in pl["z_levels"]:
        for (k, x, y, zz, f) in _level_moves(pl["G"], pl["segs"], z, pl["feed"],
                                             pl["plunge_feed"], pl["feed_plane"]):
            out.append([k, round(x, 4), round(y, 4), round(zz, 4)])
    if pl["fin_on"]:
        for _ in range(1 + pl["springs"]):
            for (k, x, y, zz, f) in _level_moves(pl["Gf"], pl["fsegs"], pl["faceZ"],
                                                 pl["f_feed"], pl["f_feed"], pl["feed_plane"]):
                out.append([k, round(x, 4), round(y, 4), round(zz, 4)])
    return {"dia": D, "topZ": topZ, "moves": out}


def cycle_time(**P):
    try:
        pl = _plan(P); feed = pl["feed"] or 400.0
        cut = sum(math.hypot(x2 - x1, y2 - y1)
                  for (k, x1, y1, x2, y2) in pl["segs"] if k == "cut")
        t_min = (cut * pl["nlev"]) / feed
        extra = 0.0
        if pl["fin_on"]:
            fcut = sum(math.hypot(x2 - x1, y2 - y1)
                       for (k, x1, y1, x2, y2) in pl["fsegs"] if k == "cut")
            extra = (fcut * (1 + pl["springs"])) / (pl["f_feed"] or feed)
        return (t_min + extra) * 60.0 + 6.0 * pl["nlev"]
    except Exception:
        return 0.0
