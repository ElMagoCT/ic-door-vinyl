#!/usr/bin/env python3
"""Cut an exported door-vinyl SVG on the Graphtec CE6000 Plus over USB, with no vendor software.

  python3 tools/cut.py check [FILE.svg]      ask the cutter who it is and how big its cutting area is;
                                             says whether the job fits the loaded roll
  python3 tools/cut.py test                  cut a 24 mm "F" near the origin to confirm the orientation
  python3 tools/cut.py job FILE.svg          cut the whole file (centred across the usable width)
  python3 tools/cut.py hpgl FILE.svg         only write cut/<name>.plt and a preview PNG, send nothing
Add --mirror to test/job/hpgl if the test "F" came out backwards.

The SVG must be what review.html exports: mm, absolute M/L/C/Z paths, no transforms. Its height
runs along the roll (plotter X = media feed, origin at the front edge) and its width across the
carriage (plotter Y). HP-GL units are 0.025 mm. Curves are flattened to 0.01 mm. Each piece is cut
inside-out (small holes before the outline around them) and the pieces nearest the front edge go first.
"""
import argparse, math, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, 'cut')
USBPLOT = os.path.join(HERE, 'usbplot')
UNIT = 40          # HP-GL units per mm
TOL = 0.01         # curve flattening tolerance, mm
DEFAULT_SVG = os.path.join(OUTDIR, 'ic-door-stack-v2.svg')

NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
TOK = re.compile(r'[A-DF-Za-df-z]|' + NUM)

# ---------------------------------------------------------------- SVG path parsing
def _mid(a, b): return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

def _flat(p0, p1, p2, p3, out, depth=0):
    ax, ay = p0; dx, dy = p3[0] - ax, p3[1] - ay
    L = math.hypot(dx, dy)
    def dist(p):
        if L < 1e-9: return math.hypot(p[0] - ax, p[1] - ay)
        return abs((p[0] - ax) * dy - (p[1] - ay) * dx) / L
    if depth >= 16 or (dist(p1) <= TOL and dist(p2) <= TOL and L < 0.6):
        out.append(p3); return
    m01, m12, m23 = _mid(p0, p1), _mid(p1, p2), _mid(p2, p3)
    m012, m123 = _mid(m01, m12), _mid(m12, m23)
    m = _mid(m012, m123)
    _flat(p0, m01, m012, m, out, depth + 1)
    _flat(m, m123, m23, p3, out, depth + 1)

def parse(d):
    """SVG path data -> list of subpaths, each a list of (x, y) in the file's units, curves flattened."""
    toks = TOK.findall(d); i = 0; n = len(toks)
    subs = []; sp = None; cur = (0.0, 0.0); start = cur; cmd = None; last_c2 = None
    def nums(k):
        nonlocal i
        vals = []
        for _ in range(k):
            if i >= n or toks[i][0].isalpha(): raise ValueError(f'path data: expected a number at token {i}')
            vals.append(float(toks[i])); i += 1
        return vals
    while i < n:
        t = toks[i]
        if t.isalpha(): cmd = t; i += 1
        if cmd is None: raise ValueError('path data must start with a command letter')
        rel, C = cmd.islower(), cmd.upper()
        if C == 'Z':
            if sp:
                if sp[-1] != start: sp.append(start)
                subs.append(sp); sp = None
            cur = start; cmd = None; last_c2 = None; continue
        if C == 'M':
            x, y = nums(2)
            if rel: x += cur[0]; y += cur[1]
            if sp: subs.append(sp)
            sp = [(x, y)]; cur = start = (x, y); cmd = 'l' if rel else 'L'; last_c2 = None; continue
        if sp is None: sp = [cur]
        if C == 'L':
            x, y = nums(2)
            if rel: x += cur[0]; y += cur[1]
            cur = (x, y); sp.append(cur); last_c2 = None
        elif C == 'H':
            (x,) = nums(1); cur = (x + cur[0] if rel else x, cur[1]); sp.append(cur); last_c2 = None
        elif C == 'V':
            (y,) = nums(1); cur = (cur[0], y + cur[1] if rel else y); sp.append(cur); last_c2 = None
        elif C in 'CS':
            if C == 'C':
                x1, y1, x2, y2, x, y = nums(6)
                if rel: x1 += cur[0]; y1 += cur[1]; x2 += cur[0]; y2 += cur[1]; x += cur[0]; y += cur[1]
            else:
                x2, y2, x, y = nums(4)
                if rel: x2 += cur[0]; y2 += cur[1]; x += cur[0]; y += cur[1]
                x1, y1 = (2 * cur[0] - last_c2[0], 2 * cur[1] - last_c2[1]) if last_c2 else cur
            pts = []; _flat(cur, (x1, y1), (x2, y2), (x, y), pts)
            sp.extend(pts); last_c2 = (x2, y2); cur = (x, y)
        else:
            raise ValueError(f'unsupported path command {cmd!r} (export cut-ready files from review.html)')
    if sp: subs.append(sp)
    return subs

def bbox(subs):
    xs = [p[0] for sp in subs for p in sp]; ys = [p[1] for sp in subs for p in sp]
    return min(xs), min(ys), max(xs), max(ys)

def load_svg(path):
    s = open(path, encoding='utf-8').read()
    m = re.search(r'viewBox="\s*(%s)\s+(%s)\s+(%s)\s+(%s)' % ((NUM,) * 4), s)
    if not m: raise SystemExit(f'{path}: no viewBox')
    vx, vy, W, H = (float(v) for v in m.groups())
    if re.search(r'<(g|path)\b[^>]*\btransform=', s): raise SystemExit(f'{path}: transforms are not supported, export from review.html')
    pieces = []
    for m in re.finditer(r'<path\b([^>]*)>', s):
        attrs = m.group(1)
        d = re.search(r'\bd="([^"]*)"', attrs)
        if not d: continue
        pid = re.search(r'\bid="([^"]*)"', attrs)
        pid = pid.group(1) if pid else f'path{len(pieces)}'
        pieces.append((pid, [[(x - vx, y - vy) for x, y in sp] for sp in parse(d.group(1))]))
    return W, H, pieces

# ---------------------------------------------------------------- plotter geometry
def to_plotter(W, H, pieces, mirror=False, mx=10.0, my=2.0):
    """mm in the SVG -> integer HP-GL units. X along the feed (SVG top ends up farthest from the front
    edge), Y across the carriage (SVG right edge nearest the origin), so the sheet reads normally when
    you stand in front of the cutter. mx/my = margin from the origin in mm."""
    out = []
    for pid, subs in pieces:
        usubs = []
        for sp in subs:
            pts = []
            for x, y in sp:
                X = (H - y) + mx
                Y = (x if mirror else (W - x)) + my
                p = (int(round(X * UNIT)), int(round(Y * UNIT)))
                if not pts or pts[-1] != p: pts.append(p)
            if len(pts) >= 2: usubs.append(pts)
        def area(sp):
            xs = [p[0] for p in sp]; ys = [p[1] for p in sp]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))
        usubs.sort(key=area)                     # holes before the outline around them
        if usubs: out.append((pid, usubs))
    out.sort(key=lambda p: min(x for sp in p[1] for x, _ in sp))   # front edge first
    return out

def extents(upieces):
    xs = [p[0] for _, subs in upieces for sp in subs for p in sp]
    ys = [p[1] for _, subs in upieces for sp in subs for p in sp]
    return min(xs), min(ys), max(xs), max(ys)

def hpgl(upieces):
    x0, y0, x1, y1 = extents(upieces)
    out = ['IN;SP1;PA;']
    for pid, subs in upieces:
        for sp in subs:
            out.append(f'PU{sp[0][0]},{sp[0][1]};')
            rest = sp[1:]
            for k in range(0, len(rest), 20):
                chunk = rest[k:k + 20]
                out.append('PD' + ','.join(f'{x},{y}' for x, y in chunk) + ';')
    out.append(f'PU{x1 + 20 * UNIT},0;')         # park 20 mm past the far end: the whole job is out front
    out.append('SP0;')
    return '\n'.join(out) + '\n'

def preview(upieces, svg_path, title):
    """A PNG of the job as seen standing in front of the cutter: front edge (origin) at the bottom."""
    x0, y0, x1, y1 = extents(upieces)
    pad = 12; w = (y1 / UNIT) + 2 * pad; h = (x1 / UNIT) + 2 * pad
    d = ''.join('M' + ' '.join(f'{(y1 - Y) / UNIT + pad:.2f},{(x1 - X) / UNIT + pad:.2f}' for X, Y in sp) + 'Z'
                for _, subs in upieces for sp in subs)
    fs = max(4, min(w, h) / 24)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h:.1f}" width="{w:.1f}mm" height="{h:.1f}mm">'
           f'<rect width="100%" height="100%" fill="#dfe8ec"/>'
           f'<rect x="{pad}" y="{pad}" width="{y1 / UNIT:.2f}" height="{x1 / UNIT:.2f}" fill="none" stroke="#c33" stroke-width="0.4" stroke-dasharray="3 2"/>'
           f'<path fill="#111" fill-rule="evenodd" d="{d}"/>'
           f'<text x="{w / 2:.1f}" y="{h - 3:.1f}" font-family="Helvetica" font-size="{fs:.1f}" text-anchor="middle" fill="#c33">front edge of the roll / origin (you stand here) - {title}</text>'
           f'</svg>')
    open(svg_path, 'w').write(svg)
    png = svg_path[:-4] + '.png'
    subprocess.run(['qlmanage', '-t', '-s', '1600', '-o', os.path.dirname(svg_path), svg_path], capture_output=True)
    if os.path.exists(svg_path + '.png'): os.replace(svg_path + '.png', png)
    return png

def test_pieces():
    # a 24 mm tall "F" with 4 mm bars: it is chiral, so a mirrored cut is obvious at a glance
    d = 'M0,0 L16,0 L16,4 L4,4 L4,10 L12,10 L12,14 L4,14 L4,24 L0,24 Z'
    return 16.0, 24.0, [('F', parse(d))]

# ---------------------------------------------------------------- talking to the cutter
def usb(*args, check=False):
    if not os.path.exists(USBPLOT):
        raise SystemExit(f'{USBPLOT} is missing: clang -O2 -framework IOKit -framework CoreFoundation -o tools/usbplot tools/usbplot.c')
    r = subprocess.run([USBPLOT, *args], capture_output=True, text=True)
    if check and r.returncode not in (0, 5): raise SystemExit(r.stderr.strip() or f'usbplot exit {r.returncode}')
    return r

def limits():
    """(xmin, ymin, xmax, ymax) in HP-GL units: the cutter's current window (OW;, the area it will
    cut on the media it has measured), or None when it does not answer."""
    r = usb('query', 'OW;', '3000', check=True)
    m = re.search(r'(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)', r.stdout)
    return tuple(int(v) for v in m.groups()) if m else None

def describe_limits(lim):
    if not lim: return 'the cutter did not report its cutting window (no media set, or COMMAND is not AUTO/HP-GL)'
    x0, y0, x1, y1 = lim
    return f'cutting window reported by the cutter: {(x1 - x0) / UNIT:.0f} mm along the roll x {(y1 - y0) / UNIT:.1f} mm across the media (X {x0}..{x1}, Y {y0}..{y1} units)'

def fit(upieces, lim):
    x0, y0, x1, y1 = extents(upieces)
    if not lim: return None, f'job spans {x1 / UNIT:.1f} mm along the roll and needs {y1 / UNIT:.1f} mm across'
    ok = x0 >= lim[0] and y0 >= lim[1] and x1 <= lim[2] and y1 <= lim[3]
    return ok, (f'job X {x0 / UNIT:.1f}..{x1 / UNIT:.1f} mm, Y {y0 / UNIT:.1f}..{y1 / UNIT:.1f} mm -> '
                + ('fits' if ok else 'DOES NOT FIT') + f' the area Y {lim[1] / UNIT:.1f}..{lim[3] / UNIT:.1f} mm')

def build(W, H, pieces, args, lim):
    my = args.y_margin
    if lim and not args.no_center:                      # centre across the usable width
        my = ((lim[3] - lim[1]) / UNIT - W) / 2 + lim[1] / UNIT
        if my < 0: my = 0.5
    return to_plotter(W, H, pieces, mirror=args.mirror, mx=args.x_margin, my=my)

def write_job(name, upieces, title):
    os.makedirs(OUTDIR, exist_ok=True)
    plt = os.path.join(OUTDIR, name + '.plt')
    open(plt, 'w').write(hpgl(upieces))
    png = preview(upieces, os.path.join(OUTDIR, name + '-preview.svg'), title)
    npts = sum(len(sp) for _, subs in upieces for sp in subs)
    x0, y0, x1, y1 = extents(upieces)
    print(f'{plt}: {os.path.getsize(plt) / 1024:.0f} KB, {npts} points, '
          f'{x1 / UNIT:.1f} mm along the roll x {(y1 - y0) / UNIT:.1f} mm across (Y {y0 / UNIT:.1f}..{y1 / UNIT:.1f} mm)')
    print(f'preview: {png}')
    return plt

def send(plt):
    print(f'sending {plt} to the cutter ...')
    r = subprocess.run([USBPLOT, 'send', plt])
    if r.returncode: raise SystemExit(f'send failed (usbplot exit {r.returncode})')
    print('done: the cutter has all the data (it may still be cutting).')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['check', 'test', 'job', 'hpgl'])
    ap.add_argument('svg', nargs='?', default=DEFAULT_SVG)
    ap.add_argument('--mirror', action='store_true', help='flip across the roll (if the test F was backwards)')
    ap.add_argument('--x-margin', type=float, default=10.0, help='mm from the front edge/origin to the first cut')
    ap.add_argument('--y-margin', type=float, default=2.0, help='mm from the origin side when not centring')
    ap.add_argument('--no-center', action='store_true', help='do not centre across the reported cutting width')
    ap.add_argument('--force', action='store_true', help='cut even if the cutter says it does not fit')
    args = ap.parse_args()

    if args.cmd == 'hpgl':
        W, H, pieces = load_svg(args.svg)
        name = os.path.splitext(os.path.basename(args.svg))[0]
        write_job(name, build(W, H, pieces, args, None), name)
        write_job('test-F', to_plotter(*test_pieces(), mirror=args.mirror, mx=10, my=10), 'test F')
        return

    r = usb('query', 'OI;', '3000', check=True)
    ident = r.stdout.strip()
    print(f'cutter: {ident!r}' if ident else 'cutter: no reply to the HP-GL identify command (set COMMAND to AUTO or HP-GL on the panel; it must not be in a menu)')
    lim = limits()
    print(describe_limits(lim))
    if args.cmd == 'check':
        if os.path.exists(args.svg):
            W, H, pieces = load_svg(args.svg)
            up = build(W, H, pieces, args, lim)
            ok, msg = fit(up, lim); print(f'{os.path.basename(args.svg)}: {msg}')
        return
    if args.cmd == 'test':
        up = to_plotter(*test_pieces(), mirror=args.mirror, mx=10, my=10)
        plt = write_job('test-F', up, 'test F')
    else:
        W, H, pieces = load_svg(args.svg)
        up = build(W, H, pieces, args, lim)
        ok, msg = fit(up, lim); print(msg)
        if ok is False and not args.force: raise SystemExit('refusing to cut: move the pinch rollers out or use --force')
        plt = write_job(os.path.splitext(os.path.basename(args.svg))[0], up, os.path.basename(args.svg))
    send(plt)

if __name__ == '__main__':
    main()
