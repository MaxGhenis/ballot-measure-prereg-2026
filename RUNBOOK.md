# Runbook: November 3, 2026 ballot-measure study

All paths are relative to `~/reviews/policy-conditional-markets-2026-10/prereg-nov2026/`, which sits inside the git repository `~/reviews/policy-conditional-markets-2026-10/`. The registered design is in `REGISTRATION.md` and is frozen at the commit and tag named in `FREEZE.md`. Never edit `REGISTRATION.md`, `registry/` or `scripts/` after the freeze. Record any departure in `DEVIATIONS.md` with the date and the reason.

Prefix Python with `SSL_CERT_FILE=/etc/ssl/cert.pem`. Run the tests with `uv run --no-project --python 3.12 --with pytest --with hypothesis --with numpy --with pandas python -m pytest -q tests/`.

**Network.** On October 16, 2026 this machine's network blocked kalshi.com, Kalshi's API and Polymarket's CLOB with a "NetAlerts Services" certificate. Test before each step:

```bash
curl -s -o /dev/null -w "%{http_code}\n" --max-time 15 "https://api.elections.kalshi.com/trade-api/v2/series?limit=1"
```

If the result is not 200, do not bypass the filter (no DNS or proxy workarounds, no disabled certificate checks). Run the step anyway: the capture records every failed request in its `manifest.json`, and the analysis lists what it could not use. Histories stay available after settlement, so rerun the capture once the network is unblocked (and seal it); the registered rule takes market data from the first capture that has them for every priced measure, up to the November 13 capture (December 14 for W2). Fund prices from Yahoo are not blocked.

## Steps

0. **Freeze (before October 30).**
   1. `python3 scripts/enumerate_markets.py`. If Kalshi is reachable, replace every `pending-series:` entry in `registry/measures.csv` with the series' markets from `data/raw/kalshi_measure_markets.json` that name the measure, then run `python3 scripts/build_markets.py`. If Kalshi is not reachable, leave the pending rows as they are (they have no freeze price and stay out of every test) and keep `enumeration_meta.json`'s `complete: false`.
   2. `python3 scripts/freeze_prices.py`, then `python3 scripts/capture.py all`.
   3. `python3 scripts/panel.py data/raw/capture/<that stamp>`, `python3 scripts/power.py`, `python3 scripts/summarize_registry.py`.
   4. Change "draft, not yet frozen" to "frozen" in `REGISTRATION.md`'s header. (`freeze.sh` rewrites section 7's power paragraph from `results/power.json`.)
   5. `bash scripts/freeze.sh`. It runs the tests, writes `SHA256SUMS`, commits, tags `prereg-nov2026-v1`, timestamps `SHA256SUMS` with OpenTimestamps and writes `FREEZE.md`.
1. **Pre-election snapshot (November 3, before 4 p.m. Eastern).** `python3 scripts/capture.py all`. Then `uvx --from opentimestamps-client ots upgrade SHA256SUMS.ots` and commit the upgraded proof if it changed. Do not rerun `freeze_prices.py`: the registered probabilities are the frozen ones.
2. **Captures (after 9 p.m. Eastern on November 4, 6, 9 and 13 and December 11 and 14).** `python3 scripts/capture.py all`, then at once `bash scripts/seal_capture.sh` (timestamps the new capture's `manifest.json` with OpenTimestamps and commits the folder). If it reports that the timestamp failed, the capture is committed but does not count yet: rerun `bash scripts/seal_capture.sh data/raw/capture/<stamp>` until it succeeds. Each run writes one `data/raw/capture/<stamp>/` folder with every asset and market file and a `manifest.json`. Fund net asset values post on Yahoo after about 6:30 p.m. Eastern, so earlier captures can lack the day's bars. Never rerun `capture.py --dir` into an existing capture and never delete one: the registered rule skips a merged capture, and the commits record every capture taken. An extra capture (after a network block, say) is fine; the rule decides which one counts.
3. **Analysis (November 6, after that day's capture).**
   - `python3 scripts/run_analysis.py --window W1`, then `--window W0` and `--window W3`. With no capture named, the script uses the registered captures (REGISTRATION §5.4): fund bars from one, market data from the first capture at or after it that has them for every priced measure. It lists missing bars and market data first. If it reports that no capture yet satisfies the rule, capture again (after 9 p.m. on November 9 for bars; any time up to the November 13 capture for market data) and rerun. Never name another capture unless you record the reason in `DEVIATIONS.md`.
   - Run the tests.
   - Write `results/RESULT.md`: the capture used and the integrity check, the registered reading (CONFIRM, REFUTE, INCONCLUSIVE, WRONG SIGN or UNESTIMABLE) with the placebo-set gate, any dropped states, the pooled β with its placebo SE and interval, the per-measure estimates, the placebo set, H4, the secondary specifications, the federal-election check, and every omitted measure, fallback and capture failure. Write it whatever the sign.
   - Commit everything with the message "Nov 3 study: registered analysis, window W1".
4. **Late count (December 11 and December 14, after 9 p.m. Eastern).** Capture and seal on both days, then, after the December 14 capture, `python3 scripts/run_analysis.py --window W2`. Commit and update `results/RESULT.md`.
5. **Hand-off after each analysis.** Send `results/RESULT.md` to Max with SendUserFile. Queue one decision with `cos add-decision` on whether to publish the result. Nothing goes outside the machine without his go.
