"""Property-based (fuzz) tests over the whole engine.

These are not example tests. Each one states an **invariant that must hold for every
input**, and Hypothesis then hunts for a counterexample by generating inputs — including
the degenerate ones a human never types: empty ranges, zero denominators, negative
budgets, `NaN`-adjacent floats, unicode, and enormous numbers.

What this buys over the example tests: the example tests check the cases we thought of.
These check the cases we did not.

Run everything:      uv run pytest tests/test_fuzz.py
Deeper search:       uv run pytest tests/test_fuzz.py --hypothesis-seed=random -p no:randomly
Reproduce a failure: the failing example is printed and stored in `.hypothesis/`
"""

from __future__ import annotations

import math
from urllib.parse import quote

import numpy as np
import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from app.main import app
from app.risk.asset_criticality import DIMENSIONS, CriticalityProfile, criticality_band
from app.risk.control_effect import (
    ControlApplication,
    ControlCategory,
    ControlEvidence,
    apply_control_effects,
    factor_effect,
    scale_distribution,
    shift_distribution,
)
from app.risk.distributions import BetaPert, Constant, Lognormal, Poisson
from app.risk.frequency import FrequencyModel
from app.risk.magnitude import MagnitudeModel
from app.risk.metrics import (
    annualize,
    risk_reduction,
    risk_reduction_pct,
    risk_removed_per_unit,
    rosi,
)
from app.risk.monte_carlo import SimulationConfig, run_simulation, summarize
from app.risk.provenance import (
    SOURCE_CREDIBILITY,
    ConfidenceBand,
    EvidenceMix,
    Provenance,
    SourceType,
    confidence_band,
)

SETTINGS = settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)

# Floats that behave badly: zero, negatives, huge, subnormal, infinities excluded.
FINITE = st.floats(allow_nan=False, allow_infinity=False)
UNIT = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
SMALL_POSITIVE = st.floats(min_value=1e-9, max_value=1e6, allow_nan=False)
PERCENTILE = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)

DIMENSION_SCORES = st.integers(min_value=0, max_value=5)

# A workable magnitude range. Generating raw FINITE floats and then filtering on the
# spread discards almost everything, which both slows generation and distorts the domain —
# so the range is built up from bounded pieces instead.
_MAGNITUDE = st.floats(min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False)


@st.composite
def ordered_triples(draw: st.DrawFn, *, min_spread: float = 0.0) -> tuple[float, float, float]:
    """Generate ``(min, mode, max)`` already in order, rather than filtering for it."""
    lo = draw(_MAGNITUDE)
    spread = draw(st.floats(min_value=min_spread, max_value=1e9, allow_nan=False))
    hi = lo + spread
    mode = lo + draw(st.floats(min_value=0.0, max_value=max(spread, 0.0), allow_nan=False))
    return lo, min(mode, hi), hi


# ---------------------------------------------------------------------------------------
# 1. Distributions
# ---------------------------------------------------------------------------------------
@SETTINGS
@given(triple=ordered_triples(), weight=st.floats(min_value=0.01, max_value=50.0))
def test_beta_pert_samples_stay_within_bounds(
    triple: tuple[float, float, float], weight: float
) -> None:
    """A bounded distribution must never emit a value outside its support."""
    lo, mode, hi = triple
    dist = BetaPert(lo, mode, hi, weight)
    samples = dist.sample(np.random.default_rng(0), 500)
    assert np.all(samples >= lo - 1e-9)
    assert np.all(samples <= hi + 1e-9)


@SETTINGS
@given(triple=ordered_triples(min_spread=1e-3))
def test_beta_pert_mean_matches_closed_form(triple: tuple[float, float, float]) -> None:
    """The analytic mean must agree with a Monte Carlo draw, within sampling error.

    The tolerance comes from the standard error of the mean — ``std / sqrt(n)`` — not from
    the size of the mean. Those differ by orders of magnitude when the distribution is
    skewed toward its lower bound (``mode == minimum`` gives ``Beta(1, 5)``, whose relative
    spread is ~85%), and the mean itself can sit arbitrarily close to zero.
    """
    lo, mode, hi = triple
    assume(abs(hi - lo) < 1e9)
    assume(abs(hi) < 1e12)  # keep the Beta parameters numerically stable

    n = 200_000
    dist = BetaPert(lo, mode, hi)
    empirical = float(np.mean(dist.sample(np.random.default_rng(1), n)))

    standard_error = dist.std / math.sqrt(n)
    assert abs(empirical - dist.mean) < 6 * standard_error + 1e-6


@SETTINGS
@given(triple=ordered_triples())
def test_beta_pert_variance_is_non_negative_and_finite(
    triple: tuple[float, float, float],
) -> None:
    lo, mode, hi = triple
    dist = BetaPert(lo, mode, hi)
    assert dist.variance >= 0.0
    assert math.isfinite(dist.variance)
    assert math.isfinite(dist.std)


@SETTINGS
@given(value=_MAGNITUDE)
def test_degenerate_beta_pert_is_constant(value: float) -> None:
    """min == mode == max must collapse to a point mass, not divide by zero."""
    dist = BetaPert(value, value, value)
    assert dist.is_degenerate
    assert dist.variance == 0.0
    samples = dist.sample(np.random.default_rng(2), 50)
    assert np.allclose(samples, value)


@given(a=FINITE, b=FINITE, c=FINITE)
def test_beta_pert_rejects_unordered_input(a: float, b: float, c: float) -> None:
    """The constructor must reject a mis-ordered triple rather than silently reorder."""
    assume(math.isfinite(a) and math.isfinite(b) and math.isfinite(c))
    assume(not (a <= b <= c))
    with pytest.raises(ValueError):
        BetaPert(a, b, c)


@SETTINGS
@given(median=SMALL_POSITIVE, ratio=st.floats(min_value=1.01, max_value=100.0))
def test_lognormal_from_median_p90_round_trips(median: float, ratio: float) -> None:
    """The 90th percentile of the fitted lognormal should recover the input p90."""
    p90 = median * ratio
    dist = Lognormal.from_median_p90(median, p90)
    samples = dist.sample(np.random.default_rng(3), 300_000)
    assert abs(float(np.median(samples)) - median) / median < 0.05
    empirical_p90 = float(np.percentile(samples, 90))
    assert abs(empirical_p90 - p90) / p90 < 0.05


@SETTINGS
@given(rate=st.floats(min_value=0.0, max_value=1e4))
def test_poisson_never_returns_negative_counts(rate: float) -> None:
    samples = Poisson(rate).sample(np.random.default_rng(4), 1000)
    assert np.all(samples >= 0)
    assert np.all(np.equal(np.mod(samples, 1), 0))


@given(rate=st.floats(max_value=-1e-9, allow_nan=False, allow_infinity=False))
def test_poisson_rejects_negative_rate(rate: float) -> None:
    with pytest.raises(ValueError):
        Poisson(rate)


@SETTINGS
@given(triple=ordered_triples(), m=st.floats(min_value=0.0, max_value=10.0))
def test_scale_distribution_preserves_ordering(
    triple: tuple[float, float, float], m: float
) -> None:
    """Scaling must not break min <= mode <= max, or the constructor would raise."""
    scaled = scale_distribution(BetaPert(*triple), m)
    if isinstance(scaled, BetaPert):
        assert scaled.minimum <= scaled.mode <= scaled.maximum


@SETTINGS
@given(triple=ordered_triples(), d=_MAGNITUDE)
def test_shift_distribution_preserves_ordering(
    triple: tuple[float, float, float], d: float
) -> None:
    shifted = shift_distribution(BetaPert(*triple), d, cap=100.0)
    if isinstance(shifted, BetaPert):
        assert shifted.minimum <= shifted.mode <= shifted.maximum


@SETTINGS
@given(triple=ordered_triples())
def test_zero_multiplier_collapses_to_zero(triple: tuple[float, float, float]) -> None:
    """A fully-effective avoidance control must zero the value, not invert it."""
    assert scale_distribution(BetaPert(*triple), 0.0) == Constant(0.0)


@given(dist=st.one_of(st.integers(), st.text()))
def test_scale_distribution_rejects_unknown_types(dist: object) -> None:
    with pytest.raises(TypeError):
        scale_distribution(dist, 2.0)


# ---------------------------------------------------------------------------------------
# 2. Control effectiveness
# ---------------------------------------------------------------------------------------
@SETTINGS
@given(coverage=UNIT, config=UNIT, policy=UNIT, incident=UNIT, age=st.integers(0, 10_000))
def test_effectiveness_is_always_bounded(
    coverage: float, config: float, policy: float, incident: float, age: int
) -> None:
    """Whatever evidence we feed in, effectiveness must land in [0, 1]."""
    evidence = ControlEvidence(coverage, config, policy, incident, age)
    assert 0.0 <= evidence.effectiveness() <= 1.0


@SETTINGS
@given(
    low=UNIT,
    high=UNIT,
    config=UNIT,
    policy=UNIT,
    incident=UNIT,
    age=st.integers(0, 10_000),
)
def test_effectiveness_is_monotonic_in_coverage(
    low: float, high: float, config: float, policy: float, incident: float, age: int
) -> None:
    """More coverage must never mean less effectiveness."""
    assume(low <= high)
    weaker = ControlEvidence(low, config, policy, incident, age).effectiveness()
    stronger = ControlEvidence(high, config, policy, incident, age).effectiveness()
    assert stronger >= weaker - 1e-12


@SETTINGS
@given(low=UNIT, high=UNIT, coverage=UNIT, config=UNIT, policy=UNIT, age=st.integers(0, 5000))
def test_more_incidents_never_increase_effectiveness(
    low: float, high: float, coverage: float, config: float, policy: float, age: int
) -> None:
    assume(low <= high)
    fewer = ControlEvidence(coverage, config, policy, low, age).effectiveness()
    more = ControlEvidence(coverage, config, policy, high, age).effectiveness()
    assert more <= fewer + 1e-12


@SETTINGS
@given(recent=st.integers(0, 120), stale=st.integers(0, 120), coverage=UNIT)
def test_stale_evidence_never_increases_effectiveness(
    recent: int, stale: int, coverage: float
) -> None:
    """Evidence that has aged is weaker evidence."""
    assume(recent <= stale)
    fresh = ControlEvidence(coverage=coverage, verification_age_days=recent).effectiveness()
    old = ControlEvidence(coverage=coverage, verification_age_days=stale).effectiveness()
    assert old <= fresh + 1e-12


@given(
    coverage=st.one_of(
        st.floats(max_value=-1e-9, allow_nan=False, allow_infinity=False),
        st.floats(min_value=1.0 + 1e-9, max_value=1e9, allow_nan=False),
    )
)
def test_evidence_rejects_out_of_range_input(coverage: float) -> None:
    with pytest.raises(ValueError):
        ControlEvidence(coverage=coverage)


@SETTINGS
@given(effectiveness=UNIT, category=st.sampled_from(list(ControlCategory)))
def test_factor_effect_stays_in_its_declared_range(
    effectiveness: float, category: ControlCategory
) -> None:
    """A multiplier may not go negative and a percentile shift may not exceed 100."""
    effect = factor_effect(category, effectiveness)
    assert 0.0 <= effect.multiplier <= 1.0
    assert 0.0 <= effect.shift <= 100.0


def _frequency() -> FrequencyModel:
    return FrequencyModel(
        contact_frequency=Poisson(12.0),
        probability_of_action=BetaPert(0.1, 0.4, 0.9),
        threat_capability=BetaPert(20.0, 60.0, 95.0),
        resistance_strength=BetaPert(30.0, 55.0, 80.0),
    )


def _magnitude() -> MagnitudeModel:
    return MagnitudeModel(
        primary={"downtime": BetaPert(1e5, 5e5, 2e6)},
        secondary={"regulatory": BetaPert(0.0, 2e5, 1e6)},
        secondary_loss_event_frequency=BetaPert(0.05, 0.2, 0.5),
    )


@SETTINGS
@given(
    effectiveness=UNIT,
    category=st.sampled_from(list(ControlCategory)),
    seed=st.integers(0, 2**31 - 1),
)
def test_applying_a_control_never_increases_risk(
    effectiveness: float, category: ControlCategory, seed: int
) -> None:
    """Whatever the control and however strong it is, hardening must not raise the LEF.

    The tolerance is derived from the Monte Carlo standard error rather than set to a fixed
    epsilon. Vulnerability is estimated as the mean of ``n`` Bernoulli draws, so its own
    standard error is ``sqrt(p(1-p)/n)``; at n = 20,000 that is ~0.0035, which swamps the
    ~1e-4 effect of an effectiveness near zero. An absolute epsilon would therefore fail at
    random. This check cannot resolve effects smaller than its own noise — a real limit of
    the test, not a defective model (verified at n = 2,000,000: every category strictly
    decreases LEF).
    """
    n = 20_000
    before = _frequency().sample(np.random.default_rng(seed), n)
    frequency, _ = apply_control_effects(
        frequency=_frequency(),
        magnitude=_magnitude(),
        applications=[
            ControlApplication("FUZZ", category, effectiveness),
        ],
    )
    after = frequency.sample(np.random.default_rng(seed), n)

    mean_before = float(np.mean(before.lef))
    mean_after = float(np.mean(after.lef))
    standard_error = math.sqrt((float(np.var(before.lef)) + float(np.var(after.lef))) / n)

    assert mean_after <= mean_before + 6 * standard_error
    assert 0.0 <= after.vulnerability <= 1.0
    assert np.all(after.tef >= 0.0)


@SETTINGS
@given(effectiveness=UNIT, category=st.sampled_from(list(ControlCategory)))
def test_controlled_probability_of_action_never_exceeds_one(
    effectiveness: float, category: ControlCategory
) -> None:
    """Scaling a probability must respect the cap — no 1.4 probabilities."""
    frequency, _ = apply_control_effects(
        frequency=_frequency(),
        magnitude=_magnitude(),
        applications=[ControlApplication("FUZZ", category, effectiveness)],
    )
    samples = frequency.probability_of_action.sample(np.random.default_rng(5), 2000)
    assert np.all(samples <= 1.0 + 1e-9)
    assert np.all(samples >= 0.0)


@SETTINGS
@given(count=st.integers(0, 6), effectiveness=UNIT)
def test_many_resistive_controls_are_capped_at_full_resistance(
    count: int, effectiveness: float
) -> None:
    """Stacked resistive controls must saturate, never exceed the percentile maximum."""
    applications = [
        ControlApplication(f"R{i}", ControlCategory.RESISTIVE, effectiveness) for i in range(count)
    ]
    frequency, _ = apply_control_effects(
        frequency=_frequency(), magnitude=_magnitude(), applications=applications
    )
    samples = frequency.resistance_strength.sample(np.random.default_rng(6), 2000)
    assert np.all(samples <= 100.0 + 1e-9)
    assert np.all(samples >= 0.0)


# ---------------------------------------------------------------------------------------
# 3. Asset criticality
# ---------------------------------------------------------------------------------------
@SETTINGS
@given(scores=st.lists(DIMENSION_SCORES, min_size=6, max_size=6))
def test_criticality_score_and_fraction_are_bounded(scores: list[int]) -> None:
    profile = CriticalityProfile(**dict(zip(DIMENSIONS, scores, strict=True)))
    assert 1.0 <= profile.score <= 5.0
    assert 0.0 <= profile.fraction <= 1.0


@SETTINGS
@given(
    scores=st.lists(DIMENSION_SCORES, min_size=6, max_size=6), dimension=st.sampled_from(DIMENSIONS)
)
def test_raising_a_dimension_never_lowers_criticality(scores: list[int], dimension: str) -> None:
    """Monotonicity: more critical in any dimension must not reduce the score."""
    raiseable = scores[DIMENSIONS.index(dimension)] < 5
    assume(raiseable)
    values = dict(zip(DIMENSIONS, scores, strict=True))
    raised = dict(values)
    raised[dimension] += 1

    base = CriticalityProfile(**values)
    higher = CriticalityProfile(**raised)
    assert higher.score >= base.score - 1e-12


@SETTINGS
@given(scores=st.lists(DIMENSION_SCORES, min_size=6, max_size=6))
def test_criticality_band_agrees_with_score(scores: list[int]) -> None:
    profile = CriticalityProfile(**dict(zip(DIMENSIONS, scores, strict=True)))
    assert profile.band == criticality_band(profile.score)


@SETTINGS
@given(
    scores=st.lists(DIMENSION_SCORES, min_size=6, max_size=6),
    bad=st.one_of(st.integers(max_value=-1), st.integers(min_value=6)),
    position=st.integers(min_value=0, max_value=5),
)
def test_out_of_range_dimensions_are_rejected(scores: list[int], bad: int, position: int) -> None:
    """Values outside 0-5 must raise, never be silently clamped."""
    corrupted = list(scores)
    corrupted[position] = bad
    with pytest.raises(ValueError):
        CriticalityProfile(**dict(zip(DIMENSIONS, corrupted, strict=True)))


# ---------------------------------------------------------------------------------------
# 4. Frequency model invariants (the FAIR ordering constraint)
# ---------------------------------------------------------------------------------------
@SETTINGS
@given(seed=st.integers(0, 2**31 - 1), size=st.integers(1, 2000))
def test_lef_never_exceeds_tef(seed: int, size: int) -> None:
    """LEF = TEF × Vulnerability with V <= 1, so LEF <= TEF must always hold."""
    sample = _frequency().sample(np.random.default_rng(seed), size)
    assert np.all(sample.lef <= sample.tef + 1e-9)
    assert 0.0 <= sample.vulnerability <= 1.0


# ---------------------------------------------------------------------------------------
# 5. Monte Carlo summary
# ---------------------------------------------------------------------------------------
@SETTINGS
@given(
    losses=st.lists(
        st.floats(min_value=0.0, max_value=1e12, allow_nan=False), min_size=2, max_size=2000
    )
)
def test_percentiles_are_ordered_and_eal_is_bounded(losses: list[float]) -> None:
    """P50 <= P90 <= P95 <= P99, and the mean lies within the sampled range.

    The range check uses a relative tolerance: the mean of identical doubles can land one
    unit-in-the-last-place below them (``np.mean([x, x, x])`` at 7e11 differs from ``x`` by
    ~1e-4), which is floating-point summation behaviour rather than a modelling defect.
    """
    array = np.asarray(losses, dtype=float)
    summary = summarize(array, "INR")
    tolerance = 1e-9 * max(1.0, float(array.max()))

    assert summary.p50 <= summary.p90 <= summary.p95 <= summary.p99
    assert summary.eal >= 0.0
    assert summary.minimum - tolerance <= summary.eal <= summary.maximum + tolerance
    assert summary.cvar_95 >= summary.var_95 - tolerance


@SETTINGS
@given(
    losses=st.lists(
        st.floats(min_value=0.0, max_value=1e9, allow_nan=False), min_size=2, max_size=500
    )
)
def test_summary_is_finite_for_extreme_inputs(losses: list[float]) -> None:
    summary = summarize(np.asarray(losses, dtype=float), "INR")
    for value in (
        summary.eal,
        summary.p90,
        summary.p95,
        summary.p99,
        summary.var_95,
        summary.cvar_95,
    ):
        assert math.isfinite(value)


def test_simulation_is_reproducible_for_any_seed() -> None:
    """Same seed must reproduce the same distribution byte for byte."""
    scenario = _compiled_scenario()
    for seed in (0, 1, 42, 123_456, 2**31 - 1):
        first = run_simulation(scenario, SimulationConfig(n_trials=2000, seed=seed))
        second = run_simulation(scenario, SimulationConfig(n_trials=2000, seed=seed))
        assert np.array_equal(first.losses, second.losses), f"seed {seed} not reproducible"


# ---------------------------------------------------------------------------------------
# 6. Metrics
# ---------------------------------------------------------------------------------------
@SETTINGS
@given(before=FINITE, after=FINITE)
def test_risk_reduction_sign_convention(before: float, after: float) -> None:
    """Reduction is defined as before − after; it may legitimately be negative."""
    assume(math.isfinite(before) and math.isfinite(after))
    assert risk_reduction(before, after) == pytest.approx(before - after)


@SETTINGS
@given(before=FINITE, after=FINITE)
def test_percentage_metrics_are_finite_or_none(before: float, after: float) -> None:
    """Every ratio must be a finite number or None — never inf/nan.

    ``Infinity`` is not valid JSON, so an overflow here would corrupt a whole response.
    A denormal baseline overflowing the division is the case that actually triggered this.
    """
    assume(math.isfinite(before) and math.isfinite(after))

    pct = risk_reduction_pct(before, after)
    if before <= 0:
        assert pct is None
    elif pct is not None:
        assert math.isfinite(pct)

    for cost in (0.0, -5.0):
        assert rosi(before, after, cost) is None
        assert risk_removed_per_unit(before, after, cost) is None


@SETTINGS
@given(before=FINITE, after=FINITE, cost=SMALL_POSITIVE)
def test_ratio_metrics_never_overflow_to_infinity(before: float, after: float, cost: float) -> None:
    """A near-zero cost must yield None, not an unrepresentable ratio."""
    assume(math.isfinite(before) and math.isfinite(after))
    for value in (rosi(before, after, cost), risk_removed_per_unit(before, after, cost)):
        if value is not None:
            assert math.isfinite(value)


@given(years=st.floats(max_value=0.0, allow_nan=False, allow_infinity=False))
def test_annualize_rejects_non_positive_horizon(years: float) -> None:
    with pytest.raises(ValueError):
        annualize(1000.0, years)


# ---------------------------------------------------------------------------------------
# 7. Provenance & confidence
# ---------------------------------------------------------------------------------------
@SETTINGS
@given(counts=st.lists(st.integers(min_value=0, max_value=50), min_size=0, max_size=5))
def test_confidence_score_is_bounded_by_credibility_table(counts: list[int]) -> None:
    """The weighted average can never escape the min/max credibility of the sources used."""
    mix = EvidenceMix(dict(zip(list(SourceType), counts, strict=False)))
    score = mix.confidence_score
    assert 0.0 <= score <= 1.0
    if mix.total > 0:
        present = [SOURCE_CREDIBILITY[s] for s, c in mix.counts.items() if c > 0]
        assert min(present) - 1e-9 <= score <= max(present) + 1e-9


@SETTINGS
@given(counts=st.lists(st.integers(min_value=0, max_value=50), min_size=0, max_size=5))
def test_proportions_sum_to_one_when_non_empty(counts: list[int]) -> None:
    mix = EvidenceMix(dict(zip(list(SourceType), counts, strict=False)))
    proportions = mix.proportions
    if mix.total == 0:
        assert proportions == {}
    else:
        assert abs(sum(proportions.values()) - 1.0) < 1e-9


@SETTINGS
@given(score=st.floats(min_value=0.0, max_value=1.0))
def test_band_is_consistent_with_score(score: float) -> None:
    band = confidence_band(score)
    if score >= 0.75:
        assert band is ConfidenceBand.HIGH
    elif score >= 0.50:
        assert band is ConfidenceBand.MEDIUM
    else:
        assert band is ConfidenceBand.LOW


@given(
    confidence=st.one_of(
        st.floats(max_value=-1e-9, allow_nan=False, allow_infinity=False),
        st.floats(min_value=1.0 + 1e-9, max_value=1e9, allow_nan=False),
    )
)
def test_provenance_rejects_out_of_range_confidence(confidence: float) -> None:
    with pytest.raises(ValueError):
        Provenance(source_type=SourceType.PUBLIC_DATA, source="fuzz", confidence=confidence)


# ---------------------------------------------------------------------------------------
# 8. HTTP surface — malformed input must never produce a 500
# ---------------------------------------------------------------------------------------
client = TestClient(app, raise_server_exceptions=False)

# Lone surrogates (Unicode category Cs) are excluded: they cannot be UTF-8 encoded, so the
# request would fail inside the test client before reaching the app. That is a harness
# limitation, not something the API could receive over real HTTP.
_SAFE_CHARS = st.characters(blacklist_categories=["Cs"])

NASTY_TEXT = st.one_of(
    st.text(alphabet=_SAFE_CHARS, max_size=200),
    st.text(alphabet="\x00\u200b\ufeff'\"\\;--<>", max_size=60),
    st.just("' OR 1=1 --"),
    st.just("../../etc/passwd"),
    st.just("%s%s%s%n"),
    st.just("x" * 5000),
    st.just("\x00\x00\x00"),
    st.just("\\u0000"),
)

NASTY_NUMBER = st.one_of(
    st.floats(allow_nan=False, allow_infinity=False),
    st.floats(min_value=-1e18, max_value=-1e-9),
    st.integers(min_value=-(2**63), max_value=2**63 - 1),
    st.just(0),
    st.just(10**30),
)


@SETTINGS
@given(
    payload=st.recursive(
        st.none() | st.booleans() | NASTY_NUMBER | NASTY_TEXT,
        lambda children: (
            st.lists(children, max_size=4) | st.dictionaries(NASTY_TEXT, children, max_size=4)
        ),
        max_leaves=8,
    )
)
def test_optimize_never_returns_5xx(payload: object) -> None:
    """Whatever the body, the endpoint must answer 4xx or 2xx — never crash."""
    response = client.post("/api/v1/optimize", json=payload)
    assert response.status_code < 500, f"5xx on payload {payload!r}: {response.text[:200]}"


@SETTINGS
@given(budget=NASTY_NUMBER, trials=NASTY_NUMBER, seed=NASTY_NUMBER)
def test_optimize_number_surface_never_returns_5xx(
    budget: object, trials: object, seed: object
) -> None:
    response = client.post(
        "/api/v1/optimize", json={"budget": budget, "n_trials": trials, "seed": seed}
    )
    assert response.status_code < 500, f"5xx for budget={budget!r}: {response.text[:200]}"


@SETTINGS
@given(path=NASTY_TEXT, trials=st.one_of(st.just(0), NASTY_NUMBER))
def test_simulate_unknown_scenario_is_never_5xx(path: str, trials: object) -> None:
    """A malformed or unknown scenario id must be a clean 4xx.

    The path is percent-encoded, which is what a real client would do — a raw control
    character cannot appear in a URL at all (httpx rejects it before the request is sent),
    so an unencoded fuzz input would test the client rather than the server.
    """
    encoded = quote(path, safe="")
    assume("/" not in encoded)
    response = client.post(f"/api/v1/scenarios/{encoded}/simulate", json={"n_trials": trials})
    assert response.status_code < 500, f"5xx for id {path!r}: {response.text[:200]}"


@SETTINGS
@given(question=NASTY_TEXT)
def test_ask_never_returns_5xx(question: str) -> None:
    response = client.post("/api/v1/ask", json={"question": question})
    assert response.status_code < 500, f"5xx for question {question[:40]!r}: {response.text[:200]}"


@SETTINGS
@given(overrides=st.dictionaries(NASTY_TEXT, NASTY_NUMBER, max_size=4))
def test_criticality_overrides_never_return_5xx(overrides: dict) -> None:
    response = client.post(
        "/api/v1/what-if/scenarios/SCN-THIRD-01/criticality",
        json={"n_trials": 1000, "overrides": overrides},
    )
    assert response.status_code < 500, f"5xx for overrides {overrides!r}: {response.text[:200]}"


@SETTINGS
@given(
    body=st.one_of(
        st.text(max_size=300),
        st.binary(max_size=100).map(lambda b: b.decode("latin-1")),
    )
)
def test_malformed_json_body_never_returns_5xx(body: str) -> None:
    """Truncated or non-JSON bodies must be 4xx, not a stack trace."""
    response = client.post(
        "/api/v1/optimize", content=body, headers={"content-type": "application/json"}
    )
    assert response.status_code < 500, f"5xx on body {body[:60]!r}: {response.text[:200]}"


@SETTINGS
@given(name=NASTY_TEXT)
def test_ai_status_and_tools_are_stable(name: str) -> None:
    """Read-only GETs must never depend on prior state."""
    assert client.get("/api/v1/ai/status").status_code < 500
    assert client.get("/api/v1/ai/tools").status_code < 500


# ---------------------------------------------------------------------------------------
# helper: a compiled scenario for the determinism check
# ---------------------------------------------------------------------------------------
def _compiled_scenario():
    from app.optimization.context import load_planning_context

    context = load_planning_context()
    return next(iter(context.scenarios.values()))
