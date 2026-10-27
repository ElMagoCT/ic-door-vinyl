"""verify.py [files]: re-render each finished SVG at 20 px/mm in overlapping 290 mm tiles and run
the rule check on the whole sheet, plus a roll-width check on every path. Writes ../.work/verify.json"""
import sys, os, re, json, glob, numpy as np
from lib import ROOT, WORK, PXMM, render
from rules import check
CORE, OV = 240.0, 25.0
PAIR = re.compile(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)')
ROLL, ROLL_USABLE = 304.8, 292.1          # 12 in roll, 11.5 in usable

def verify(fn):
    svg = open(fn).read(); W, H = (float(x) for x in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    res = dict(file=os.path.relpath(fn, ROOT), w_mm=round(W, 1), h_mm=round(H, 1), violations=[], tiles=0)
    body = re.search(r'<g id="vinyl".*</g>', svg, re.S).group(0)
    for j in range(int(np.ceil(H / CORE))):
        for i in range(int(np.ceil(W / CORE))):
            x0, y0, s = i * CORE - OV, j * CORE - OV, CORE + 2 * OV
            t = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {s} {s}" preserveAspectRatio="none">'
                 f'{body}</svg>')
            a = render(t, int(s * PXMM), int(s * PXMM)) < 128; res['tiles'] += 1
            for k, lst in check(a).items():
                for it in lst:
                    gx, gy = it[0] + x0, it[1] + y0
                    if i * CORE - 2 <= gx < (i + 1) * CORE + 2 and j * CORE - 2 <= gy < (j + 1) * CORE + 2:
                        res['violations'].append([k, round(gx, 1), round(gy, 1), *it[2:]])
    res['pieces'] = []
    for pid, d in re.findall(r'<path id="([^"]+)"[^>]*d="([^"]+)"', svg):
        xy = np.array([(float(a), float(b)) for a, b in PAIR.findall(d)])
        ext = sorted(xy.max(0) - xy.min(0))
        res['pieces'].append([pid, round(ext[0], 1), round(ext[1], 1), bool(ext[0] <= ROLL_USABLE)])
    res['fits_roll'] = all(p[3] for p in res['pieces'])
    return res

if __name__ == '__main__':
    fs = sys.argv[1:] or sorted(glob.glob(f'{ROOT}/logos/*.svg') + glob.glob(f'{ROOT}/concepts/*.svg'))
    os.makedirs(os.path.join(WORK, 'verify'), exist_ok=True)
    for f in fs:
        r = verify(f)
        print(r['file'], f"{r['w_mm']}x{r['h_mm']}mm", 'violations:', len(r['violations']), r['violations'][:4],
              'fits 12in roll:', r['fits_roll'], flush=True)
        json.dump(r, open(os.path.join(WORK, 'verify', os.path.basename(f) + '.json'), 'w'), indent=1)
