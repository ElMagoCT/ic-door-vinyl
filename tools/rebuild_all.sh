#!/bin/bash
# Full rebuild: logos re-cleaned with margin -> letters -> editor limits -> concepts -> strict verify -> previews -> review page.
# Usage: PY=/path/to/venv/python ./rebuild_all.sh
set -e
cd "$(dirname "$0")"; PY=${PY:-../.venv/bin/python}; L=../.work/logs; mkdir -p $L
$PY -u reclean.py > $L/reclean.log 2>&1 & $PY -u glyphs.py > $L/glyphs.log 2>&1 & wait
rm -rf ../.work/pieces/* ../.work/small.json ../.work/minsize.json
$PY -u small.py > $L/small.log 2>&1 & $PY -u minsize.py > $L/minsize.log 2>&1 &
for c in stack corners chip band gears; do $PY -u concepts.py $c > $L/$c.log 2>&1 & done; wait
rm -rf ../.work/verify
# 4 at a time: each check renders 5800 px tiles in headless Chrome, and 13 at once can time out
ls ../logos/*.svg ../concepts/*.svg | xargs -P 4 -I{} sh -c '"$0" -u verify.py "{}" > "$1/v-$(basename "{}").log" 2>&1' "$PY" "$L"
$PY previews.py > $L/prev.log 2>&1
$PY build_review.py
grep -hv timestamp $L/reclean.log $L/small.log $L/minsize.log $L/v-*.log
grep -hv "clean$\|timestamp" $L/glyphs.log || true
