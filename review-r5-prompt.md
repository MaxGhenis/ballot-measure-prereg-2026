# Delta check, round 5: pre-registration of the November 3, 2026 ballot-measure study (prereg-nov2026/)

You are an independent reviewer. The sandbox is read-only and may have no shell; put everything in your final message. Do not contact anyone, post, or submit anything.

**Scope: only the post-approval diff.** Round 4 (`review-r4.md`) approved commit db434fa and listed three minor findings. The fixes are commits b9f1ea4 and 505b184: `git diff db434fa 505b184 -- prereg-nov2026/`. The response is `response-r4.md`. Check only that diff; do not re-review settled findings.

1. **Seal.** Read `files_match`, `ots_matches`, `committed` and `sealed` in `scripts/run_analysis.py`, and `scripts/seal_capture.sh`. Could a correctly taken and sealed capture on election night fail these checks for a reason unrelated to tampering? Consider: how `capture.py` builds the manifest's `files` map (every `save()`), files the operating system adds (`.DS_Store` is excluded by the leading-dot rule), the receipt layout (`OTS_HEAD` = magic, version byte 0x01, sha256 tag 0x08, then the 32-byte digest, confirmed on a live stamp), git commands run with `-C` inside a subfolder of the repository, and a stamp that fails and is retried. Conversely, could an edited, deleted, added or renamed file, or a rewritten manifest, still pass?
2. **W2 calendar.** `W2_DAYS` (NYSE weekdays November 9 to December 11, 2026, without Thanksgiving, November 26) and `BASE`. Is any 2026 NYSE closure in that range missing, and is using the fixed baseline close for the first change consistent with how `y` is computed in `spreads_daily`/`panel.leg`?
3. **Tests.** Do the changed tests check what they claim (`test_unsealed_captures_do_not_count`, `test_w2_day_missing_everywhere_is_unestimable`, `test_w2_calendar_is_fixed_in_advance`, the strengthened first-capture and venue tests)? Any test that writes through a hard link created by `place()`?
4. **Text.** REGISTRATION §5.4 and RUNBOOK step 2 against the code.

**Output.** APPROVE (ready to freeze), MINOR FIXES or MAJOR FIXES, then numbered findings with severity, evidence and a concrete fix. Approve unless a finding would change a registered reading or block a valid capture.
