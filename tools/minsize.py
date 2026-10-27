"""For each logo, the smallest size the browser sliders may scale it to: the verified art is
scaled down in 2.5 % steps and re-checked (no thickening) until a rule fails. Writes ../.work/minsize.json"""
import json, os, sys
from lib import WORK, path_mask
from rules import check, DESIGN_TOL
from pieces import source, SRC
def ok(d, w, h, f): return not any(check(_scaled(d, w, h, f), tol=DESIGN_TOL).values())
def _scaled(d, w, h, f):
    from lib import render, PXMM
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
           f'<path fill-rule="evenodd" d="{d}"/></svg>')
    return render(svg, int(round(w * f * PXMM)), int(round(h * f * PXMM))) < 128
if __name__ == '__main__':
    out = json.load(open(os.path.join(WORK, 'minsize.json'))) if os.path.exists(os.path.join(WORK, 'minsize.json')) else {}
    for v in (sys.argv[1:] or SRC):
        s = source(v); f, last = 1.0, None
        while f > 0.4 and ok(s['d'], s['w'], s['h'], f): last = f; f = round(f - 0.025, 3)
        out[v] = dict(native_w=s['w'], native_h=s['h'], min_scale=last, min_w=round(s['w'] * last, 1) if last else None)
        print(v, out[v], flush=True)
    json.dump(out, open(os.path.join(WORK, 'minsize.json'), 'w'), indent=1)
