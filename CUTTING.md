# Cutting the door vinyl on the Graphtec CE6000 Plus (from this Mac)

No Graphtec software is needed. `tools/usbplot` (a 150-line IOKit program) talks to the cutter over
USB - it shows up as a USB printer-class device - and `tools/cut.py` turns an exported stack SVG into
HP-GL (the cutter answers the identify command with `7586`, Graphtec's HP 7586 emulation; units are
0.025 mm) and streams it. Everything lives in this folder, so it works again next time.

```bash
cd ~/Documents/Workspace/ic-door-vinyl
python3 tools/cut.py check      # who is on USB, the cutting window it measured, does the job fit
python3 tools/cut.py test       # cuts a 24 mm "F" 10 mm in from the origin corner
python3 tools/cut.py job        # cuts cut/ic-door-stack-v2.svg (add a path for another file)
python3 tools/cut.py hpgl FILE  # only writes cut/<name>.plt + a preview PNG, sends nothing
```

Add `--mirror` to `test`/`job` if the test F comes out backwards (see step 7).

## On the cutter

1. **Blade.** A CB09U (45°, the standard blue-cap holder) with the blade tip showing about the
   thickness of a credit card. Seat the holder in the carriage clamp and tighten the thumbscrew.
2. **Load the roll.** Roll on the stocker bars at the back, vinyl face up, media set lever **up**.
   Feed the vinyl forward under the pinch rollers until about 30 cm hangs out the front, square it
   to the guide lines on the platen. Each pinch roller must sit over a grit roller (the arrow marks
   on the rail above show where they are) and about 5 mm in from the vinyl's edge on each side -
   the manual wants at least 5 mm for jobs under 2 m. Lever **down**.
3. **Media type.** The display asks how the media is loaded: pick **ROLL-1 FRONT EDGE**. The cutter
   measures the width and puts the origin at the front edge, right-hand side (as you face it).
   That measured width is what `cut.py check` reads back; the job needs 271 mm across and a 12-inch
   roll gives about 293 mm.
4. **Interface.** MENU -> I/F (interface): **COMMAND = AUTO** (or HP-GL) and, for HP-GL,
   **ORIGIN = LOWER LEFT**. These were already right when the Mac first talked to it.
5. **Cutting condition.** Make **CONDITION 1** the current one (the job selects it with `SP1`):
   tool **CB09U**, FORCE **12** to start, SPEED **30**, QUALITY **2**. Press the cutter's own
   **TEST** key once: weed the little square/triangle it cuts. The vinyl should lift cleanly with the
   backing paper only scored, not cut through. Raise FORCE by 2 if the vinyl does not release,
   lower it if the backing is cut.
6. **Feed check for a long job.** The stack is 1.37 m long. Use the arrow keys (with the lever
   down, from the ready screen) to run about 1.5 m of vinyl forward and back once; it should track
   straight without walking under either pinch roller. A media basket or a clear floor in front
   stops it crumpling.
7. **Test F from the Mac** (`cut.py test`). Stand in front of the cutter, look down at the vinyl
   from above. A correct F has its two bars pointing to your **right** and its stem on the left, with
   the top bar away from you. Bars pointing left = mirrored: rerun with `--mirror`, and cut the job
   with `--mirror` too.
8. **The job** (`cut.py job`). It refuses to start if the measured window is narrower than the job,
   centres the design across the window, cuts pieces nearest the front edge first and each piece
   inside-out (holes before outlines), then parks 20 mm past the far end so the whole sheet is out
   the front. Cut it off in the cross-cut groove, weed, apply transfer tape.

Previews of exactly what will be cut are in `cut/`: `ic-door-stack-v2-design.png` (the design) and
`ic-door-stack-v2-preview.png` (as laid on the roll, origin at the bottom).

## If something is off

- `usbplot: no Graphtec CE6000 Plus on USB` - switch the cutter on / replug; `cut.py check` lists it.
- `cannot open the cutter's USB interface` - another program has it open (Chrome's WebUSB prompt,
  a print queue); close it.
- No reply to `check` - the cutter is inside a menu, or COMMAND is set to GP-GL. Back out to the
  ready screen.
- The job sends in seconds but the cutter keeps cutting for a while: that is normal, it buffers.
  To stop mid-job press the cutter's pause/stop and clear its buffer from the panel; the Mac side
  has nothing left to cancel once `usbplot` returns.
- Re-exporting from `review.html`: run `python3 tools/restack.py IN.svg OUT.svg bb rc rk cs` to keep
  the CubeSat-at-the-bottom order, then `cut.py job OUT.svg`.
