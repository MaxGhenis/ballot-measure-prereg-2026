# Ballot measures and municipal bond spreads: November 3, 2026 pre-registration

This repository publishes a pre-registered test of whether the passage odds of state and local ballot measures on November 3, 2026 move state municipal bond fund spreads, in proportion to each measure's official fiscal estimate. [`REGISTRATION.md`](REGISTRATION.md) is the design: hypotheses, measures and markets, funds, event windows, estimators, power, and what counts as confirming or refuting an effect. [`RUNBOOK.md`](RUNBOOK.md) gives the commands. The registration was frozen on October 19, 2026, before the election.

The background is in [Testing California's bond funds against the billionaire tax odds](https://maxghenis.com/blog/california-bond-funds-billionaire-tax-odds/).

## Verify the freeze

- `shasum -a 256 -c --ignore-missing SHA256SUMS` checks every published file against the checksums written at the freeze.
- `SHA256SUMS.ots` is an [OpenTimestamps](https://opentimestamps.org) proof that `SHA256SUMS` existed by Bitcoin block 972148, mined at 13:06:53 UTC on October 19, 2026 (merkle root `96c9539a730fa93ee55c3a7f0e5350e54ac8830cb0badeed1713307718100687`). Check it with `ots verify SHA256SUMS.ots`, which needs a Bitcoin node, or at [opentimestamps.org](https://opentimestamps.org).
- [`FREEZE.md`](FREEZE.md) records the freeze. Its commit hash refers to the private working repository where the study was built; this repository starts at publication, so the checksums and the timestamp, not a commit hash, tie these files to the freeze.

## What is withheld

`SHA256SUMS` lists 1,299 files. This repository publishes 116 of them. The other 1,183 are third-party data without a redistribution license, and their checksums stay in `SHA256SUMS` so that any copy can be checked against them:

| Path | Files | What it holds |
|---|---|---|
| `data/raw/` | 1,111 | Raw responses from Yahoo Finance's chart service and from the Kalshi and Polymarket APIs, including the freeze capture |
| `evidence/funds/` | 47 | Fund sponsors' fact sheets and web pages |
| `evidence/history/` | 24 | Five years of daily fund prices from Yahoo Finance |
| `results/spread_panel.json` | 1 | Daily spread changes computed from those prices |

`scripts/capture.py` downloads the same data again from the public endpoints. `REGISTRATION.md` section 1 refers to `../memo.md`, an unpublished research memo; the post above summarizes its results.
