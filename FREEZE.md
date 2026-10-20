# Freeze record

- Registration: `REGISTRATION.md`, sha256 c3b0ebb372f783bafb7e03c41770d6a10fea4e94137f7ecb22cab03c2df6065e
- Every registered file (1299 files): `SHA256SUMS`, sha256 f4d6c50ab8412514e5d4c36e0bd0306e301d28d014520c5425bdc0a9602b40b3. Excluded: `SHA256SUMS`, `SHA256SUMS.ots` and `FREEZE.md` themselves, `.pytest_cache/`, `.hypothesis/`, `__pycache__/` and `.DS_Store`.
- Commit: 02cef30e43ad03582cfa42e52ab7f7b9edd582df (tag `prereg-nov2026-v1`) in the repository at ~/reviews/policy-conditional-markets-2026-10
- Frozen (local clock): 2026-10-19T12:55:00Z
- Independent timestamp: `SHA256SUMS.ots` (OpenTimestamps), committed with the freeze. Only a salted hash of `SHA256SUMS` was sent to the public calendars. After the Bitcoin attestation, `ots upgrade SHA256SUMS.ots` completes the proof and `ots verify SHA256SUMS.ots` reports the earliest time the sums existed. It proves the registration existed by then, not that it was the only one.
- Public: not yet. Publishing (OSF or a public repository) is Max's decision; the repository has no remote.

Verify the files: `shasum -a 256 -c SHA256SUMS` from this folder. `scripts/run_analysis.py` checks every file in the sums outside `data/raw/capture/` and `results/` on every run, records the result, and lists files the sums do not cover. Files added after the freeze (captures, results, `DEVIATIONS.md`) are not in the sums.
