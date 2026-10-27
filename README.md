# IC Storage Room door vinyl

Single-colour cut-vinyl concepts for the IC Storage Room glass door (Robotics / Broncobots,
CubeSat / BrophySat-1, RC, Rocketry). Units are mm everywhere; every SVG is cut-ready
(one fill, outlined paths, no strokes, no transforms).

- `review.html` — open in a browser: concept editor with sliders, live rule checks, logo
  options and the verification table. (Also published privately as a claude.ai artifact.)
- `logos/` — each logo redrawn for one colour at 200 mm (Rocketry 140 mm). Only scale up.
- `concepts/` — 01a/01b stacked, 02 four corners, 03 IC chip circuit, 04 privacy band (knockout),
  05 gear train.
- `previews/` — white vinyl on dark glass PNGs.

## Cut rules (checked on the finished files)
- Nothing thinner than 0.5 mm, vinyl or gap.
- Anything thinner than 1 mm must run shorter than 10 mm.
- Every piece's short side ≤ 11.5 in (12 in roll).
Sharp corners taper to zero; a tip up to 0.6 mm counts as a corner, longer is a sliver.

## Rebuild
```bash
/opt/homebrew/bin/python3.12 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
tools/rebuild_all.sh          # re-clean logos, letters, editor limits, concepts, strict verify, previews, review.html
# swap in a new logo first if needed:
cd tools && ../.venv/bin/python make_logo.py SRC.svg rc-A-mark 200 mark "RC A - mark only"
```
Everything generated must clear a 10% design margin (0.55 mm / 1.1 mm); `verify.py` then checks the
finished files at exactly 0.5 / 1.0 mm. Letters are DIN Condensed Bold, processed at 10 mm (the minimum height).
Rendering uses headless Google Chrome. Caches live in `.work/` (safe to delete).
The Broncobots gear constants (13 teeth, fitted from the supplied art) are in `tools/concepts.py`.
