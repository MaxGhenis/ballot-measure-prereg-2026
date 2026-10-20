"""The registered analysis, end to end, from one post-election capture directory (scripts/capture.py all).

  python scripts/run_analysis.py --window W0|W1|W2|W3              the registered capture for the window (below)
  python scripts/run_analysis.py data/raw/capture/<stamp> --window W1   a named capture; recorded as a deviation if it is
                                                                        not the registered one

Registered capture (REGISTRATION.md section 5.4): for W0 and W1, the first capture stamped after 9 p.m. Eastern on November 6
in which every rank-1 instrument has daily bars for November 3 to 6; if none has them by the capture stamped after 9 p.m.
Eastern on November 9, that capture, with every state still missing an event-day bar dropped and listed. W3: the first
capture after 9 p.m. Eastern on November 4 with 5-minute bars for November 3 and 4 (deadline: after 9 p.m. Eastern on
November 6). W2: the first capture after 9 p.m. Eastern on December 11 with daily bars for every W2 day (deadline: after
9 p.m. Eastern on December 14). Market data come from the first capture at or after the bar capture in which every measure
with a freeze price has, from at least one of its registered markets, the market record and the 60-minute price history
(or the venue's recorded answer that it has none); deadline the capture after 9 p.m. Eastern on November 13 (W2: December
14), after which omissions stand. Only sealed captures count (sealed() below; scripts/seal_capture.sh seals each one):
the manifest names the directory, records one capture command, started within an hour of the stamp and lists exactly the
files present with their sha256; it carries an OpenTimestamps receipt for its bytes; and the directory is committed with
no later change. W2's days are fixed in advance (W2_DAYS).

Steps (REGISTRATION.md sections 3-6):
 1. Probabilities. For each registered measure, the 4 p.m. Eastern probability on every sampling day from its primary market
    (Kalshi 60-minute candles: midpoint when the spread is 10 cents or less, else last trade, carried forward; Polymarket:
    last price at or before the time). Once a market has resolved, its probability from the resolution time on is the
    settlement value from the captured market record (Kalshi: result and close time; Polymarket: outcome prices and closed
    time). If the primary market lacks a price for any sampling time, the measure's other registered markets are tried in
    order of volume at enumeration; if none covers every time, the measure is omitted and listed with the reason.
 2. Exposure. E_s(t) = sum_i p_i(t) F_i + sum over registered pairs (registry/interactions.csv) of p_i(t) p_j(t) G_ij, where
    G_ij = F_joint - F_i - F_j (independent outcomes across markets). X[s, t] = E_s(t) - E_s(t-1).
 3. Spreads. y[s, t]: duration-matched spread changes for every testable state (registry/assets.csv rank 1); placebo matrix
    of the 250 trading days ending October 30, 2026, minus November 5-7, 2025.
 4. Tests. H3 first (placebo set, jointly with revenue exposure), then the primary pooled test, its registered reading
    (estimate.classify, with the H3 gate), the secondary specifications, H4 (bonds), per-measure tests and the
    federal-election-day check (archived prices in evidence/history/).
Windows: W0 = November 4; W1 = November 4-6; W2 = every trading day from November 9 to December 11, for measures whose
primary-market probability at the November 6 close is between 0.05 and 0.95 (others enter with dp = 0); W3 = intraday, ETF
states only, from the last 5-minute bar at or before 3:55 p.m. Eastern on November 3 to the bar ending 10:30 a.m. on
November 4, with the same clock window on earlier trading days as placebos.
Writes results/analysis_<window>.json and results/analysis_<window>.md."""
import csv, datetime as dt, json, pathlib, statistics, sys
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from estimate import pooled_test, joint_test, measure_test, classify
import panel as P
ET = ZoneInfo("America/New_York")
FIXED = {"W0": ["2026-11-04"], "W1": ["2026-11-04", "2026-11-05", "2026-11-06"]}
W2_RANGE = ("2026-11-09", "2026-12-11")
# W2's trading days, fixed in advance: NYSE weekdays in W2_RANGE without Thanksgiving (November 26). Fund NAVs post on
# Veterans Day and the day after Thanksgiving (checked in evidence/history/ for 2023-2025).
W2_DAYS = [str(d.date()) for d in pd.bdate_range(*W2_RANGE) if str(d.date()) != "2026-11-26"]
BASE = {"W0": "2026-11-03", "W1": "2026-11-03", "W2": "2026-11-06"}   # the close each window's first change starts from
FEDERAL_DAYS = ["2024-11-06", "2022-11-09"]
QUALITATIVE_ONETIME = {"tens of billions": 20.0}   # the smallest amount the phrase allows, $ billion
W3_MIN_BLOCKS = 30
# window: (earliest capture stamp, deadline stamp), UTC stamps of scripts/capture.py; 9 p.m. Eastern = 02:00 UTC next day
REG_CAPTURE = {"W1": ("20261107T020000Z", "20261110T020000Z"), "W0": ("20261107T020000Z", "20261110T020000Z"),
               "W3": ("20261105T020000Z", "20261107T020000Z"), "W2": ("20261212T020000Z", "20261215T020000Z")}
W1_BAR_DAYS = ["2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]
# market data: the first sealed capture at or after the bar capture in which every priced measure has a market record and a
# price history (or the venue's answer that there is none) from at least one of its markets; deadline below
MARKET_DEADLINE = {"W1": "20261114T020000Z", "W0": "20261114T020000Z", "W3": "20261114T020000Z", "W2": "20261215T020000Z"}
ANSWERED_EMPTY = ("endpoint returned no candles", "empty history")


def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


# ---------- probabilities ----------
def _4pm(d): return dt.datetime.combine(dt.date.fromisoformat(d), dt.time(16, 0), ET)


def kalshi_points(cap, ticker):
    """60-minute candles over the market's life merged with 1-minute candles from October 20, 2026."""
    cs = {}
    for iv in ("60m", "1m"):
        f = cap / f"kalshi_{ticker}_{iv}.json"
        if f.exists():
            for c in json.load(open(f))["data"]: cs[c["end_period_ts"]] = c
    if not cs: return None
    g = lambda d, k: (num(d.get(k + "_dollars", d.get(k))) if d else None)
    pts, last = [], None
    for _, c in sorted(cs.items()):
        b, a, lc = g(c.get("yes_bid"), "close"), g(c.get("yes_ask"), "close"), g(c.get("price"), "close")
        p = (a + b) / 2 if (b is not None and a is not None and a - b <= 0.10 and a > 0) else lc
        if p is not None: last = p
        pts.append((dt.datetime.fromtimestamp(c["end_period_ts"], dt.timezone.utc), last))
    return pts


def kalshi_settlement(cap, ticker):
    f = cap / f"kalshi_{ticker}_market.json"
    if not f.exists(): return None
    d = json.load(open(f)); m = d["data"]; m = m.get("market", m)
    if m.get("status") not in ("determined", "settled", "finalized", "amended") or m.get("result") not in ("yes", "no"): return None
    v = num(m.get("settlement_value_dollars")); v = v if v is not None else (1.0 if m["result"] == "yes" else 0.0)
    ts = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if m.get("settlement_ts"): return (ts(m["settlement_ts"]), v)
    # no settlement time: the close time counts only if it had passed when the record was captured (Kalshi rewrites
    # close_time when a market closes early; a scheduled close in the future says nothing about resolution)
    ct, got = m.get("close_time"), d.get("retrieved")
    if ct and got and ts(ct) <= ts(got): return (ts(ct), v)
    return None


def pm_points(cap, token):
    """60-minute history over the market's life merged with 1-minute history from October 20, 2026."""
    pts = {}
    for fid in ("60m", "1m"):
        f = cap / f"pm_{token}_{fid}.json"
        if f.exists():
            for x in json.load(open(f))["data"].get("history", []): pts[x["t"]] = float(x["p"])
    return [(dt.datetime.fromtimestamp(t, dt.timezone.utc), p) for t, p in sorted(pts.items())] if pts else None


def pm_settlement(cap, market_id):
    f = cap / f"pm_market_{market_id}.json"
    if not f.exists(): return None
    m = json.load(open(f))["data"]
    if not m.get("closed"): return None
    prices = json.loads(m["outcomePrices"]) if isinstance(m.get("outcomePrices"), str) else m.get("outcomePrices")
    v = num(prices[0]) if prices else None
    t = m.get("closedTime")          # endDate and umaEndDate can precede resolution; only the closed time counts
    if v not in (0.0, 1.0) or not t: return None
    t = t.replace(" ", "T").replace("+00", "+00:00").replace("Z", "+00:00")
    return (dt.datetime.fromisoformat(t), v)


def prob_at(points, settle, when):
    if settle and when >= settle[0]: return settle[1]
    best = None
    for t, p in points or []:
        if t <= when and p is not None: best = p
        elif t > when: break
    return best


def market_probs(cap, key, mkts, times):
    venue, mk = key.split(":", 1)
    if venue == "kalshi": pts, st = kalshi_points(cap, mk), kalshi_settlement(cap, mk)
    else:
        toks = json.loads((mkts.get(mk) or {}).get("clob_token_ids") or "[]")
        pts, st = (pm_points(cap, toks[0]) if toks else None), pm_settlement(cap, mk)
    if pts is None and st is None: return None, "no capture file"
    vals = [prob_at(pts, st, t) for t in times]
    return (vals, "") if all(v is not None for v in vals) else (None, "no price at one or more sampling times")


def measure_probs(cap, meas, mkts, prim, times):
    """Primary market first, then the measure's other registered markets by volume at enumeration."""
    out, used, omitted, venue_avg = {}, {}, {}, {}
    for mid, m in meas.items():
        keys = [k for k in (m.get("markets") or "").split(";") if k and not k.startswith("pending-series:")]
        first = prim.get(mid, {}).get("primary_market")
        if first not in keys: continue                       # not registered with a freeze price: outside the tests
        rest = sorted([k for k in keys if k != first], key=lambda k: -(num((mkts.get(k.split(":", 1)[1]) or {}).get("volume_at_enumeration")) or 0))
        reasons, got = [], []
        for k in [first] + rest:
            v, why = market_probs(cap, k, mkts, times)
            if v is None: reasons.append(f"{k}: {why}"); continue
            got.append((k, v))
        if not got: omitted[mid] = reasons; continue
        out[mid] = got[0][1]; used[mid] = got[0][0]
        venue_avg[mid] = list(np.mean([v for _, v in got], axis=0))
    return out, used, omitted, venue_avg


# ---------- exposure ----------
def onetime_annual(m):
    amt = (m.get("onetime_bn") or "").strip()
    a = num(amt) if num(amt) is not None else QUALITATIVE_ONETIME.get(amt.lower())
    yrs = num(m.get("onetime_years")) or 3.0
    return None if a is None else a / yrs


def exposure(states, probs, meas, cats, Ffun, inter=(), T=None, jcol="F_joint_bn"):
    """X[s, t] = change in expected revenue; probs[mid] = list of probabilities at the sampling times (first = baseline)."""
    T = (len(next(iter(probs.values()))) - 1 if probs else 0) if T is None else T
    E = np.zeros((len(states), T + 1))
    for mid, ps in probs.items():
        m = meas[mid]
        if m["category"] not in cats or m["state"] not in states: continue
        F = Ffun(m)
        if F is None: continue
        E[states.index(m["state"])] += np.array(ps) * F
    for r in inter:
        # a pair counts when either member is in the categories; a member outside them contributes F = 0 on its own
        i, j = r["measure_i"], r["measure_j"]
        if not (r.get(jcol) or "").strip() or i not in probs or j not in probs: continue
        if meas[i]["state"] not in states or (meas[i]["category"] not in cats and meas[j]["category"] not in cats): continue
        Fi = Ffun(meas[i]) if meas[i]["category"] in cats else 0.0
        Fj = Ffun(meas[j]) if meas[j]["category"] in cats else 0.0
        if Fi is None or Fj is None: continue
        G = float(r[jcol]) - Fi - Fj
        E[states.index(meas[i]["state"])] += np.array(probs[i]) * np.array(probs[j]) * G
    return np.diff(E, axis=1)


# ---------- spreads ----------
def spreads_daily(cap, assets):
    """(spread changes by state, [states with a leg whose price file is missing or unreadable])."""
    full, nofile = {}, []
    for a in assets:
        try:
            ys = P.leg(cap, a["tickers"].split(";")); yb = P.leg(cap, a["benchmark"].split(";"))
        except Exception:
            nofile.append(a["state"]); continue
        full[a["state"]] = (-(ys / float(a["duration_state"]) - yb / float(a["duration_bench"])) * 100)
    return pd.DataFrame(full), nofile


def _unestimable(res, window, days, out, reason):
    from estimate import _bad
    res.update({"days": days, "primary": _bad(reason), "reading": "UNESTIMABLE", "h3_gate": "untestable", "reading_upper_end": "UNESTIMABLE"})
    out = pathlib.Path(out) if out else ROOT / "results"; out.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(out / f"analysis_{window}.json", "w"), indent=1, default=float)
    (out / f"analysis_{window}.md").write_text(f"# Registered analysis, window {window}\n\nPrimary pooled test UNESTIMABLE: {reason}.\n")
    return res


def placebo_matrix(full):
    plac = full.dropna()
    plac = plac[~plac.index.isin(pd.to_datetime(P.EXCLUDE))].loc[:P.PLACEBO_END].iloc[-P.N_PLACEBO:]
    return plac


def yahoo_5m(cap, t):
    f = cap / f"yahoo_{t}_5m.json"
    if not f.exists(): return None
    d = json.load(open(f))["data"]["chart"]["result"][0]
    ts = pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_convert("America/New_York")
    return pd.Series(d["indicators"]["quote"][0]["close"], index=ts, dtype=float).dropna()


def at_or_before(s, when):
    s = s.loc[:when]
    return float(s.iloc[-1]) if len(s) else None


def intraday_spread(cap, a, t0, t1):
    """Spread change from the 5-minute bar starting at or before t0 to the bar starting at or before t1 - 5 minutes."""
    legs = []
    for side in ("tickers", "benchmark"):
        rs = []
        for t in a[side].split(";"):
            s = yahoo_5m(cap, t)
            if s is None: return None
            p0, p1 = at_or_before(s, t0), at_or_before(s, t1 - pd.Timedelta(minutes=5))
            if p0 is None or p1 is None: return None
            rs.append(100 * np.log(p1 / p0))
        legs.append(float(np.mean(rs)))
    return -(legs[0] / float(a["duration_state"]) - legs[1] / float(a["duration_bench"])) * 100


# ---------- registered capture, preflight, integrity ----------
def missing_bars(cap, assets, days, intraday=False):
    """{state: [days with no bar]} for every rank-1 instrument (state legs and benchmarks)."""
    out = {}
    for a in assets:
        miss = set()
        for t in a["tickers"].split(";") + a["benchmark"].split(";"):
            try:
                idx = {str(x.date()) for x in (yahoo_5m(cap, t).index if intraday else P.yahoo_daily(cap, t).index)}
            except Exception:                      # missing or malformed file: no bars
                idx = set()
            miss |= {d for d in days if d not in idx}
        if miss: out[a["state"]] = sorted(miss)
    return out


def window_bar_days(cap, window):
    if window in ("W0", "W1"): return W1_BAR_DAYS
    if window == "W3": return ["2026-11-03", "2026-11-04"]
    return [BASE["W2"]] + W2_DAYS


SKIPPED = {}   # capture dir -> why the registered rule skipped it
OTS_HEAD = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94\x01\x08"   # magic, version 1, sha256


def ots_matches(f):
    """True if f.ots is an OpenTimestamps receipt for f's current bytes (offline check of the digest it commits to; the
    Bitcoin attestation itself is checked with `ots verify`)."""
    import hashlib
    try: b = (f.parent / (f.name + ".ots")).read_bytes()
    except OSError: return False
    return b[:len(OTS_HEAD)] == OTS_HEAD and b[len(OTS_HEAD):len(OTS_HEAD) + 32] == hashlib.sha256(f.read_bytes()).digest()


def committed(c):
    """'' if the capture directory is in the repository's HEAD with no uncommitted change, else why not."""
    import subprocess
    g = lambda *a: subprocess.run(["git", "-C", str(c), *a], capture_output=True, text=True)
    if g("ls-files", "--error-unmatch", "manifest.json").returncode: return "not committed"
    if g("status", "--porcelain", "--", ".").stdout.strip(): return "uncommitted changes"
    return ""


def files_match(c, m):
    """'' if the directory holds exactly the files the manifest lists, with their sha256, else why not."""
    import hashlib
    want = m.get("files") or {}
    have = {q.name for q in c.iterdir() if q.is_file() and not q.name.startswith(".") and q.name not in ("manifest.json", "manifest.json.ots")}
    if have != set(want): return f"{len(have ^ set(want))} files differ from the manifest's list"
    for n, v in want.items():
        if hashlib.sha256((c / n).read_bytes()).hexdigest() != v.get("sha256"): return f"{n} differs from its manifest hash"
    return ""


def sealed(c):
    """'' if the capture counts under the registered rule, else why not: its manifest must name it, record exactly one
    capture command (no later merge via --dir), have started within an hour of the stamp in its name and list exactly the
    files present with their sha256; the manifest must carry an OpenTimestamps receipt for its bytes
    (scripts/seal_capture.sh); and the directory must be committed with no later change."""
    try:
        m = json.load(open(c / "manifest.json"))
        when = dt.datetime.strptime(c.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    except Exception as e: return f"no readable manifest or stamp ({e.__class__.__name__})"
    if m.get("stamp") != c.name: return f"manifest stamp {m.get('stamp')} differs from the directory name"
    if len(m.get("commands") or []) != 1: return f"manifest records {len(m.get('commands') or [])} capture commands"
    try: lag = (dt.datetime.fromisoformat(m["started"]) - when).total_seconds()
    except Exception: return "manifest has no start time"
    if not 0 <= lag <= 3600: return f"capture started {lag:.0f} s from its stamp"
    why = files_match(c, m)
    if why: return why
    if not ots_matches(c / "manifest.json"): return "no OpenTimestamps receipt matching manifest.json (run scripts/seal_capture.sh)"
    return committed(c)


def captures_from(lo):
    base = ROOT / "data/raw/capture"
    return sorted(d for d in base.iterdir() if d.is_dir() and d.name >= lo) if base.exists() else []


def registered_capture(window, assets):
    """Bar capture: (capture dir, {state: missing days}) under the registered rule, or (None, reason)."""
    lo, deadline = REG_CAPTURE[window]
    for c in captures_from(lo):
        why = sealed(c)
        if why: SKIPPED[str(c)] = why; continue
        try:
            days = window_bar_days(c, window)
            miss = missing_bars(c, assets if window != "W3" else [a for a in assets if a["instrument_type"].startswith("ETF")], days, intraday=(window == "W3"))
        except Exception as e:
            SKIPPED[str(c)] = f"unreadable ({e.__class__.__name__}: {e})"; continue
        if not miss or c.name >= deadline: return c, miss
    return None, f"no capture yet satisfies the rule for {window} (earliest stamp {lo}, deadline {deadline})"


def missing_markets(cap, meas, mkts, prim):
    """Priced measures for which no registered market has both its market record and its price history (or the venue's
    recorded answer that there is none) in this capture."""
    try: fails = {f["what"]: f["error"] for f in json.load(open(cap / "manifest.json")).get("failures", [])}
    except Exception: fails = {}
    out = []
    for mid, pr in prim.items():
        ok = False
        for key in [k for k in (meas.get(mid, {}).get("markets") or "").split(";") if k and not k.startswith("pending-series:")]:
            venue, mk = key.split(":", 1)
            if venue == "kalshi":
                rec = (cap / f"kalshi_{mk}_market.json").exists()
                hist = (cap / f"kalshi_{mk}_60m.json").exists() or fails.get(f"kalshi candles {mk} 60m") in ANSWERED_EMPTY
            else:
                toks = json.loads((mkts.get(mk) or {}).get("clob_token_ids") or "[]")
                rec = (cap / f"pm_market_{mk}.json").exists()
                hist = bool(toks) and ((cap / f"pm_{toks[0]}_60m.json").exists() or fails.get(f"polymarket history {toks[0]} 60m") in ANSWERED_EMPTY)
            if rec and hist: ok = True; break
        if not ok: out.append(mid)
    return out


def registered_market_capture(window, bar_cap, meas, mkts, prim):
    """Market capture: (capture dir, [measures missing market data]) or (None, reason)."""
    for c in captures_from(bar_cap.name):
        why = sealed(c)
        if why: SKIPPED[str(c)] = why; continue
        miss = missing_markets(c, meas, mkts, prim)
        if not miss or c.name >= MARKET_DEADLINE[window]: return c, miss
    return None, f"no capture yet has market data for every priced measure for {window} (deadline {MARKET_DEADLINE[window]})"


def integrity():
    """Compare every frozen file outside data/raw/capture/ and results/ with SHA256SUMS (written at the freeze), and list
    files in registry/, scripts/, evidence/ or tests/ that the sums do not cover."""
    import hashlib
    sums = ROOT / "SHA256SUMS"
    if not sums.exists(): return "not frozen: no SHA256SUMS"
    want = {}
    for line in sums.read_text().splitlines():
        h, f = line.split(None, 1); want[f.strip().lstrip("./")] = h
    bad, n = [], 0
    for f, h in want.items():
        if f.startswith("data/raw/capture/") or f.startswith("results/"): continue
        n += 1; pth = ROOT / f
        if not pth.exists() or hashlib.sha256(pth.read_bytes()).hexdigest() != h: bad.append(f)
    extra = sorted(str(q.relative_to(ROOT)) for d in ("registry", "scripts", "evidence", "tests") for q in (ROOT / d).rglob("*")
                   if q.is_file() and "__pycache__" not in q.parts and ".hypothesis" not in q.parts and str(q.relative_to(ROOT)) not in want)
    return {"files_checked": n, "mismatched": bad, "not_in_sums": extra}


# ---------- main ----------
def run(cap=None, window="W1", out=None):
    import hashlib
    R_ = lambda f: list(csv.DictReader(open(ROOT / "registry" / f)))
    meas = {r["measure_id"]: r for r in R_("measures.csv")}
    mkts = {r["market"]: r for r in R_("markets.csv")}
    prim = {r["measure_id"]: r for r in R_("prices_at_freeze.csv")}
    SKIPPED.clear()
    reg_cap, reg_miss = registered_capture(window, [a for a in R_("assets.csv") if a["rank"] == "1"])
    reg_mcap, reg_mmiss = registered_market_capture(window, reg_cap, meas, mkts, prim) if reg_cap is not None else (None, reg_miss)
    if cap is None:
        if reg_cap is None: raise SystemExit(reg_miss)
        if reg_mcap is None: raise SystemExit(reg_mmiss)
        cap, mcap = reg_cap, reg_mcap
    else:
        mcap = cap
    cap, mcap = pathlib.Path(cap), pathlib.Path(mcap)
    same = lambda a, b: b is not None and pathlib.Path(a).resolve() == pathlib.Path(b).resolve()
    inter = R_("interactions.csv") if (ROOT / "registry/interactions.csv").exists() else []
    assets_all = [a for a in R_("assets.csv") if a["rank"] == "1"]
    names = {r["abbr"]: r["name"] for r in R_("state_codes.csv")}
    tax = json.load(open(ROOT / "evidence/census/stc_2025_total_taxes.json"))["states"]
    manifest = json.load(open(cap / "manifest.json")) if (cap / "manifest.json").exists() else None
    mmanifest = json.load(open(mcap / "manifest.json")) if (mcap / "manifest.json").exists() else None
    sha = lambda c: hashlib.sha256((c / "manifest.json").read_bytes()).hexdigest() if (c / "manifest.json").exists() else None
    res = {"capture": str(cap), "market_capture": str(mcap), "window": window,
           "capture_manifest_sha256": sha(cap), "market_capture_manifest_sha256": sha(mcap),
           "registered_capture": str(reg_cap) if reg_cap else reg_miss,
           "registered_market_capture": str(reg_mcap) if reg_mcap else reg_mmiss,
           "measures_missing_market_data": missing_markets(mcap, meas, mkts, prim),
           "skipped_captures": dict(SKIPPED),
           "deviation": None if (same(cap, reg_cap) and same(mcap, reg_mcap)) else "not the registered capture (record in DEVIATIONS.md)",
           "capture_failures": manifest.get("failures") if manifest else "manifest missing",
           "market_capture_failures": mmanifest.get("failures") if mmanifest else "manifest missing", "integrity": integrity()}
    try: res["preflight_missing_bars"] = missing_bars(cap, assets_all if window != "W3" else [a for a in assets_all if a["instrument_type"].startswith("ETF")],
                                                      window_bar_days(cap, window), intraday=(window == "W3"))
    except Exception as e: res["preflight_missing_bars"] = f"preflight failed: {e}"
    pre = res["preflight_missing_bars"] if isinstance(res["preflight_missing_bars"], dict) else {}

    full, nofile = spreads_daily(cap, assets_all)
    plac = placebo_matrix(full)
    cal = [d for d in full.index]
    if window == "W3":
        assets = [a for a in assets_all if a["instrument_type"].startswith("ETF")]
        states = [a["state"] for a in assets]
        t0, t1 = pd.Timestamp("2026-11-03 15:55", tz="America/New_York"), pd.Timestamp("2026-11-04 10:30", tz="America/New_York")
        y = np.array([[v if v is not None else np.nan] for v in (intraday_spread(cap, a, t0, t1) for a in assets)])
        Ypl = []
        s5 = {t: yahoo_5m(cap, t) for t in {a["tickers"] for a in assets}}
        days5 = sorted({ts.normalize() for s in s5.values() if s is not None for ts in s.index})
        for d0, d1 in zip(days5[:-1], days5[1:]):
            if d1.date() >= dt.date(2026, 11, 3): break
            col = [intraday_spread(cap, a, d0 + pd.Timedelta(hours=15, minutes=55), d1 + pd.Timedelta(hours=10, minutes=30)) for a in assets]
            if all(v is not None for v in col): Ypl.append(col)
        Yp = np.array(Ypl).T if Ypl else np.zeros((len(states), 0))
        times = [(t0 + pd.Timedelta(minutes=5)).to_pydatetime(), t1.to_pydatetime()]   # 16:00 = close of the 15:55 bar
        days = ["2026-11-03 15:55 to 2026-11-04 10:30"]
    else:
        assets = assets_all; states = list(full.columns)
        days = FIXED[window] if window in FIXED else W2_DAYS
        missing_days = [d for d in [BASE[window]] + days if pd.Timestamp(d) not in full.index]   # baseline close included
        if missing_days:
            res["missing_event_days"] = missing_days
            return _unestimable(res, window, days, out, f"registered day(s) {missing_days} missing from every series")
        prev = BASE[window]
        times = [_4pm(d) for d in ([prev] + days)] if days else []
        y = full.loc[pd.to_datetime(days)].T.to_numpy() if days else np.zeros((len(states), 0))
        Yp = plac.T.to_numpy()
    y = np.asarray(y, float)
    universe = {a["state"] for a in assets}
    why = {s: f"missing bars on {', '.join(v)}" for s, v in pre.items() if s in universe}    # exactly the registered preflight
    why.update({s: "no price file for a leg" for s in nofile if s in universe and s not in why})
    why.update({s: "missing an event-window value" for k, s in enumerate(states) if s not in why and not (y.shape[1] and np.all(np.isfinite(y[k])))})
    keep = [k for k, s in enumerate(states) if s not in why]
    res["dropped_states"] = dict(sorted(why.items()))
    if res["dropped_states"]:
        states = [states[k] for k in keep]; y = y[keep]; Yp = np.asarray(Yp)[keep]
    R = {s: tax[names[s]]["total_taxes_thousands"] / 1e6 for s in states}
    probs, used, omitted, venue_avg = measure_probs(mcap, meas, mkts, prim, times) if times else ({}, {}, {}, {})
    if window == "W2":   # eligibility: primary-market probability at the November 6 close between 0.05 and 0.95
        p6, _, _, _ = measure_probs(mcap, meas, mkts, prim, [_4pm("2026-11-06")])
        elig = {m for m, v in p6.items() if 0.05 < v[0] < 0.95}
        res["w2_eligible"] = sorted(elig)
        probs = {m: (v if m in elig else [v[0]] * len(v)) for m, v in probs.items()}
        venue_avg = {m: (v if m in elig else [v[0]] * len(v)) for m, v in venue_avg.items()}
    res.update({"days": days, "states": states, "y_bp": dict(zip(states, np.asarray(y).tolist())), "n_placebo_columns": int(np.asarray(Yp).shape[1]),
                "markets_used": used, "fallbacks": {m: k for m, k in used.items() if k != prim[m]["primary_market"]},
                "omitted_measures": omitted, "probabilities": probs})
    fR = lambda m: num(m.get("F_annual_bn"))
    nT = max(len(times) - 1, 0)
    exp_ = lambda pr, cats, Ff, it=(), jc="F_joint_bn": exposure(states, pr, meas, cats, Ff, it, nT, jc)
    X = exp_(probs, {"R"}, fR, inter)
    XN = exp_(probs, {"N"}, lambda m: 1.0)
    mb = W3_MIN_BLOCKS if window == "W3" else None
    test = lambda yy, XX, intercept=False: pooled_test(yy, XX, Yp, intercept, min_blocks=mb)
    h3 = joint_test(y, X, XN, Yp, min_blocks=mb) if np.any(XN) else {"N": None, "R": None}
    res["placebo_set_N"] = h3["N"] if h3["N"] is not None else "no category N measure moved"
    XNx = exp_(probs, {"N"}, lambda m: 0.0 if m.get("n_tax_limit") else 1.0)       # reported, not a gate
    res["placebo_set_N_excluding_tax_limits"] = (joint_test(y, X, XNx, Yp, min_blocks=mb)["N"] if np.any(XNx) else "no such measure moved")
    res["primary"] = test(y, X)
    w = (X ** 2).sum(axis=1)
    bench = [float((w * np.array([-k / R[s] for s in states])).sum() / w.sum()) if w.sum() > 0 else None for k in (70.0, 150.0)]
    res["benchmark_bp_per_bn"] = {"nmr_7bp": bench[0], "nmr_15bp": bench[1]}
    if bench[0] is None: res["reading"], res["h3_gate"], res["reading_upper_end"] = "UNESTIMABLE", "untestable", "UNESTIMABLE"
    else:
        res["reading"], res["h3_gate"] = classify(res["primary"], h3["N"], abs(bench[0]))
        res["reading_upper_end"] = classify(res["primary"], h3["N"], abs(bench[1]))[0]
    Fmed = statistics.median([abs(fR(m)) for m in meas.values() if m["category"] == "R" and fR(m)]) if any(m["category"] == "R" for m in meas.values()) else None
    sign = lambda m: num(m.get("F_sign"))
    res["secondary"] = {
        "day_intercepts": test(y, X, intercept=True),
        "revenue_share_bp_per_pct": test(y, X / np.array([[R[s] / 100] for s in states])),
        "with_other_fiscal_O": test(y, X + exp_(probs, {"O"}, lambda m: num(m.get("F_secondary_bn")))),
        "policyengine_F_where_available": test(y, exp_(probs, {"R"}, lambda m: num(m.get("pe_F_annual_bn")) if num(m.get("pe_F_annual_bn")) is not None else fR(m), inter)),
        "venue_average": test(y, exp_(venue_avg, {"R"}, fR, inter)) if venue_avg else "no probabilities",
        "with_RU_signed_median_F": test(y, X + exp_(probs, {"RU"}, lambda m: (sign(m) * Fmed) if sign(m) and Fmed else None)),
        "with_onetime_spread": test(y, X + exp_(probs, {"R", "RU", "O"}, onetime_annual)),
        "with_stated_receipts_RU": test(y, X + exp_(probs, {"RU"}, lambda m: num(m.get("F_secondary_bn")))),
        "interactions_at_low_bound": test(y, exp_(probs, {"R"}, fR, [dict(r, F_joint_bn=r["F_joint_low_bn"] or r["F_joint_bn"]) for r in inter])),
        "interactions_at_high_bound": test(y, exp_(probs, {"R"}, fR, [dict(r, F_joint_bn=r["F_joint_high_bn"] or r["F_joint_bn"]) for r in inter])),
        "no_interactions": test(y, exp_(probs, {"R"}, fR)),
    }
    ds = lambda m: (lambda v: sum(v) / len(v) if v else None)([float(x) for x in (m.get("debt_service_bn_per_year") or "").replace("to", " ").split() if num(x) is not None])
    res["H4_bonds_bp_per_bn_debt_service"] = test(y, exp_(probs, {"B"}, ds))
    res["per_measure"] = {}
    for mid, ps in probs.items():
        m = meas[mid]
        if m["state"] not in states or m["category"] not in ("R", "RU", "B"): continue
        d = np.diff(ps); k = states.index(m["state"])
        t = measure_test(y[k], d, Yp[k]) if window != "W3" else {"status": "not run intraday", "b": None}
        if t.get("b") is not None and fR(m): t["b_per_bn"] = t["b"] / fR(m)
        t["joint_with"] = sorted({o for o, pp in probs.items() if o != mid and meas[o]["state"] == m["state"] and meas[o]["category"] in ("R", "RU", "B", "O") and np.max(np.abs(np.diff(pp))) >= 0.10}
                                 | {(r["measure_j"] if r["measure_i"] == mid else r["measure_i"]) for r in inter if mid in (r["measure_i"], r["measure_j"])})
        res["per_measure"][mid] = t
    res["federal_election_days"] = federal_check(assets_all, plac) if window == "W1" else "reported with W1"
    out = pathlib.Path(out) if out else ROOT / "results"; out.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(out / f"analysis_{window}.json", "w"), indent=1, default=float)
    r = res["primary"]
    md = [f"# Registered analysis, window {window} ({', '.join(days)})", ""]
    if r.get("status") == "OK":
        md.append(f"Primary pooled beta: {r['beta']:+.3f} bp per $ billion a year (placebo SE {r['se_placebo']:.3f}, p = {r['p_placebo']:.3f}, placebo 95% interval {r['ci95_placebo'][0]:+.3f} to {r['ci95_placebo'][1]:+.3f}, detectable about {r['mde']:.3f}).")
    else:
        md.append(f"Primary pooled test UNESTIMABLE: {r.get('reason')}.")
    md += [f"Benchmark (Novy-Marx and Rauh, illustrative): {res['benchmark_bp_per_bn']}.",
           f"Registered reading: **{res['reading']}** (placebo-set gate: {res['h3_gate']}; against the 15 bp end: {res['reading_upper_end']}).",
           f"Omitted measures: {len(omitted)}; fallbacks to a secondary market: {len(res['fallbacks'])}; dropped states: {len(res['dropped_states'])}; capture failures: {len(manifest.get('failures') or []) if manifest else 'manifest missing'} (bars), {len(mmanifest.get('failures') or []) if mmanifest else 'manifest missing'} (markets).",
           f"Bar capture: {res['capture']} (registered: {res['registered_capture']}); market capture: {res['market_capture']} (registered: {res['registered_market_capture']}); measures missing market data: {len(res['measures_missing_market_data'])}; deviation: {res['deviation']}; integrity: {res['integrity']}.", ""]
    (out / f"analysis_{window}.md").write_text("\n".join(md))
    return res


def federal_check(assets, plac):
    """Spread changes on the trading days after the 2024 and 2022 federal elections, from archived prices, against the
    placebo distribution. A day counts only when the archive has both that day and the previous trading day."""
    H = ROOT / "evidence/history"
    if not H.exists(): return "archive missing"
    out = {}
    for a in assets:
        try:
            ser = []
            for side in ("tickers", "benchmark"):
                ser.append(pd.concat([100 * np.log(P.yahoo_daily(H, t)).diff() for t in a[side].split(";")], axis=1).mean(axis=1, skipna=False))
            y = (-(ser[0] / float(a["duration_state"]) - ser[1] / float(a["duration_bench"])) * 100)
        except FileNotFoundError:
            out[a["state"]] = "not archived"; continue
        cal = list(P.yahoo_daily(H, "MUB").index)
        for d in FEDERAL_DAYS:
            ts_ = pd.Timestamp(d); v = None
            if ts_ in cal:
                prev = cal[cal.index(ts_) - 1]
                legs = [P.yahoo_daily(H, x).index for x in a["tickers"].split(";") + a["benchmark"].split(";")]
                if all(ts_ in ix and prev in ix for ix in legs): v = y.get(ts_)
            share = float(np.mean(np.abs(plac[a["state"]]) >= abs(v))) if (v is not None and a["state"] in plac.columns) else "no placebo series in this capture"
            out.setdefault(a["state"], {})[d] = ({"y_bp": float(v), "placebo_share_abs_ge": share}
                                                 if v is not None and np.isfinite(v) else "unavailable (day or previous close missing)")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]; win = args[args.index("--window") + 1] if "--window" in args else "W1"
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--window")]
    cap = pathlib.Path(pos[0]).resolve() if pos else None
    r = run(cap, win)
    print(json.dumps({k: r.get(k) for k in ("primary", "placebo_set_N", "benchmark_bp_per_bn", "reading", "h3_gate", "reading_upper_end", "omitted_measures", "fallbacks")}, indent=1, default=float))
