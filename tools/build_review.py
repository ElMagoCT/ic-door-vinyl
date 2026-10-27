"""Assembles ../review.html from review_template.html + the verified data."""
import json, os, glob, numpy as np
from lib import ROOT, WORK, path_mask
from pieces import source, piece, SRC
INFO = {
 'bb1': ('Robotics A · solid gear', 'Rebuilt 13-tooth gear; horse shading kept as cut-outs.'),
 'bb2': ('Robotics B · outline gear', 'Gear as a 3 mm outline. About 45% less vinyl, the horse reads in front.'),
 'cs1': ('CubeSat A · solid patch', 'The dark parts of the patch become vinyl. Most faithful to the original.'),
 'cs2': ('CubeSat B · line patch', 'Outlines and round stars only. Much lighter on the glass.'),
 'rc1': ('RC A · mark', 'The finished RC mark, already one colour.'),
 'rc2': ('RC B · tile', 'Rounded tile with the mark cut out of it.'),
 'rk':  ('Rocketry', 'B and two rockets, already one colour.'),
}
mins = json.load(open(f'{WORK}/minsize.json')); small = json.load(open(f'{WORK}/small.json'))
G = json.load(open(f'{WORK}/glyphs.json'))
logos = {}
for v in SRC:
    n = source(v); s = piece(v, small[v]['w'])
    V = path_mask(n['d'], n['w'], n['h'], pxmm=4); ys, xs = np.nonzero(V)
    fitR = float(np.hypot(xs - V.shape[1] / 2, ys - V.shape[0] / 2).max() / 4 / n['w'])
    logos[v] = dict(title=INFO[v][0], note=INFO[v][1], file=f'logos/{SRC[v]}.svg', fitR=round(fitR, 4),
                    native=dict(w=n['w'], h=n['h'], d=n['d'], min_w=mins[v]['min_w']),
                    small=dict(w=s['w'], h=s['h'], d=s['d'], min_w=small[v]['min_w']))
ver = [json.load(open(f)) for f in sorted(glob.glob(f'{WORK}/verify/*.json'))]
ver.sort(key=lambda r: (not r['file'].startswith('concepts'), r['file']))
import re
def bearings(g):   # left / right side bearing of the processed glyph, in cap heights
    xs = [float(a) for a, b in re.findall(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)', g['d'])]
    return (round(min(xs), 4), round(g['adv'] - max(xs), 4)) if xs else (g['adv'] / 2, g['adv'] / 2)
data = dict(logos=logos, glyphs={c: {'d': g['d'], 'adv': g['adv'], 'sb': bearings(g)} for c, g in G['glyphs'].items()},
            labelMinCap=G['C0'], verify=ver,
            gear=dict(vb=[-40, -40, 3273.07, 3261.2], C=[1607.3, 1591.8], RR=1265.2, RT=1596.0, N=13, PH=8.9,
                      HW_ROOT=184.6, HW_TIP=90.6))
t = open(os.path.join(os.path.dirname(__file__), 'review_template.html')).read()
out = t.replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
# local copy gets a full document; the artifact copy (no skeleton) is published from WORK
open(f'{ROOT}/review.html', 'w').write('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>\n' + out + '\n</body></html>\n')
open(f'{WORK}/review-artifact.html', 'w').write(out)
print('review.html', round(len(out) / 1e6, 2), 'MB')
