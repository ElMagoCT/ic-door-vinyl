# IC Storage Room door vinyl — notes for Claude

Single-colour cut-vinyl concepts (Robotics, CubeSat, RC, Rocketry) for the IC
Storage Room glass door, built 2026-10-26. `review.html` = slider editor +
verification table. Public repo **https://github.com/ElMagoCT/ic-door-vinyl**,
GitHub Pages at **https://elmagoct.github.io/ic-door-vinyl/** (pushes to `main`
publish; made public 2026-10-27 at Micah's request). Also a private claude.ai
artifact. Local: `python3 -m http.server 8811`. See `README.md`; cutting on the
Graphtec is in `CUTTING.md`. Rules (Micah's): nothing < 0.5 mm, < 1 mm only for
runs < 10 mm, pieces ≤ 11.5 in (12 in roll).

- Pipeline (tools/): render with headless Chrome at 20 px/mm → `rules.enforce` →
  potrace → re-render + `rules.check` (closed loop). `verify.py` re-checks finished
  SVGs in tiles. venv is NOT kept: create `.venv` from tools/requirements.txt.
- potracer treats False as ink: trace `~mask`. Paths are absolute 'x,y' pairs so
  `shift()`/JS `bake()` work; no arc commands.
- Text comes from `.work/glyphs.json` (DIN Condensed run through the enforcer at
  10 mm cap); never go below 10 mm caps.
- Generate with `DESIGN_TOL` = 1.1 margin, verify at exactly 1.0: features right
  at 0.50 mm flip pass/fail with pixel alignment.
- `tools/rebuild_all.sh` runs everything; verify at most ~4 files in parallel or
  Chrome renders time out.
- RC logo source = `../brophy-rc-logo/final/` (rebuild with `make_logo.py` when
  it changes).
