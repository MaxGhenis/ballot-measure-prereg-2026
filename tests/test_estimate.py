"""Tests for the pre-registered estimators (pytest + Hypothesis).
Invariants: (1) beta is unchanged by adding any per-day constant to every state's spread (day intercepts);
(2) scaling X by c scales beta by 1/c; (3) beta is unchanged by permuting states; (4) with y independent of X, the
placebo test rejects about 5% of the time (size); (5) with beta planted at the reported smallest detectable effect,
it rejects about 80% of the time (power) and the mean estimate is unbiased; (6) classify() follows its stated rules."""
import pathlib, sys
import numpy as np, pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from hypothesis.extra.numpy import arrays
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from estimate import pooled_beta, pooled_test, measure_test, classify, placebo_blocks

fin = st.floats(-50, 50, allow_nan=False, allow_infinity=False)

@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.integers(3, 12), st.integers(1, 4), st.integers(0, 10**6))
def test_day_constants_scaling_permutation(S, T, seed):
    rng = np.random.default_rng(seed); y = rng.normal(size=(S, T)); X = rng.normal(size=(S, T))
    for icpt in (False, True):
        b = pooled_beta(y, X, icpt)
        c = rng.uniform(0.1, 10)
        assert pooled_beta(y, c * X, icpt) == pytest.approx(b / c, rel=1e-9, abs=1e-12)
        perm = rng.permutation(S)
        assert pooled_beta(y[perm], X[perm], icpt) == pytest.approx(b, rel=1e-9, abs=1e-12)
    bi = pooled_beta(y, X, True)
    assert pooled_beta(y + rng.normal(size=(1, T)), X, True) == pytest.approx(bi, rel=1e-9, abs=1e-12)
    # no intercept: beta is the X-weighted least-squares slope through the origin
    assert pooled_beta(y, X) == pytest.approx(float((X * y).sum() / (X ** 2).sum()), rel=1e-12)

def test_placebo_blocks_shape_and_content():
    Y = np.arange(20).reshape(2, 10)
    bl = placebo_blocks(Y, 3)
    assert bl.shape == (8, 2, 3) and (bl[2] == Y[:, 2:5]).all()

def _sim(beta, S=8, T=1, N=500, sims=600, seed=3):
    """Spread changes with fat tails and cross-state correlation; X fixed across simulations."""
    rng = np.random.default_rng(seed); rej = 0; est = []
    X = rng.normal(scale=2.0, size=(S, T))
    for _ in range(sims):
        common = rng.standard_t(4, size=N + T); idio = rng.standard_t(4, size=(S, N + T))
        Y = 0.6 * common[None, :] + idio
        y = Y[:, -T:] + beta * X; Yp = Y[:, :N]
        r = pooled_test(y, X, Yp); rej += r["p_placebo"] <= 0.05; est.append(r["beta"])
    return rej / sims, float(np.mean(est)), r

def test_size():
    size, _, _ = _sim(0.0)
    assert 0.02 <= size <= 0.08

def test_power_and_bias_at_mde():
    _, _, r = _sim(0.0, sims=1)
    mde = r["mde"]
    power, mean_b, _ = _sim(mde)
    assert 0.70 <= power <= 0.92
    assert abs(mean_b - mde) < 0.1 * mde

def test_measure_test_matches_pooled_single_state():
    rng = np.random.default_rng(0); y = rng.normal(size=3); dp = np.array([0.4, -0.1, 0.05]); Yp = rng.normal(size=300)
    r = measure_test(y, dp, Yp)
    assert r["b"] == pytest.approx((y * dp).sum() / (dp ** 2).sum())
    assert 0 < r["p_placebo"] <= 1

def _res(beta, se, p, lo=None, hi=None):
    lo = beta - 1.96 * se if lo is None else lo; hi = beta + 1.96 * se if hi is None else hi
    return {"status": "OK", "beta": beta, "se_placebo": se, "p_placebo": p, "ci95_placebo": [lo, hi]}

def test_classify_rules():
    ok_h3 = {"status": "OK", "p_placebo": 0.4}; bad_h3 = {"status": "OK", "p_placebo": 0.01}
    assert classify(_res(-3.0, 1.0, 0.01), ok_h3, 1.0) == ("CONFIRM", "passed")
    assert classify(_res(-3.0, 1.0, 0.01), None, 1.0) == ("CONFIRM", "untestable")
    assert classify(_res(-3.0, 1.0, 0.01), bad_h3, 1.0) == ("INCONCLUSIVE", "failed")      # the placebo set also moved
    assert classify(_res(3.0, 1.0, 0.01), ok_h3, 1.0)[0] == "WRONG SIGN"
    assert classify(_res(0.2, 0.3, 0.5), ok_h3, 2.0)[0] == "REFUTE"        # interval [-0.39, 0.79] lies above -2
    assert classify(_res(0.2, 2.0, 0.5), ok_h3, 2.0)[0] == "INCONCLUSIVE"  # interval [-3.7, 4.1] includes -2
    assert classify({"status": "UNESTIMABLE", "reason": "x"}, ok_h3, 2.0)[0] == "UNESTIMABLE"
    # H3 moved but could not be estimated: the gate blocks CONFIRM (only 'no N measure moved', h3=None, is untestable)
    assert classify(_res(-3.0, 1.0, 0.01), {"status": "UNESTIMABLE", "reason": "collinear"}, 1.0) == ("INCONCLUSIVE", "unestimable")
    # REFUTE reads the placebo interval, not the normal one
    assert classify(_res(0.2, 0.3, 0.5, lo=-2.5, hi=0.9), ok_h3, 2.0)[0] == "INCONCLUSIVE"

def test_unestimable_inputs():
    rng = np.random.default_rng(0); Yp = rng.normal(size=(4, 250)); y = rng.normal(size=(4, 3)); X = rng.normal(size=(4, 3))
    assert pooled_test(y, np.zeros_like(X), Yp)["status"] == "UNESTIMABLE"            # no exposure: no crash on an empty null
    yn = y.copy(); yn[1, 2] = np.nan
    r = pooled_test(yn, X, Yp)
    assert r["status"] == "UNESTIMABLE" and r["p_placebo"] is None                       # NaN never yields a small p
    Xn = X.copy(); Xn[0, 0] = np.nan
    assert pooled_test(y, Xn, Yp)["status"] == "UNESTIMABLE"
    assert pooled_test(y, X, Yp[:, :50])["status"] == "UNESTIMABLE"                     # too few placebo blocks
    assert classify(pooled_test(yn, X, Yp), None, 1.0)[0] == "UNESTIMABLE"
    assert measure_test(np.array([np.nan, 1, 2]), np.array([0.1, 0, 0]), Yp[0])["status"] == "UNESTIMABLE"
    assert measure_test(y[0], np.zeros(3), Yp[0])["status"] == "UNESTIMABLE"

def test_joint_test_controls_for_correlated_exposure():
    """With a real revenue effect and placebo-set surprises correlated with revenue surprises, the unconditional N slope is
    biased away from zero; the joint model's bN is not."""
    from estimate import joint_test
    rng = np.random.default_rng(5); S, T = 12, 3
    Yp = rng.standard_t(5, size=(S, 400)); XR = rng.normal(scale=3, size=(S, T)); XN = 0.8 * XR + rng.normal(scale=0.5, size=(S, T))
    y = -2.0 * XR + rng.normal(scale=0.3, size=(S, T))
    alone = pooled_test(y, XN, Yp)
    j = joint_test(y, XR, XN, Yp)
    assert alone["p_placebo"] < 0.05                     # the naive test would fail the gate
    assert abs(j["N"]["beta"]) < abs(alone["beta"]) and j["N"]["status"] == "OK"
    assert j["R"]["beta"] == pytest.approx(-2.0, abs=0.3)
    assert joint_test(y, np.zeros_like(XR), XN, Yp)["R"] is None   # no revenue exposure: placebo set alone
