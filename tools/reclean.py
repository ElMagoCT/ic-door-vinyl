"""reclean.py: re-run the closed loop on the finished logos in ../logos/ against the strict checker
(no slack). Backs the old files up to ../.work/logos-before-strict/ first."""
import os, re, shutil, glob
from lib import ROOT, WORK, PXMM, render, path_mask
from rules import enforce, check, DESIGN_TOL
from trace import trace
os.makedirs(f'{WORK}/logos-before-strict', exist_ok=True)
for fn in sorted(glob.glob(f'{ROOT}/logos/*.svg')):
    shutil.copy(fn, f'{WORK}/logos-before-strict/')
    s = open(fn).read()
    w, h = (float(x) for x in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s).groups())
    d = re.search(r' d="([^"]+)"', s).group(1)
    R = path_mask(d, w, h); bad = {k: v for k, v in check(R, tol=DESIGN_TOL).items() if v}; log = [f'before: {sum(map(len, bad.values()))} issues']
    rnd = 0
    while bad and rnd < 6:
        E = enforce(R, log=log, iters=1, minw=0.65 + 0.05 * rnd)
        d = trace(E); R = path_mask(d, w, h)
        bad = {k: v for k, v in check(R, tol=DESIGN_TOL).items() if v}; log.append(f'round {rnd}: {sum(map(len, bad.values()))}'); rnd += 1
    s = re.sub(r' d="[^"]+"', f' d="{d}"', s, count=1)
    open(fn, 'w').write(s)
    print(os.path.basename(fn), log, 'CLEAN' if not bad else bad, flush=True)
