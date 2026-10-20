#!/bin/bash
# Seal one capture as soon as it is taken (REGISTRATION.md section 5.4): timestamp its manifest.json with OpenTimestamps
# and commit the directory with the receipt. The registered-capture rule counts only sealed captures: committed with no
# later change and carrying a receipt for the manifest's current bytes. The capture is committed even when the timestamp
# fails, but it does not count until a rerun of this script stamps it (rerunning is safe). A capture must not be rewritten
# (capture.py --dir into an existing directory adds a second command to its manifest and the rule then skips it) and
# must not be deleted (the commits record it).
# Usage (from prereg-nov2026/): bash scripts/seal_capture.sh            the newest capture
#                               bash scripts/seal_capture.sh data/raw/capture/<stamp>
set -euo pipefail
cd "$(dirname "$0")/.."
d="${1:-$(ls -d data/raw/capture/*/ | sort | tail -1)}"; d="${d%/}"
[ -f "$d/manifest.json" ] || { echo "no manifest in $d" >&2; exit 1; }
stamped=1
if [ ! -e "$d/manifest.json.ots" ]; then
  uvx --from opentimestamps-client ots stamp "$d/manifest.json" || stamped=0
fi
git add -- "$d"
git diff --cached --quiet -- "$d" || git commit -q -m "Capture $(basename "$d")

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- "$d"
if [ "$stamped" = 0 ]; then
  echo "committed $d, but the OpenTimestamps stamp failed: the capture does not count until you rerun: bash scripts/seal_capture.sh $d" >&2
  exit 1
fi
echo "sealed $d at $(git rev-parse --short HEAD)"
