"""Cut-safe letters: every DIN Condensed glyph is rasterised at the minimum cap height C0,
pushed through the same rule enforcer as the logos (sharp inside notches filled, slivers
removed), traced, and stored normalised to cap height 1. Text built from these only ever
scales UP from C0, which keeps it inside the rules. Writes ../.work/glyphs.json"""
import json, os, re
from lib import WORK, PXMM, render, path_mask
from rules import enforce, check, DESIGN_TOL
from trace import trace
import text as T
C0 = 10.0   # DIN stems are 0.143 x cap: at 10 mm every stroke is >= 1.3 mm, so nothing is thickened, only notches filled
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ·-.&/'#+!?,:()"
NUM = re.compile(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)')
out = {}
for c in CHARS:
    adv = T.GS[T.CM[ord(c)]].width / T.CAP
    if c == ' ': out[c] = {'d': '', 'adv': adv}; continue
    pad = 2.0; base = pad + C0 * 1.15
    W, H = adv * C0 + 2 * pad, C0 * 1.5 + 2 * pad
    d, _ = T.raw_text_path(c, pad, base, C0, anchor='start')   # glyph origin at the left pad
    V = path_mask(d, W, H)
    lg = []; E = enforce(V, log=lg)
    for _ in range(3):
        dd = trace(E); R = path_mask(dd, W, H)
        bad = {k: v for k, v in check(R, tol=DESIGN_TOL).items() if v}
        if not bad: break
        E = enforce(R, iters=1, minw=0.65 + 0.05 * _)
    norm = NUM.sub(lambda m: f'{(float(m.group(1)) - pad) / C0:.5f},{(float(m.group(2)) - base) / C0:.5f}', dd)
    out[c] = {'d': norm, 'adv': adv, 'clean': not bad}
    print(repr(c), lg[0], 'clean' if not bad else bad, flush=True)
json.dump({'C0': C0, 'glyphs': out}, open(os.path.join(WORK, 'glyphs.json'), 'w'))
