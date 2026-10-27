"""Small source versions for the browser editor (re-enforced at 125 mm / rocketry 88 mm). Each one's
real floor is found by scaling down in 2.5 % steps until a rule fails. Writes ../.work/small.json"""
import json, os, sys
from lib import WORK
from pieces import piece, SRC
from rules import check, DESIGN_TOL
from minsize import _scaled
out = json.load(open(os.path.join(WORK, 'small.json'))) if os.path.exists(os.path.join(WORK, 'small.json')) else {}
for v in (sys.argv[1:] or SRC):
    w = 88.0 if v == 'rk' else 125.0
    p = piece(v, w); f, last = 1.0, None
    while f > 0.5 and not any(check(_scaled(p['d'], p['w'], p['h'], f), tol=DESIGN_TOL).values()): last = f; f = round(f - 0.025, 3)
    out[v] = dict(w=p['w'], h=p['h'], clean=not p['check'], min_scale=last, min_w=round(p['w'] * last, 1) if last else None)
    print(v, out[v], flush=True)
json.dump(out, open(os.path.join(WORK, 'small.json'), 'w'), indent=1)
