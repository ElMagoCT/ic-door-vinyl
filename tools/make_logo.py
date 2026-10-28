"""make_logo.py SRC.svg OUT_NAME WIDTH_MM MODE "TITLE"
Turns a one-colour source logo into a cut-ready, rule-checked SVG in ../logos/.
MODE: 'mark' = every filled shape is vinyl, cropped to the art; 'tile' = coloured shapes are vinyl,
white shapes are cut out of them (full viewBox kept)."""
import sys, re, json, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from lib import ROOT, PXMM, render, path_mask
from rules import enforce, check, DESIGN_TOL
from trace import trace
src, name, width, mode, title = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
s = open(src).read()
s = re.sub(r'fill="(#[0-9A-Fa-f]{3,6})"', lambda m: 'fill="#fff"' if m.group(1).lower() in ('#fff', '#ffffff') else 'fill="#000"', s)
vb = [float(x) for x in re.search(r'viewBox="([^"]+)"', s).group(1).split()]
def with_vb(v): return re.sub(r'<svg\b[^>]*>', f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{v[0]} {v[1]} {v[2]} {v[3]}" preserveAspectRatio="none">', s, 1)
if mode == 'mark':
    a = render(with_vb(vb), 1500, int(1500 * vb[3] / vb[2])) < 128
    ys, xs = np.nonzero(a); k = vb[2] / 1500; p = 0.01 * vb[2]
    vb = [vb[0] + xs.min() * k - p, vb[1] + ys.min() * k - p, (xs.max() - xs.min() + 1) * k + 2 * p, (ys.max() - ys.min() + 1) * k + 2 * p]
wpx = int(round(width * PXMM)); hpx = int(round(wpx * vb[3] / vb[2]))
V = render(with_vb(vb), wpx, hpx) < 128
w, h = wpx / PXMM, hpx / PXMM
raw = {k2: v for k2, v in check(V, tol=DESIGN_TOL).items() if v}   # what fails as drawn, before any fix
log = []; E = enforce(V, log=log)
# where the enforcer changed the art: added vinyl (filled gaps / thickened) vs removed (slivers / tips)
changes = []
for kind, M in (('added', E & ~V), ('removed', V & ~E)):
    lab, n = ndi.label(M, structure=np.ones((3, 3)))
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        a = (lab[sl] == i).sum() / PXMM**2
        if a < 0.02: continue
        cy, cx = ndi.center_of_mass(lab == i) if a > 2 else ((sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2)
        changes.append(dict(kind=kind, area_mm2=round(a, 2), x_mm=round(cx / PXMM, 1), y_mm=round(cy / PXMM, 1),
                            src_x=round(vb[0] + cx / wpx * vb[2], 1), src_y=round(vb[1] + cy / hpx * vb[3], 1)))
img = np.full(V.shape + (3,), 255, np.uint8); img[V & E] = (60, 60, 60); img[E & ~V] = (220, 30, 40); img[V & ~E] = (30, 110, 230)
Image.fromarray(img).save(f'{ROOT}/.work/{name}-enforcer-diff.png')
json.dump(dict(raw_violations=raw, changes=changes), open(f'{ROOT}/.work/{name}-enforcer-report.json', 'w'), indent=1)
for rnd in range(6):
    d = trace(E); R = path_mask(d, w, h)
    bad = {k2: v for k2, v in check(R, tol=DESIGN_TOL).items() if v}
    log.append(f'round {rnd}: {sum(len(v) for v in bad.values())} issues')
    if not bad: break
    E = enforce(R, log=log, iters=1, minw=0.65 + 0.05 * rnd)
open(f'{ROOT}/logos/{name}.svg', 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.2f} {h:.2f}">\n'
    f'<title>{title}</title>\n<desc>Cut-ready at {w:.0f} mm wide. Only scale UP: shrinking breaks the 0.5 mm / 1 mm rules.</desc>\n'
    f'<g id="vinyl" fill="#000">\n  <path id="{name}" fill-rule="evenodd" d="{d}"/>\n</g>\n</svg>\n')
print(name, f'{w:.1f}x{h:.1f}mm', log, 'VIOLATIONS' if bad else 'clean', bad or '')
print('  as drawn:', {k2: len(v) for k2, v in raw.items()} or 'passes', '| enforcer changes:', len(changes))
for c in sorted(changes, key=lambda c: -c['area_mm2']): print('   ', c)
