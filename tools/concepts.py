"""Builds the five layout concepts into ../concepts/. Run: python concepts.py [stack corners chip band gears]"""
import sys, math, re, numpy as np
from shapely.geometry import Polygon, LineString
from compose import *
from lib import path_mask

# Broncobots gear, fitted from the supplied art (units = the logo's padded viewBox)
BB_VB = [-40, -40, 3273.07, 3261.2]
BB_C = (1607.3, 1591.8); BB_R0, BB_RR, BB_RT, BB_N, BB_PH = 923.8, 1265.2, 1596.0, 13, 8.9
BB_HW_ROOT, BB_HW_TIP = 184.6, 90.6      # tooth half-chord at root / tip

def gear_path(cx, cy, N, Rr, Rt, hw_root, hw_tip, ph_deg, steps=10):
    pts = []
    for k in range(N):
        c = math.radians(ph_deg + k * 360 / N); nxt = math.radians(ph_deg + (k + 1) * 360 / N)
        ar, at = math.asin(hw_root / Rr), math.asin(hw_tip / Rt)
        pts += [(Rr, c - ar)] + [(Rt, t) for t in np.linspace(c - at, c + at, steps)] + [(Rr, c + ar)]
        pts += [(Rr, t) for t in np.linspace(c + ar, nxt - ar, steps * 2)[1:-1]]
    xy = [(cx + r * math.cos(t), cy + r * math.sin(t)) for r, t in pts]
    return 'M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in xy) + 'Z', Polygon(xy)

def stack(name, variants, title):
    sizes = {'bb': 200, 'cs': 200, 'rc': 200, 'rk': 140}
    ps = [piece(v, sizes[v[:2]]) for v in variants]
    CAP, GAPL, SP, M = 14, 12, 45, 20
    H = 2 * M + sum(p['h'] for p in ps) + len(ps) * (GAPL + CAP) + (len(ps) - 1) * SP
    doc = Doc(name, W11, H, title, 'Single-colour cut vinyl, mm. One 11 in wide strip.')
    y = M
    for v, p in zip(variants, ps):
        doc.logo(v, sizes[v[:2]], (W11 - p['w']) / 2, y); y += p['h'] + GAPL + CAP
        doc.text('label-' + v, LABEL[v[:2]], W11 / 2, y, CAP, track=4); y += SP
    return doc

def corners(gw=609.6, gh=914.4):
    doc = Doc('02-four-corners', gw, gh, 'Four corners', 'Laid out on a 24 x 36 in glass panel; each logo + label is its own piece.')
    M, CAP, GL = 38, 12, 10
    for v, w, hz, vt in [('bb1', 200, 'L', 'T'), ('cs1', 200, 'R', 'T'), ('rc1', 200, 'L', 'B'), ('rk', 140, 'R', 'B')]:
        p = piece(v, w)
        x = M if hz == 'L' else gw - M - p['w']
        y = M if vt == 'T' else gh - M - (p['h'] + GL + CAP)
        doc.logo(v, w, x, y)
        doc.text('label-' + v, LABEL[v[:2]], x + p['w'] / 2, y + p['h'] + GL + CAP, CAP, track=3.5)
    return doc

def chip():
    LW, TR = 165, 3.2
    logos = [('bb1', LW), ('cs1', LW), ('rc1', LW), ('rk', round(LW * 0.70, 1))]
    ps = [piece(v, w) for v, w in logos]
    BX, BY, BW, BH, band = 25, 40, 229.4, 112, 4.5
    doc = Doc('03-ic-chip-circuit', W11, 10, 'IC chip circuit',
              'The IC Storage Room as an integrated circuit: four clubs wired to one chip. Traces 3.2 mm.')
    nx = BX + BW / 2; r1 = 11
    body = Polygon([(BX, BY), (BX + BW, BY), (BX + BW, BY + BH), (BX, BY + BH)]).buffer(-6).buffer(6)
    inner = Polygon([(BX + band, BY + band), (BX + BW - band, BY + band), (BX + BW - band, BY + BH - band),
                     (BX + band, BY + BH - band)]).buffer(-3).buffer(3)
    notch = Polygon([(nx + (r1 + band) * math.cos(t), BY + band + (r1 + band) * math.sin(t)) for t in np.linspace(0, math.pi, 40)])
    hole = Polygon([(nx + r1 * math.cos(t), BY + band + r1 * math.sin(t)) for t in np.linspace(0, math.pi, 40)])
    npins, pw, ph = 8, 10, 16; pitch = (BW - 40) / (npins - 1)
    pinx = [BX + 20 + i * pitch for i in range(npins)]
    shape = body.difference(inner).union(notch).difference(hole.buffer(0))
    for px in pinx:
        shape = shape.union(Polygon([(px - pw/2, BY - ph), (px + pw/2, BY - ph), (px + pw/2, BY + 1), (px - pw/2, BY + 1)]))
        shape = shape.union(Polygon([(px - pw/2, BY + BH - 1), (px + pw/2, BY + BH - 1), (px + pw/2, BY + BH + ph), (px - pw/2, BY + BH + ph)]))
    doc.text('chip-ic', 'IC', nx, BY + BH / 2 + 18, 40, track=4)
    doc.text('chip-sub', 'ROBOTICS · CUBESAT · RC · ROCKETRY', nx, BY + BH - 14, 10, track=1.0)
    doc.text('chip-p1', '1', pinx[0], BY + band + 18, 10)
    trace = lambda pts: LineString(pts).buffer(TR / 2, cap_style=2, join_style=1)
    disc = lambda x, y, r: Polygon([(x + r * math.cos(t), y + r * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 48)])
    via = lambda x, y, ro, ri: disc(x, y, ro).difference(disc(x, y, ri))
    for i, px in enumerate(pinx):      # top pins: alternate stubs to vias
        if i % 2: shape = shape.union(trace([(px, BY - ph + 1), (px, BY - ph - 10.5)])).union(via(px, BY - ph - 14, 5, 2))   # stub ends inside the via ring, not in its hole
    LX, y = 14, BY + BH + ph + 40
    lanes = [W11 - 14 - 45 + 15 * k for k in range(4)]
    pads = []
    for (v, w), p in zip(logos, ps):
        x = LX + (LW - p['w']) / 2
        doc.logo(v, w, x, y)
        doc.text('label-' + v, LABEL[v[:2]], LX + LW / 2, y + p['h'] + 20, 10, track=3)
        pads.append((x + p['w'], y + p['h'] / 2)); y += p['h'] + 58
    doc.h = y - 58 + 25
    y0 = BY + BH + ph
    for k in range(4):
        sx, lx = pinx[4 + k], lanes[k]
        ya = y0 + 8; yb = ya + (lx - sx)
        px, py = pads[k]; padx = px + 16; ex = padx + 6
        shape = shape.union(trace([(sx, y0 - 1), (sx, ya), (lx, yb), (lx, py - (lx - ex)), (ex, py)])).union(via(padx, py, 6.5, 2.4))
    for i in range(4):
        px = pinx[i]
        shape = shape.union(trace([(px, y0 - 1), (px, y0 + 12)])).union(via(px, y0 + 16.5, 5, 2))
    doc.add('chip-and-traces', poly_d(shape))
    return doc

def band(L=762.0, HB=W11):
    doc = Doc('04-privacy-band-knockout', L, HB, 'Privacy band',
              'One solid 11 x 30 in band (frosted / etched-look vinyl is ideal) with the logos cut out of it. Cuts along the roll.')
    LH, CAP = 158, 13
    vs = ['bb1', 'cs1', 'rc1', 'rk']
    asp = {v: piece(v, 140 if v == 'rk' else 200)['w'] / piece(v, 140 if v == 'rk' else 200)['h'] for v in vs}
    ws = [round(LH * asp[v], 1) for v in vs]
    gap = (L - sum(ws)) / (len(ws) + 1)
    d = rect_d(0, 0, L, HB, 10); x = gap; top = (HB - (LH + 12 + CAP)) / 2
    for v, w in zip(vs, ws):
        p = piece(v, w)
        d += shift(p['d'], x, top + (LH - p['h']) / 2)
        d += text_path(LABEL[v[:2]], x + w / 2, top + LH + 12 + CAP, CAP, 3.5)[0]
        x += w + gap
    return doc.add('band', d)

def fit_in_circle(v, R):
    """largest width at which the logo's vinyl stays inside radius R of its bbox centre"""
    p = piece(v, 140 if v == 'rk' else 200)
    Vm = path_mask(p['d'], p['w'], p['h'], pxmm=4)
    ys, xs = np.nonzero(Vm)
    rmax = np.hypot(xs - Vm.shape[1] / 2, ys - Vm.shape[0] / 2).max() / 4
    return round(p['w'] * R / rmax, 1)

def gears():
    WB = 190.0; s = WB / BB_VB[2]
    m = (BB_RR + BB_RT) / BB_N * s          # module: pitch diameter / teeth (mm)
    add = (BB_RT - BB_RR) / 2 * s
    hw_r, hw_t = BB_HW_ROOT * s, BB_HW_TIP * s
    ringw = (BB_RR - BB_R0) * s * 0.62
    CLR, M = 2.0, 8
    spec = [('bb1', 13), ('cs1', 14), ('rc1', 13), ('rk', 13)]
    side = ['L', 'R', 'L', 'R']
    doc = Doc('05-gear-train', W11, 10, 'Gear train',
              'Four meshing gears, one per club. The Broncobots gear sets the tooth size; each gear is its own piece.')
    RpB = m * 13 / 2; c0 = (M + RpB + add + 4, M + RpB + add + 4)
    doc.logo('bb1', WB, c0[0] - (BB_C[0] - BB_VB[0]) * s, c0[1] - (BB_C[1] - BB_VB[1]) * s, id='bb1-gear')
    prev = gear_path(*c0, 13, RpB - add, RpB + add, hw_r, hw_t, BB_PH)[1]
    info = [(c0, RpB)]; doc.meshclear = []; polys = [prev]
    for k in range(1, 4):
        v, N = spec[k]; Rp = m * N / 2; Rt = Rp + add
        (pcx, pcy), pRp = info[-1]
        cx = (W11 - M - Rt - 2) if side[k] == 'R' else (M + Rt + 2)
        dist = pRp + Rp + CLR
        cy = pcy + math.sqrt(dist**2 - (cx - pcx)**2)
        best = max(((gear_path(cx, cy, N, Rp - add, Rt, hw_r, hw_t, ph)[1].distance(prev), ph)
                    for ph in np.linspace(0, 360 / N, 121, endpoint=False)))
        gd, prev = gear_path(cx, cy, N, Rp - add, Rt, hw_r, hw_t, best[1])
        doc.meshclear.append(round(best[0], 2)); polys.append(prev)
        Rh = Rp - add - ringw
        doc.add(f'gear-{v}', gd + circ(cx, cy, Rh))
        fw = fit_in_circle(v, Rh - 5); p = piece(v, fw)
        doc.logo(v, fw, cx - p['w'] / 2, cy - p['h'] / 2)
        info.append(((cx, cy), Rp))
    from shapely.geometry import box
    for k, ((cx, cy), Rp) in enumerate(info):          # label in the free space beside each gear
        lab = LABEL[spec[k][0][:2]]; placed = False
        for cap in (12, 11, 10, 9):
            w = text_path(lab, 0, 0, cap, 3)[1]
            x0 = W11 - M - 2 - w if side[k] == 'L' else M + 2
            for dy in sorted(np.arange(-0.6 * Rp, 0.6 * Rp, 2.0), key=abs):
                y = cy + cap / 2 + dy
                if min(box(x0, y - cap, x0 + w, y).distance(g) for g in polys) >= 5:
                    doc.text('label-' + spec[k][0], lab, x0, y, cap, track=3, anchor='start'); placed = True; break
            if placed: break
        assert placed, lab
    doc.h = info[-1][0][1] + info[-1][1] + add + M + 4
    return doc

if __name__ == '__main__':
    for w in sys.argv[1:] or ['stack', 'corners', 'chip', 'band', 'gears']:
        if w == 'stack':
            print(stack('01a-stack-solid', ['bb1', 'cs1', 'rc1', 'rk'], 'Stacked - solid badges').save())
            print(stack('01b-stack-line', ['bb2', 'cs2', 'rc1', 'rk'], 'Stacked - outline badges').save())
        if w == 'corners': print(corners().save())
        if w == 'chip': print(chip().save())
        if w == 'band': print(band().save())
        if w == 'gears': g = gears(); print(g.save(), 'mesh clearances mm', g.meshclear)
