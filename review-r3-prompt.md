# Adversarial review, round 3: pre-registration of the November 3, 2026 ballot-measure study (prereg-nov2026/)

You are an independent reviewer. The sandbox is read-only and may have no shell; put everything in your final message. Do not contact anyone, post, or submit anything. Review the current commit of the repository (`git log -1`).

Round 2 (`review-r2.md`) returned MAJOR FIXES with two major findings (M1: the Amendment 87 × Proposition 136 bounds; M2: which capture feeds the registered reading) and eleven minor ones. The response is `response-r2.md`; `git show HEAD` holds the changes. Round 1 and its response are `review-r1.md` and `response-r1.md`.

1. **Round-diff.** Check each round-2 finding against the files. For M1, re-derive the three outcomes and the midpoint from the saved fiscal statement (`evidence/co/fis_A87_pp17-21.txt`) and judge the rule's wording in REGISTRATION §3.2. For M2, read `registered_capture`, `missing_bars` and the dropping logic in `scripts/run_analysis.py` against REGISTRATION §5.4 and RUNBOOK, and look for a way the reading could still depend on a choice made after the election.
2. **Fresh pass** over everything a registration needs before it is frozen: code paths that would fail silently on election night, tests that test the wrong thing, text that contradicts the code, anything that could be gamed after the freeze. Keep it proportionate: this is round 3.

**Output.** APPROVE (ready to freeze), MINOR FIXES or MAJOR FIXES; a round-diff table; numbered new findings with severity, text or code, evidence and a concrete fix. Approve if no blocker or major finding remains; minor findings and nits alone are compatible with APPROVE if you list them.
