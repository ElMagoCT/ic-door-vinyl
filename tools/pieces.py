"""Cut-ready logo pieces at any size. Source = the verified 200 mm logos in ../logos/.
A resized piece is re-rasterised at 20 px/mm, re-enforced, re-traced and re-checked
(closed loop) - so a smaller logo is thickened where needed, never just shrunk."""
import os, re, json
from lib import ROOT, WORK, PXMM, path_mask, render
from rules import enforce, check, DESIGN_TOL
from trace import trace
SRC = {'bb1': 'robotics-A-solid-gear', 'bb2': 'robotics-B-outline-gear', 'cs1': 'cubesat-A-solid-patch',
       'cs2': 'cubesat-B-line-patch', 'rc1': 'rc-A-mark', 'rc2': 'rc-B-tile', 'rk': 'rocketry-mark'}
PD = os.path.join(WORK, 'pieces'); os.makedirs(PD, exist_ok=True)

def source(v):
    s = open(f'{ROOT}/logos/{SRC[v]}.svg').read()
    w, h = (float(x) for x in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s).groups())
    return dict(variant=v, w=w, h=h, d=re.search(r'<path id="[^"]+" fill-rule="evenodd" d="([^"]+)"', s).group(1))

def piece(v, w_mm, force=False):
    src = source(v)
    if abs(w_mm - src['w']) < 0.05: return src
    fn = f'{PD}/{v}_{w_mm:.1f}.json'
    if os.path.exists(fn) and not force: return json.load(open(fn))
    h_mm = src['h'] * w_mm / src['w']
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {src["w"]} {src["h"]}" preserveAspectRatio="none">'
           f'<path fill-rule="evenodd" d="{src["d"]}"/></svg>')
    V = render(svg, int(round(w_mm * PXMM)), int(round(h_mm * PXMM))) < 128
    w_mm, h_mm = V.shape[1] / PXMM, V.shape[0] / PXMM
    log = []; E = enforce(V, log=log)
    for rnd in range(6):
        d = trace(E); R = path_mask(d, w_mm, h_mm)
        bad = {k: x for k, x in check(R, tol=DESIGN_TOL).items() if x}
        log.append(f'round {rnd}: {sum(len(x) for x in bad.values())} issues')
        if not bad: break
        E = enforce(R, log=log, iters=1, minw=0.65 + 0.05 * rnd)
    out = dict(variant=v, w=w_mm, h=h_mm, d=d, log=log, check=bad)
    json.dump(out, open(fn, 'w')); return out
