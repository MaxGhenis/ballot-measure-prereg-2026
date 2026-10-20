#!/bin/bash
# Freeze the registration: check that the power results match the registry, run the tests, checksum every file,
# timestamp the checksums with OpenTimestamps, commit, tag prereg-nov2026-v1, and write FREEZE.md.
# Usage (from prereg-nov2026/): bash scripts/freeze.sh
#
# What the freeze establishes. The commit, tag and SHA256SUMS fix the content: anyone holding the files can check them
# against the sums. A local commit's date can be rewritten, so the date comes from OpenTimestamps: `ots stamp` sends a
# salted hash of SHA256SUMS (nothing else leaves the machine) to public calendar servers, which commit it to the Bitcoin
# blockchain within hours. `ots upgrade SHA256SUMS.ots` completes the proof once that happens (RUNBOOK step 1), and
# `ots verify SHA256SUMS.ots` shows the earliest time the sums existed. A private timestamp proves the registration
# existed by then, not that it was the only one; publishing it (OSF or a public repository) is Max's call.
#
# Safe to rerun: nothing is committed or tagged until the timestamp succeeds, and a step already done is skipped.
set -euo pipefail
cd "$(dirname "$0")/.."
if git rev-parse -q --verify refs/tags/prereg-nov2026-v1 >/dev/null && [ -e FREEZE.md ]; then echo "already frozen:"; cat FREEZE.md; exit 0; fi
grep -q 'draft, not yet frozen' REGISTRATION.md && { echo "REGISTRATION.md still says draft"; exit 1; }
# results/power.json must have been computed from the files being frozen
python3 - <<'EOF'
import hashlib, json, pathlib, sys
d = json.load(open("results/power.json"))
bad = [f for f, h in d.get("inputs_sha256", {}).items() if hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest() != h]
if not d.get("inputs_sha256") or bad: sys.exit(f"results/power.json is stale for {bad or 'all inputs'}: rerun scripts/power.py")
EOF
python3 scripts/fill_power_summary.py > /dev/null   # section 7 states exactly what results/power.json holds
grep -q 'power-summary:start' REGISTRATION.md || { echo "REGISTRATION.md has no power summary"; exit 1; }
BT=$(mktemp -d); trap 'rm -rf "$BT"' EXIT        # pytest.ini deletes each passing test's synthetic capture (peak about 110 MB); this removes the rest
uv run --no-project --python 3.12 --with pytest --with hypothesis --with numpy --with pandas python -m pytest -q -p no:cacheprovider --basetemp "$BT/pt" tests/ | tee tests/last_run.txt
# Every file except the freeze outputs themselves, caches and Finder metadata.
find . -type f -not -path './.pytest_cache/*' -not -path './.hypothesis/*' -not -path '*/__pycache__/*' -not -name SHA256SUMS \
  -not -name 'SHA256SUMS.ots' -not -name FREEZE.md -not -name '.DS_Store' | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS
rm -f SHA256SUMS.ots
uvx --from opentimestamps-client ots stamp SHA256SUMS      # fails before anything is committed if the calendars are unreachable
git add -A .
git diff --cached --quiet || git commit -q -m "Freeze: November 3, 2026 ballot-measure pre-registration v1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git rev-parse -q --verify refs/tags/prereg-nov2026-v1 >/dev/null || git tag -a prereg-nov2026-v1 -m "November 3, 2026 ballot-measure pre-registration, v1"
C=$(git rev-parse prereg-nov2026-v1^{commit})
N=$(wc -l < SHA256SUMS | tr -d ' ')
cat > FREEZE.md <<EOF2
# Freeze record

- Registration: \`REGISTRATION.md\`, sha256 $(shasum -a 256 REGISTRATION.md | cut -d' ' -f1)
- Every registered file ($N files): \`SHA256SUMS\`, sha256 $(shasum -a 256 SHA256SUMS | cut -d' ' -f1). Excluded: \`SHA256SUMS\`, \`SHA256SUMS.ots\` and \`FREEZE.md\` themselves, \`.pytest_cache/\`, \`.hypothesis/\`, \`__pycache__/\` and \`.DS_Store\`.
- Commit: $C (tag \`prereg-nov2026-v1\`) in the repository at ~/reviews/policy-conditional-markets-2026-10
- Frozen (local clock): $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Independent timestamp: \`SHA256SUMS.ots\` (OpenTimestamps), committed with the freeze. Only a salted hash of \`SHA256SUMS\` was sent to the public calendars. After the Bitcoin attestation, \`ots upgrade SHA256SUMS.ots\` completes the proof and \`ots verify SHA256SUMS.ots\` reports the earliest time the sums existed. It proves the registration existed by then, not that it was the only one.
- Public: not yet. Publishing (OSF or a public repository) is Max's decision; the repository has no remote.

Verify the files: \`shasum -a 256 -c SHA256SUMS\` from this folder. \`scripts/run_analysis.py\` checks every file in the sums outside \`data/raw/capture/\` and \`results/\` on every run, records the result, and lists files the sums do not cover. Files added after the freeze (captures, results, \`DEVIATIONS.md\`) are not in the sums.
EOF2
git add FREEZE.md
git diff --cached --quiet || git commit -q -m "Freeze record for prereg-nov2026-v1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
cat FREEZE.md
