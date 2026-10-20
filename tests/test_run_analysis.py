"""End-to-end tests of scripts/run_analysis.py on SYNTHETIC captures (no real market or price data), plus settlement on two
real saved market records (tests/fixtures/).

The synthetic capture writes Yahoo daily bars for every registered rank-1 asset, 5-minute bars for the ETF tickers, and a
price history for EVERY registered market of every priced measure (so fallbacks can be exercised). Each measure's markets
jump to its drawn outcome at 11 p.m. Eastern on November 3, except "slow" measures, which stay at their freeze price until
November 20 (a late count). A planted beta (bp per $ billion a year) multiplies the registered revenue exposure on
November 4 (and on November 20 for slow measures)."""
import csv, datetime as dt, hashlib, json, os, pathlib, shutil, subprocess, sys
import numpy as np, pandas as pd, pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_analysis as RA
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
reg = lambda f: list(csv.DictReader(open(ROOT / "registry" / f)))
FIX = ROOT / "tests" / "fixtures"


def fake_capture(tmp, beta, outcome_seed=1, noise_seed=2, slow=(), intraday=False, name="capture"):
    cap = tmp / name; cap.mkdir(parents=True)
    meas = {r["measure_id"]: r for r in reg("measures.csv")}; mk = {r["market"]: r for r in reg("markets.csv")}
    prim = reg("prices_at_freeze.csv"); assets = [a for a in reg("assets.csv") if a["rank"] == "1"]
    rng = np.random.default_rng(outcome_seed)
    jump = dt.datetime(2026, 11, 3, 23, 0, tzinfo=ET).astimezone(dt.timezone.utc)
    late = dt.datetime(2026, 11, 20, 12, 0, tzinfo=ET).astimezone(dt.timezone.utc)
    hours = pd.date_range(dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc), dt.datetime(2026, 12, 15, tzinfo=dt.timezone.utc), freq="1h")
    X4 = {a["state"]: 0.0 for a in assets}; X20 = dict(X4); outcomes = {}
    for pr in prim:
        p0 = float(pr["p"]); out = float(rng.random() < p0); mid = pr["measure_id"]; outcomes[mid] = out
        when = late if mid in slow else jump
        path = [(h, (out if h >= when else p0)) for h in hours]
        for key in [k for k in meas[mid]["markets"].split(";") if k and not k.startswith("pending")]:
            venue, m = key.split(":", 1)
            if venue == "kalshi":
                (cap / f"kalshi_{m}_market.json").write_text(json.dumps({"retrieved": "SYNTHETIC", "data": {"market": {"status": "active"}}}))
                c = [{"end_period_ts": int(h.timestamp()), "yes_bid": {"close_dollars": str(max(0, v - 0.01))}, "yes_ask": {"close_dollars": str(min(1, v + 0.01))},
                      "price": {"close_dollars": str(v)}} for h, v in path]
                (cap / f"kalshi_{m}_60m.json").write_text(json.dumps({"retrieved": "SYNTHETIC", "data": c}))
            elif m in mk:
                (cap / f"pm_market_{m}.json").write_text(json.dumps({"retrieved": "SYNTHETIC", "data": {"closed": False}}))
                tok = json.loads(mk[m]["clob_token_ids"])[0]
                (cap / f"pm_{tok}_60m.json").write_text(json.dumps({"retrieved": "SYNTHETIC", "data": {"history": [{"t": int(h.timestamp()), "p": v} for h, v in path]}}))
        mm = meas[mid]
        if mm["category"] == "R" and mm["state"] in X4:
            (X20 if mid in slow else X4)[mm["state"]] += (out - p0) * float(mm["F_annual_bn"])
    days = pd.bdate_range("2025-09-01", "2026-12-14")
    days = days[~days.isin(pd.to_datetime(["2025-11-27", "2026-11-26"]))]      # NYSE closed on Thanksgiving
    nrng = np.random.default_rng(noise_seed)
    rb = nrng.normal(0, 0.3, len(days)); tick = {}
    for a in assets:
        ysp = nrng.normal(0, 1.0, len(days))
        ysp[days.get_loc(pd.Timestamp("2026-11-04"))] += beta * X4[a["state"]]
        ysp[days.get_loc(pd.Timestamp("2026-11-20"))] += beta * X20[a["state"]]
        tick[a["tickers"]] = float(a["duration_state"]) * (rb / float(a["duration_bench"]) - ysp / 100); tick[a["benchmark"]] = rb
    for t, r in tick.items():
        px = 100 * np.exp(np.cumsum(r / 100))
        ts = [int(pd.Timestamp(d).tz_localize("America/New_York").replace(hour=16).timestamp()) for d in days]
        (cap / f"yahoo_{t}_1d.json").write_text(json.dumps({"retrieved": "SYNTHETIC", "data": {"chart": {"result": [{"timestamp": ts, "indicators": {"adjclose": [{"adjclose": px.tolist()}], "quote": [{"close": px.tolist()}]}}]}}}))
    if intraday:   # 5-minute bars for the ETF legs, September 1 to November 4; a planted move between Nov 3 close and Nov 4 10:30
        etf = [a for a in assets if a["instrument_type"].startswith("ETF")]
        bars = [b for d in pd.bdate_range("2026-09-01", "2026-11-04") for b in pd.date_range(pd.Timestamp(d).tz_localize("America/New_York").replace(hour=9, minute=30), periods=78, freq="5min")]
        r5b = nrng.normal(0, 0.02, len(bars)); shock_i = next(i for i, b in enumerate(bars) if b >= pd.Timestamp("2026-11-04 09:30", tz="America/New_York"))
        for a in etf:
            r5s = nrng.normal(0, 0.02, len(bars)); r5s[shock_i] += -float(a["duration_state"]) * beta * X4[a["state"]] / 100
            for t, r in ((a["tickers"], r5s + r5b * float(a["duration_state"]) / float(a["duration_bench"])), (a["benchmark"], r5b)):
                px = 100 * np.exp(np.cumsum(r / 100)); ts = [int(b.timestamp()) for b in bars]
                (cap / f"yahoo_{t}_5m.json").write_text(json.dumps({"retrieved": "SYNTHETIC", "data": {"chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{"close": px.tolist()}]}}]}}}))
    (cap / "manifest.json").write_text(json.dumps({"stamp": "SYNTHETIC", "files": {}, "failures": []}))
    return cap, X4, X20


GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]


def receipt(f):
    """A stand-in OpenTimestamps receipt for f: the real header and f's digest (no calendar is contacted)."""
    (f.parent / (f.name + ".ots")).write_bytes(RA.OTS_HEAD + hashlib.sha256(f.read_bytes()).digest() + b"\xf0\x10pending")


def place(src, root, stamp, commands=1, started_lag=5, failures=(), stamp_ots=True, commit=True, drop=()):
    """Copy a synthetic capture into root/data/raw/capture/<stamp> without the files in `drop`, write a manifest as
    capture.py does (every file with its sha256), then seal it as scripts/seal_capture.sh does (receipt, commit) unless
    told not to."""
    d = root / "data/raw/capture" / stamp; shutil.copytree(src, d, copy_function=os.link)   # hard links: tests only unlink
    (d / "manifest.json").unlink()                                                             # never write through a link
    for f in drop: (d / f).unlink()
    t0 = dt.datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc) + dt.timedelta(seconds=started_lag)
    files = {q.name: {"sha256": hashlib.sha256(q.read_bytes()).hexdigest()} for q in d.iterdir() if q.is_file()}
    (d / "manifest.json").write_text(json.dumps({"stamp": stamp, "started": t0.isoformat(), "files": files, "failures": list(failures),
                                                 "commands": ["scripts/capture.py all"] * commands}))
    if stamp_ots: receipt(d / "manifest.json")
    if commit:
        subprocess.run(GIT + ["-C", str(root), "add", "--", str(d)], check=True, capture_output=True)
        subprocess.run(GIT + ["-C", str(root), "commit", "-q", "-m", stamp], check=True, capture_output=True)
    return d


def fake_root(tmp):
    """A study folder (its own git repository) whose registry and evidence are the real ones and whose captures are
    synthetic."""
    root = tmp / "root"; (root / "data/raw/capture").mkdir(parents=True)
    for d in ("registry", "evidence"): (root / d).symlink_to(ROOT / d)
    subprocess.run(GIT + ["init", "-q", str(root)], check=True, capture_output=True)
    return root


def drop_bar(f, day):
    d = json.load(open(f)); res = d["data"]["chart"]["result"][0]
    drop = int(pd.Timestamp(day).tz_localize("America/New_York").replace(hour=16).timestamp())
    keep = [i for i, t in enumerate(res["timestamp"]) if t != drop]
    res["timestamp"] = [res["timestamp"][i] for i in keep]
    res["indicators"]["adjclose"][0]["adjclose"] = [res["indicators"]["adjclose"][0]["adjclose"][i] for i in keep]
    res["indicators"]["quote"][0]["close"] = [res["indicators"]["quote"][0]["close"][i] for i in keep]
    f.write_text(json.dumps(d))


def market_files(key, mk):
    """(history file, market-record file, manifest failure key for the history) of a registered market."""
    v, x = key.split(":", 1)
    if v == "kalshi": return f"kalshi_{x}_60m.json", f"kalshi_{x}_market.json", f"kalshi candles {x} 60m"
    tok = json.loads(mk[x]["clob_token_ids"])[0]
    return f"pm_{tok}_60m.json", f"pm_market_{x}.json", f"polymarket history {tok} 60m"


def single_market_measure(venue=None):
    """A priced measure with exactly one registered market, and that market's capture files and the manifest's failure key
    for its history."""
    meas = {r["measure_id"]: r for r in reg("measures.csv")}; mk = {r["market"]: r for r in reg("markets.csv")}
    for m in [r["measure_id"] for r in reg("prices_at_freeze.csv")]:
        keys = [k for k in meas[m]["markets"].split(";") if k and not k.startswith("pending")]
        if len(keys) == 1 and keys[0].split(":", 1)[1] in mk:
            h, rec, what = market_files(keys[0], mk)
            return m, [h, rec], what


def measure_on(venue):
    """A priced measure with a registered market on the venue: (measure, [that market's history, record], failure key,
    [every file of its other markets])."""
    meas = {r["measure_id"]: r for r in reg("measures.csv")}; mk = {r["market"]: r for r in reg("markets.csv")}
    for m in [r["measure_id"] for r in reg("prices_at_freeze.csv")]:
        keys = [k for k in meas[m]["markets"].split(";") if k and not k.startswith("pending") and k.split(":", 1)[1] in mk]
        on = [k for k in keys if k.startswith(venue + ":")]
        if on:
            h, rec, what = market_files(on[0], mk)
            return m, [h, rec], what, [f for k in keys if k != on[0] for f in market_files(k, mk)[:2]]


def test_recovers_planted_effect_and_confirms(tmp_path):
    cap, X4, _ = fake_capture(tmp_path, beta=-5.0)
    r = RA.run(cap, "W1", out=tmp_path / "out")
    assert any(abs(v) > 0 for v in X4.values())
    p = r["primary"]
    assert p["status"] == "OK" and abs(p["beta"] - (-5.0)) < 3 * p["se_placebo"] + 0.5
    assert p["p_placebo"] < 0.05 and r["reading"] == "CONFIRM"
    assert isinstance(r["placebo_set_N"], dict) and r["placebo_set_N"]["status"] == "OK" and r["h3_gate"] == "passed"   # H3 wired into run()
    assert r["deviation"]   # a synthetic capture is never the registered one


def test_null_is_not_rejected(tmp_path):
    cap, _, _ = fake_capture(tmp_path, beta=0.0)
    r = RA.run(cap, "W1", out=tmp_path / "out")
    assert r["primary"]["status"] == "OK" and r["primary"]["p_placebo"] >= 0.05
    assert r["reading"] in ("INCONCLUSIVE", "REFUTE")


def test_w2_late_count_with_a_slow_measure(tmp_path):
    slow = ["CA-P3"]
    cap, _, X20 = fake_capture(tmp_path, beta=-5.0, slow=slow)
    r = RA.run(cap, "W2", out=tmp_path / "out")
    assert r["days"][0] == "2026-11-09" and r["days"][-1] == "2026-12-11"
    assert set(r["w2_eligible"]) >= set(slow)
    assert r["primary"]["status"] == "OK" and r["primary"]["beta"] < 0


def test_w3_intraday(tmp_path):
    cap, _, _ = fake_capture(tmp_path, beta=-5.0, intraday=True)
    r = RA.run(cap, "W3", out=tmp_path / "out")
    assert r["n_placebo_columns"] >= RA.W3_MIN_BLOCKS
    assert r["primary"]["status"] == "OK"


def test_w3_without_intraday_bars_is_unestimable(tmp_path):
    cap, _, _ = fake_capture(tmp_path, beta=0.0)
    r = RA.run(cap, "W3", out=tmp_path / "out")
    assert r["primary"]["status"] == "UNESTIMABLE" and r["reading"] == "UNESTIMABLE" and r["primary"]["reason"]


def test_fallback_is_used_and_omission_listed(tmp_path):
    cap, _, _ = fake_capture(tmp_path, beta=0.0)
    meas = {r["measure_id"]: r for r in reg("measures.csv")}; prim = {r["measure_id"]: r for r in reg("prices_at_freeze.csv")}
    mk = {r["market"]: r for r in reg("markets.csv")}
    keys = lambda m: [k for k in meas[m]["markets"].split(";") if k and not k.startswith("pending")]
    def files(key):
        v, m = key.split(":", 1)
        return [cap / f"kalshi_{m}_60m.json"] if v == "kalshi" else [cap / f"pm_{json.loads(mk[m]['clob_token_ids'])[0]}_60m.json"]
    multi = [m for m in prim if len(keys(m)) > 1 and all(k.split(":", 1)[1] in mk for k in keys(m))]
    single = [m for m in prim if len(keys(m)) == 1]
    assert multi and single
    for f in files(prim[multi[0]]["primary_market"]): f.unlink()
    for k in keys(single[0]):
        for f in files(k): f.unlink()
    r = RA.run(cap, "W1", out=tmp_path / "out")
    assert multi[0] in r["fallbacks"] and r["fallbacks"][multi[0]] != prim[multi[0]]["primary_market"]
    assert single[0] in r["omitted_measures"] and single[0] not in r["probabilities"]


@pytest.mark.parametrize("day", ["2026-11-03", "2026-11-05"])
def test_dropped_state_when_a_bar_is_missing(tmp_path, day):
    """A state missing any registered bar (Nov 3 included: panel.leg would otherwise difference Nov 2 to Nov 4) is dropped
    because the preflight lists it."""
    cap, _, _ = fake_capture(tmp_path, beta=0.0)
    a = [a for a in reg("assets.csv") if a["rank"] == "1" and a["state"] == "CO"][0]
    drop_bar(cap / f"yahoo_{a['tickers']}_1d.json", day)
    r = RA.run(cap, "W1", out=tmp_path / "out")
    assert r["preflight_missing_bars"]["CO"] == [day]
    assert set(r["dropped_states"]) == {"CO"} and day in r["dropped_states"]["CO"] and "CO" not in r["states"]
    assert r["primary"]["status"] == "OK"


def test_dropped_state_when_a_price_file_is_missing(tmp_path):
    cap, _, _ = fake_capture(tmp_path, beta=0.0)
    a = [a for a in reg("assets.csv") if a["rank"] == "1" and a["state"] == "CO"][0]
    (cap / f"yahoo_{a['tickers']}_1d.json").unlink()
    r = RA.run(cap, "W1", out=tmp_path / "out")
    assert set(r["dropped_states"]) == {"CO"} and "CO" not in r["states"] and r["primary"]["status"] == "OK"


@pytest.mark.parametrize("day", ["2026-11-03", "2026-11-05"])
def test_event_day_missing_everywhere_is_unestimable(tmp_path, day):
    cap, _, _ = fake_capture(tmp_path, beta=-5.0)
    for f in cap.glob("yahoo_*_1d.json"): drop_bar(f, day)
    r = RA.run(cap, "W1", out=tmp_path / "out")
    assert r["reading"] == "UNESTIMABLE" and r["primary"]["status"] == "UNESTIMABLE" and day in r["missing_event_days"]


def test_registered_capture_rule(tmp_path, monkeypatch):
    """The first sealed capture after the earliest stamp with every bar is chosen; before the deadline an incomplete one is
    skipped, and so is any capture that is unsealed (merged by a second command, renamed, or started long after its stamp)."""
    root = fake_root(tmp_path); c, _, _ = fake_capture(tmp_path, beta=0.0, name="c")
    place(c, root, "20261106T230000Z")                                    # before the earliest stamp
    incomplete = place(c, root, "20261107T023000Z", drop=["yahoo_MUB_1d.json"])
    merged = place(c, root, "20261107T120000Z", commands=2)               # capture.py --dir into an existing capture
    late = place(c, root, "20261107T130000Z", started_lag=86400)          # a directory named for a time it was not taken
    renamed = place(c, root, "20261107T140000Z"); m = json.load(open(renamed / "manifest.json")); m["stamp"] = "20261107T020000Z"
    (renamed / "manifest.json").write_text(json.dumps(m))
    good = place(c, root, "20261108T023000Z")
    monkeypatch.setattr(RA, "ROOT", root); RA.SKIPPED.clear()
    assets = [a for a in reg("assets.csv") if a["rank"] == "1"]
    cap, miss = RA.registered_capture("W1", assets)
    assert cap == good and miss == {}
    assert {pathlib.Path(k).name for k in RA.SKIPPED} == {merged.name, late.name, renamed.name}


def test_unsealed_captures_do_not_count(tmp_path, monkeypatch):
    """A capture counts only when committed with no later change and carrying a receipt for its manifest's bytes."""
    root = fake_root(tmp_path); c, _, _ = fake_capture(tmp_path, beta=0.0, name="c")
    no_receipt = place(c, root, "20261107T023000Z", stamp_ots=False)
    uncommitted = place(c, root, "20261107T033000Z", commit=False)
    stale = place(c, root, "20261107T043000Z"); m = json.load(open(stale / "manifest.json")); m["failures"] = [{"what": "x", "error": "y"}]
    (stale / "manifest.json").unlink(); (stale / "manifest.json").write_text(json.dumps(m))   # manifest rewritten after stamping
    subprocess.run(GIT + ["-C", str(root), "commit", "-qam", "rewrite"], check=True, capture_output=True)
    edited = place(c, root, "20261107T053000Z")
    (edited / "yahoo_MUB_1d.json").unlink(); (edited / "yahoo_MUB_1d.json").write_text("{}")   # a data file changed after sealing
    deleted = place(c, root, "20261107T063000Z"); (deleted / "yahoo_MUB_1d.json").unlink()   # ... or deleted, and committed
    subprocess.run(GIT + ["-C", str(root), "commit", "-qam", "delete"], check=True, capture_output=True)
    late_commit = place(c, root, "20261107T073000Z", commit=False)
    (late_commit / "x.json").write_text("{}")                                                  # an uncommitted extra file
    good = place(c, root, "20261108T023000Z")
    monkeypatch.setattr(RA, "ROOT", root); RA.SKIPPED.clear()
    cap, miss = RA.registered_capture("W1", [a for a in reg("assets.csv") if a["rank"] == "1"])
    assert cap == good and miss == {}
    why = {pathlib.Path(k).name: v for k, v in RA.SKIPPED.items()}
    assert set(why) == {no_receipt.name, uncommitted.name, stale.name, edited.name, deleted.name, late_commit.name}
    assert why[deleted.name] == "1 files differ from the manifest's list" and why[late_commit.name] == "1 files differ from the manifest's list"
    assert "receipt" in why[no_receipt.name] and why[uncommitted.name] == "not committed"
    assert "receipt" in why[stale.name] and why[edited.name] == "yahoo_MUB_1d.json differs from its manifest hash"


def test_w2_day_missing_everywhere_is_unestimable(tmp_path):
    cap, _, _ = fake_capture(tmp_path, beta=-5.0, slow=["CA-P3"])
    for f in cap.glob("yahoo_*_1d.json"): drop_bar(f, "2026-11-12")
    r = RA.run(cap, "W2", out=tmp_path / "out")
    assert r["reading"] == "UNESTIMABLE" and "2026-11-12" in r["missing_event_days"]


def test_w2_calendar_is_fixed_in_advance():
    assert RA.W2_DAYS[0] == "2026-11-09" and RA.W2_DAYS[-1] == "2026-12-11" and "2026-11-26" not in RA.W2_DAYS
    assert "2026-11-11" in RA.W2_DAYS and "2026-11-27" in RA.W2_DAYS and len(RA.W2_DAYS) == 24
    assert RA.window_bar_days(None, "W2") == ["2026-11-06"] + RA.W2_DAYS


def test_registered_capture_deadline_branch(tmp_path, monkeypatch):
    """No complete capture by the deadline: the deadline capture is used and its missing bars listed."""
    root = fake_root(tmp_path); c, _, _ = fake_capture(tmp_path, beta=0.0, name="c")
    a = [a for a in reg("assets.csv") if a["rank"] == "1" and a["state"] == "CO"][0]
    drop_bar(c / f"yahoo_{a['tickers']}_1d.json", "2026-11-03")
    place(c, root, "20261107T023000Z"); dl = place(c, root, "20261110T023000Z"); place(c, root, "20261111T023000Z")
    monkeypatch.setattr(RA, "ROOT", root)
    cap, miss = RA.registered_capture("W1", [a for a in reg("assets.csv") if a["rank"] == "1"])
    assert cap == dl and miss == {"CO": ["2026-11-03"]}
    r = RA.run(None, "W1", out=tmp_path / "out")
    assert r["capture"] == str(dl) and r["deviation"] is None and set(r["dropped_states"]) == {"CO"}


def test_market_data_come_from_the_first_capture_that_has_them(tmp_path, monkeypatch):
    """N1: a capture with every bar but a blocked venue supplies the bars; the probabilities come from the first later
    capture with a market record and a history for every priced measure."""
    root = fake_root(tmp_path); c, _, _ = fake_capture(tmp_path, beta=-5.0, name="c")
    mid, files, _ = single_market_measure()
    bars = place(c, root, "20261107T023000Z", drop=files)                   # one venue blocked during the bar capture
    still = place(c, root, "20261108T023000Z", drop=files)
    good = place(c, root, "20261109T023000Z", drop=["yahoo_MUB_1d.json"])  # bars in the market capture do not matter
    c2, _, _ = fake_capture(tmp_path, beta=0.0, outcome_seed=7, name="c2")
    later = place(c2, root, "20261110T023000Z")                             # also complete, with other outcomes
    monkeypatch.setattr(RA, "ROOT", root)
    r = RA.run(None, "W1", out=tmp_path / "out")
    assert r["capture"] == str(bars) and r["market_capture"] == str(good) and r["deviation"] is None
    assert r["measures_missing_market_data"] == [] and mid in r["probabilities"] and mid not in r["omitted_measures"]
    meas = {x["measure_id"]: x for x in reg("measures.csv")}; mk = {x["market"]: x for x in reg("markets.csv")}
    prim = {x["measure_id"]: x for x in reg("prices_at_freeze.csv")}
    times = [RA._4pm(d) for d in ["2026-11-03"] + RA.FIXED["W1"]]
    pg, pl = RA.measure_probs(good, meas, mk, prim, times)[0], RA.measure_probs(later, meas, mk, prim, times)[0]
    assert pg != pl and r["probabilities"] == pg                            # the first qualifying capture, not a later one
    assert r["capture_manifest_sha256"] and r["market_capture_manifest_sha256"] and r["primary"]["status"] == "OK"
    assert r["primary"]["p_placebo"] < 0.05


@pytest.mark.parametrize("venue", ["kalshi", "polymarket"])
def test_venue_answer_of_no_history_counts_as_captured(tmp_path, venue):
    c, _, _ = fake_capture(tmp_path, beta=0.0, name="c")
    mid, files, what, others = measure_on(venue)
    for f in others: (c / f).unlink()                                     # only this venue's market can supply the measure
    meas = {r["measure_id"]: r for r in reg("measures.csv")}; mk = {r["market"]: r for r in reg("markets.csv")}
    prim = {r["measure_id"]: r for r in reg("prices_at_freeze.csv")}
    (c / files[0]).unlink()
    assert RA.missing_markets(c, meas, mk, prim) == [mid]                  # no history and no answer: missing
    m = json.load(open(c / "manifest.json"))
    m["failures"] = [{"what": what, "error": "connection reset"}]; (c / "manifest.json").write_text(json.dumps(m))
    assert RA.missing_markets(c, meas, mk, prim) == [mid]                  # a failed request is not an answer
    m["failures"] = [{"what": what, "error": "endpoint returned no candles" if what.startswith("kalshi") else "empty history"}]
    (c / "manifest.json").write_text(json.dumps(m))
    assert RA.missing_markets(c, meas, mk, prim) == []
    (c / files[1]).unlink()
    assert RA.missing_markets(c, meas, mk, prim) == [mid]                  # the market record is still required


def test_market_deadline_lets_omissions_stand(tmp_path, monkeypatch):
    root = fake_root(tmp_path); c, _, _ = fake_capture(tmp_path, beta=0.0, name="c")
    mid, files, _ = single_market_measure()
    for f in files: (c / f).unlink()
    place(c, root, "20261107T023000Z"); dl = place(c, root, "20261114T023000Z")
    monkeypatch.setattr(RA, "ROOT", root)
    r = RA.run(None, "W1", out=tmp_path / "out")
    assert r["market_capture"] == str(dl) and r["measures_missing_market_data"] == [mid] and mid in r["omitted_measures"]
    assert r["deviation"] is None


def test_no_market_capture_yet(tmp_path, monkeypatch):
    root = fake_root(tmp_path); c, _, _ = fake_capture(tmp_path, beta=0.0, name="c")
    _, files, _ = single_market_measure()
    for f in files: (c / f).unlink()
    place(c, root, "20261107T023000Z")
    monkeypatch.setattr(RA, "ROOT", root)
    with pytest.raises(SystemExit, match="no capture yet has market data"):
        RA.run(None, "W1", out=tmp_path / "out")


def test_integrity_checks_every_frozen_file_and_lists_new_ones(tmp_path, monkeypatch):
    import hashlib
    root = tmp_path / "r"
    for f, s in (("registry/a.csv", "a"), ("scripts/b.py", "b"), ("evidence/c.json", "c"), ("data/raw/capture/x/m.json", "m")):
        (root / f).parent.mkdir(parents=True, exist_ok=True); (root / f).write_text(s)
    (root / "SHA256SUMS").write_text("".join(f"{hashlib.sha256((root / f).read_bytes()).hexdigest()}  ./{f}\n"
                                             for f in ("registry/a.csv", "scripts/b.py", "evidence/c.json", "data/raw/capture/x/m.json")))
    (root / "evidence/c.json").write_text("changed"); (root / "scripts/new.py").write_text("x")
    (root / "data/raw/capture/x/m.json").write_text("captures are not checked")
    monkeypatch.setattr(RA, "ROOT", root)
    r = RA.integrity()
    assert r["files_checked"] == 3 and r["mismatched"] == ["evidence/c.json"] and r["not_in_sums"] == ["scripts/new.py"]


def test_kalshi_settlement_on_a_real_early_closed_market(tmp_path):
    cap = tmp_path / "c"; cap.mkdir()
    shutil.copy(FIX / "kalshi_KXWAINCOMETAX-26APR01_market.json", cap / "kalshi_KXWAINCOMETAX-26APR01_market.json")
    t, v = RA.kalshi_settlement(cap, "KXWAINCOMETAX-26APR01")
    assert v == 1.0 and t == dt.datetime(2026, 3, 30, 18, 6, 17, 872834, tzinfo=dt.timezone.utc)   # settlement_ts, not the scheduled close


def test_kalshi_future_close_time_is_not_a_resolution(tmp_path):
    cap = tmp_path / "c"; cap.mkdir()
    m = {"status": "determined", "result": "yes", "close_time": "2027-11-02T15:00:00Z"}
    (cap / "kalshi_X_market.json").write_text(json.dumps({"retrieved": "2026-11-04T23:00:00+00:00", "data": {"market": m}}))
    assert RA.kalshi_settlement(cap, "X") is None
    m["close_time"] = "2026-11-04T05:00:00Z"
    (cap / "kalshi_X_market.json").write_text(json.dumps({"retrieved": "2026-11-04T23:00:00+00:00", "data": {"market": m}}))
    assert RA.kalshi_settlement(cap, "X")[1] == 1.0


def test_polymarket_settlement_uses_closed_time(tmp_path):
    """Real record: endDate (June 30 12:00 UTC) precedes resolution; only closedTime (July 1 08:08 UTC) counts."""
    cap = tmp_path / "c"; cap.mkdir()
    shutil.copy(FIX / "pm_market_537690.json", cap / "pm_market_537690.json")
    t, v = RA.pm_settlement(cap, "537690")
    assert v == 0.0 and t == dt.datetime(2025, 7, 1, 8, 8, 43, tzinfo=dt.timezone.utc)


def test_settlement_value_overrides_last_trade(tmp_path):
    cap = tmp_path / "c"; cap.mkdir()
    close = dt.datetime(2026, 11, 4, 3, 0, tzinfo=dt.timezone.utc)
    c = [{"end_period_ts": int((close - dt.timedelta(hours=h)).timestamp()), "price": {"close_dollars": "0.97"}} for h in (30, 24, 12, 5, 1)]
    (cap / "kalshi_TEST_60m.json").write_text(json.dumps({"data": sorted(c, key=lambda x: x["end_period_ts"])}))
    (cap / "kalshi_TEST_market.json").write_text(json.dumps({"retrieved": "2026-11-05T00:00:00+00:00", "data": {"market": {"status": "finalized", "result": "yes", "settlement_value_dollars": "1.0000", "settlement_ts": "2026-11-04T03:00:00Z"}}}))
    v, _ = RA.market_probs(cap, "kalshi:TEST", {}, [RA._4pm("2026-11-03"), RA._4pm("2026-11-04")])
    assert v == [0.97, 1.0]


def test_interaction_with_a_non_revenue_member():
    """A87 x 136 pattern: 136 is RU (F = 0 alone). E = p87 F87 + p87 p136 (F_joint - F87). Moving both from 0.5 to 1 with
    F87 = 2 and F_joint = 0.7 changes E by (1 - 0.5) x 2 + (1 - 0.25) x (0.7 - 2)."""
    meas = {"A": {"category": "R", "state": "CO", "F_annual_bn": "2"}, "B": {"category": "RU", "state": "CO", "F_annual_bn": ""}}
    probs = {"A": [0.5, 1.0], "B": [0.5, 1.0]}
    inter = [{"state": "CO", "measure_i": "A", "measure_j": "B", "F_joint_bn": "0.7"}]
    fR = lambda m: RA.num(m.get("F_annual_bn"))
    X = RA.exposure(["CO"], probs, meas, {"R"}, fR, inter)
    assert X[0, 0] == pytest.approx(0.5 * 2 + 0.75 * (0.7 - 2))
    assert RA.exposure(["CO"], probs, meas, {"R"}, fR)[0, 0] == pytest.approx(1.0)


def test_interaction_term_changes_exposure():
    meas = {"A": {"category": "R", "state": "CO"}, "B": {"category": "R", "state": "CO"}}
    probs = {"A": [0.5, 1.0], "B": [0.5, 1.0]}; F = {"A": 2.0, "B": 0.5}
    Ff = lambda m: F[[k for k, v in meas.items() if v is m][0]]
    base = RA.exposure(["CO"], probs, meas, {"R"}, Ff)
    withi = RA.exposure(["CO"], probs, meas, {"R"}, Ff, [{"state": "CO", "measure_i": "A", "measure_j": "B", "F_joint_bn": "2.1"}])
    assert base[0, 0] == pytest.approx(1.25) and withi[0, 0] == pytest.approx(1.25 + 0.75 * (2.1 - 2.5))
