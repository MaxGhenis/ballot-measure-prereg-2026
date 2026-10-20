"""Pre-registered estimators for the November 3, 2026 ballot-measure study (pure numpy; no data access).

Notation
  states s = 1..S with a testable spread; event days t in E (trading days, close-to-close).
  y[s, t]  change in state s's state-minus-benchmark yield spread on day t, in basis points (duration-matched).
  X[s, t]  change on day t in the expected annual state plus local revenue from state s's registered revenue measures, in
           $ billion a year: sum over measures i of dp[i, t] * F[i], plus the registered pair interactions
           (registry/interactions.csv), computed by run_analysis.py.

Pooled model (primary):  y[s, t] = beta * X[s, t] + e[s, t]; beta is in bp per $ billion a year. Secondary: one intercept
per event day (within-day demeaning), which needs at least three states.
Inference: date-shift placebos. X stays fixed and y is replaced by the spread changes on each block of T consecutive placebo
trading days (the same days for every state, so cross-state correlation and fat tails are kept). Placebo SE = standard
deviation of the placebo betas; p = share of placebo |beta| at least as large as |beta|, with the +1 correction; the 95%
interval is the placebo interval [beta - q97.5, beta - q2.5] of the placebo betas. The smallest detectable effect is
reported as 2.8 x placebo SE, an approximation that assumes the placebo betas are close to normal.

Validity: every estimator returns status "UNESTIMABLE" with a reason, never a number, when an input is not finite, when
there is no exposure (sum of X^2 is zero), or when there are fewer than MIN_BLOCKS placebo blocks."""
import numpy as np

MIN_BLOCKS = 100


def _bad(reason):
    return {"status": "UNESTIMABLE", "reason": reason, "beta": None, "se_placebo": None, "p_placebo": None, "mde": None,
            "n_placebo": 0, "ci95_placebo": None}


def pooled_beta(y, X, intercept=False):
    """OLS of y on X (no intercept), or with one intercept per event day. y, X: arrays of shape (S, T). Returns beta."""
    y = np.asarray(y, float); X = np.asarray(X, float)
    if intercept:
        y = y - y.mean(axis=0, keepdims=True); X = X - X.mean(axis=0, keepdims=True)   # within-day demeaning = day intercepts
    sxx = float((X ** 2).sum())
    if sxx <= 0: return float("nan")
    return float((X * y).sum() / sxx)


def placebo_blocks(Y, T):
    """All blocks of T consecutive placebo days from a (S, N) matrix of daily spread changes: shape (N - T + 1, S, T)."""
    Y = np.asarray(Y, float); S, N = Y.shape
    return np.stack([Y[:, k:k + T] for k in range(N - T + 1)])


def _validate(y, Xs, Yplacebo, intercept, min_blocks=None):
    min_blocks = MIN_BLOCKS if min_blocks is None else min_blocks
    y = np.asarray(y, float); Yp = np.asarray(Yplacebo, float)
    if y.ndim != 2 or y.size == 0: return "no event-window spreads"
    if not np.all(np.isfinite(y)): return "a spread change in the event window is missing or not finite"
    for X in Xs:
        X = np.asarray(X, float)
        if X.shape != y.shape: return "exposure and spread shapes differ"
        if not np.all(np.isfinite(X)): return "an exposure is missing or not finite"
        Xd = X - X.mean(axis=0, keepdims=True) if intercept else X
        if float((Xd ** 2).sum()) <= 0: return "no exposure: no registered measure moved"
    if intercept and y.shape[0] < 3: return "fewer than three states for day intercepts"
    if Yp.ndim != 2 or Yp.shape[0] != y.shape[0]: return "placebo matrix does not match the states"
    if not np.all(np.isfinite(Yp)): return "a placebo spread change is missing or not finite"
    if Yp.shape[1] - y.shape[1] + 1 < min_blocks: return f"fewer than {min_blocks} placebo blocks"
    return None


def _summarize(b, null):
    se = float(np.std(null, ddof=1))
    p = float((1 + (np.abs(null) >= abs(b)).sum()) / (len(null) + 1))
    return {"status": "OK", "reason": "", "beta": float(b), "se_placebo": se, "p_placebo": p, "mde": 2.8 * se,
            "n_placebo": int(len(null)),
            "ci95_placebo": [float(b - np.quantile(null, 0.975)), float(b - np.quantile(null, 0.025))],
            "ci95_normal": [float(b - 1.96 * se), float(b + 1.96 * se)]}


def pooled_test(y, X, Yplacebo, intercept=False, min_blocks=None):
    """beta, placebo SE, placebo p-value, placebo interval and smallest detectable effect for the pooled model."""
    why = _validate(y, [X], Yplacebo, intercept, min_blocks)
    if why: return _bad(why)
    y = np.asarray(y, float); X = np.asarray(X, float); T = y.shape[1]
    b = pooled_beta(y, X, intercept)
    null = np.array([pooled_beta(blk, X, intercept) for blk in placebo_blocks(Yplacebo, T)])
    return _summarize(b, null)


def _ols2(y, XR, XN):
    A = np.array([[float((XR * XR).sum()), float((XR * XN).sum())], [float((XR * XN).sum()), float((XN * XN).sum())]])
    if abs(np.linalg.det(A)) < 1e-12 * max(1.0, abs(A).max()) ** 2: return None
    return np.linalg.solve(A, np.array([float((XR * y).sum()), float((XN * y).sum())]))


def joint_test(y, XR, XN, Yplacebo, min_blocks=None):
    """H3: y = bR * XR + bN * XN + e, with date-shift placebos for both coefficients. bN tests the placebo set conditional
    on revenue exposure, so a correlation between placebo-set and revenue surprises cannot produce a spurious bN. When XR is
    all zero (no revenue measure moved), the model reduces to y = bN * XN."""
    XR = np.asarray(XR, float); XN = np.asarray(XN, float); y = np.asarray(y, float)
    if not np.any(XR):
        r = pooled_test(y, XN, Yplacebo, min_blocks=min_blocks); r["model"] = "placebo set alone (no revenue exposure)"; return {"N": r, "R": None}
    why = _validate(y, [XR, XN], Yplacebo, False, min_blocks)
    if why: return {"N": _bad(why), "R": _bad(why)}
    b = _ols2(y, XR, XN)
    if b is None: return {"N": _bad("placebo-set and revenue exposures are collinear"), "R": _bad("collinear")}
    T = y.shape[1]
    null = np.array([v for v in (_ols2(blk, XR, XN) for blk in placebo_blocks(Yplacebo, T)) if v is not None])
    rN = _summarize(b[1], null[:, 1]); rN["model"] = "joint with revenue exposure"
    rR = _summarize(b[0], null[:, 0]); rR["model"] = "joint with placebo-set exposure"
    return {"N": rN, "R": rR}


def measure_test(y_s, dp_i, Yplacebo_s):
    """Per-measure slope b = sum_t y dp / sum_t dp^2 (bp per full swing) on one state's spread, with date-shift placebos."""
    y_s = np.asarray(y_s, float); dp_i = np.asarray(dp_i, float); Yp = np.asarray(Yplacebo_s, float); T = len(y_s)
    if not (np.all(np.isfinite(y_s)) and np.all(np.isfinite(dp_i)) and np.all(np.isfinite(Yp))):
        return {"status": "UNESTIMABLE", "reason": "missing or non-finite input", "b": None}
    den = float((dp_i ** 2).sum())
    if den <= 0: return {"status": "UNESTIMABLE", "reason": "no probability movement in the window", "b": None}
    if len(Yp) - T + 1 < MIN_BLOCKS: return {"status": "UNESTIMABLE", "reason": f"fewer than {MIN_BLOCKS} placebo blocks", "b": None}
    b = float((y_s * dp_i).sum() / den)
    null = np.array([(Yp[k:k + T] * dp_i).sum() / den for k in range(len(Yp) - T + 1)])
    r = _summarize(b, null); r["b"] = r.pop("beta"); r["sum_dp2"] = den
    return r


def classify(primary, h3, benchmark, sign_expected=-1.0, alpha=0.05):
    """The registered reading of the pooled estimate (REGISTRATION.md section 6).
    primary: a pooled_test result. h3: the placebo-set result (joint_test(...)["N"]), or None only when no placebo-set
    measure moved. benchmark: the benchmark effect's magnitude (bp per $ billion a year) at the end being read.
    UNESTIMABLE  the primary test could not be computed (its reason is reported).
    CONFIRM      p < alpha, beta has the expected sign, and the placebo-set gate passes: H3 p >= alpha, or h3 is None
                 because no placebo-set measure moved (gate "untestable", reported as such).
    INCONCLUSIVE p < alpha with the expected sign but the gate fails: H3 rejects ("failed") or H3 moved but could not be
                 estimated ("unestimable"); or nothing below applies.
    WRONG SIGN   p < alpha and the other sign (an anomaly, never support).
    REFUTE       p >= alpha and the placebo 95% interval lies entirely on the near side of the benchmark (for an expected
                 negative effect, above -|benchmark|).
    Returns (reading, gate) where gate is "passed", "failed", "unestimable" or "untestable"."""
    if primary is None or primary.get("status") != "OK": return "UNESTIMABLE", "untestable"
    if h3 is None: gate = "untestable"
    elif h3.get("status") != "OK": gate = "unestimable"
    else: gate = "passed" if h3["p_placebo"] >= alpha else "failed"
    beta, p = primary["beta"], primary["p_placebo"]; lo, hi = primary["ci95_placebo"]
    if p < alpha:
        if np.sign(beta) != np.sign(sign_expected): return "WRONG SIGN", gate
        return ("CONFIRM" if gate in ("passed", "untestable") else "INCONCLUSIVE"), gate
    bench = sign_expected * abs(benchmark)
    excluded = (bench < lo) if sign_expected < 0 else (bench > hi)
    return ("REFUTE" if excluded else "INCONCLUSIVE"), gate
