"""Pydantic v2 request/response models for the public API.

Responses are deliberately *summarised*: the API returns binned histograms, percentiles and
exceedance curves, never the raw Monte Carlo path array. Each simulation response also
carries its seed, trial count, model version and evidence mix so any figure shown in the UI
can be traced back to the run that produced it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.optimization.harness import PortfolioOutcome
from app.risk.monte_carlo import DEFAULT_SEED, DEFAULT_TRIALS


# --- shared building blocks --------------------------------------------------------------
class Histogram(BaseModel):
    bins: list[float] = Field(description="Bin edges, length = counts + 1")
    counts: list[int] = Field(description="Observation count per bin")


class ExceedanceCurve(BaseModel):
    loss: list[float] = Field(description="Loss thresholds, ascending")
    probability: list[float] = Field(description="P(loss > threshold)")


class LossSummaryModel(BaseModel):
    currency: str
    eal: float = Field(description="Expected annual loss (mean of the distribution)")
    median: float
    p50: float
    p90: float
    p95: float
    p99: float
    var_95: float = Field(description="Value at Risk at 95% (the p95 loss)")
    cvar_95: float = Field(description="Mean loss at or above VaR95")
    min: float
    max: float


class FrequencySummary(BaseModel):
    mean_tef: float
    vulnerability: float
    mean_lef: float


class SimulationMeta(BaseModel):
    n_trials: int
    seed: int
    model_version: str
    library_versions: dict[str, str]


class EvidenceMixModel(BaseModel):
    proportions: dict[str, float]
    confidence_score: float
    band: str
    counts: dict[str, int]


class SimulationResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    asset_id: str | None
    business_service: str | None
    summary: LossSummaryModel
    frequency: FrequencySummary
    simulation: SimulationMeta
    evidence_mix: EvidenceMixModel
    histogram: Histogram
    loss_exceedance: ExceedanceCurve


class ScenarioOutcomeModel(BaseModel):
    scenario_id: str
    name: str
    eal: float
    p90: float
    p95: float


class PortfolioOutcomeModel(BaseModel):
    label: str
    selection: list[str]
    spend: float
    annualized_cost: float
    currency: str
    baseline_eal: float
    eal: float
    p90: float
    p95: float
    risk_reduction: float
    risk_reduction_pct: float | None = Field(
        default=None, description="Reduction as a percentage (0-100), not a fraction"
    )
    rosi: float | None
    risk_removed_per_rupee: float | None
    n_scenarios: int
    n_trials: int
    seed: int
    scenarios: list[ScenarioOutcomeModel]

    @classmethod
    def from_outcome(cls, outcome: PortfolioOutcome) -> PortfolioOutcomeModel:
        payload = outcome.to_dict()
        fraction = payload["risk_reduction_pct"]
        payload["risk_reduction_pct"] = None if fraction is None else round(fraction * 100, 2)
        return cls(**payload)


# --- catalog ----------------------------------------------------------------------------
class OrganizationModel(BaseModel):
    id: str
    name: str
    sector: str | None
    currency: str
    description: str | None
    framework_scope: list[str]


class CriticalityModel(BaseModel):
    dimensions: dict[str, int]
    score: float
    band: str
    weights: dict[str, float]


class AssetSummary(BaseModel):
    asset_id: str
    name: str
    category: str
    service_id: str | None
    service_name: str | None
    business_unit: str | None
    owner: str | None
    internet_exposed: bool
    criticality: CriticalityModel
    finding_count: int
    scenario_count: int
    tags: list[str]


class FindingSummary(BaseModel):
    finding_id: str
    asset_id: str
    asset_name: str
    cve_id: str | None
    title: str | None
    source: str
    raw_severity: str | None
    status: str
    cvss_base_score: float | None
    cvss_severity: str | None
    epss: float | None
    kev: bool
    kev_ransomware: bool


class ControlFactorModel(BaseModel):
    factor: str
    multiplier: float
    shift: float
    description: str


class ControlSummary(BaseModel):
    control_id: str
    name: str
    category: str
    effectiveness: float
    cost: float
    evidence: dict[str, float | int | None]
    protects: list[str]
    factor: ControlFactorModel


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str | None
    asset_id: str | None
    asset_name: str | None
    service_id: str | None
    category: str | None
    cve_ids: list[str]
    attack_techniques: list[str]
    max_cvss: float | None
    max_epss: float | None
    baseline_eal: float | None = Field(
        default=None, description="Current-posture expected annual loss for this scenario"
    )
    baseline_p90: float | None = None
    baseline_p95: float | None = None


class AssetDetail(BaseModel):
    asset: AssetSummary
    findings: list[FindingSummary]
    scenarios: list[ScenarioSummary]


class ScenarioSpecResponse(BaseModel):
    """The full compiled scenario specification, including per-parameter provenance."""

    id: str
    name: str
    description: str | None
    asset_id: str | None
    currency: str
    cve_ids: list[str]
    attack_techniques: list[str]
    frequency: dict[str, object]
    magnitude: dict[str, object]


class CandidateModel(BaseModel):
    id: str
    name: str
    control_id: str
    category: str
    cost: float
    annualized_cost: float
    current_effectiveness: float
    target_effectiveness: float
    effectiveness_gain: float
    scenarios: list[str]
    prerequisites: list[str]
    mandatory: bool
    implementation_days: int | None
    operational_impact: str | None


# --- overview ---------------------------------------------------------------------------
class PostureModel(BaseModel):
    baseline_eal: float
    p90: float
    p95: float
    currency: str
    n_scenarios: int
    n_trials: int
    seed: int


class OverviewResponse(BaseModel):
    organization: OrganizationModel
    counts: dict[str, int]
    criticality_bands: dict[str, int]
    posture: PostureModel
    evidence_mix: EvidenceMixModel
    model_version: str


# --- compliance -------------------------------------------------------------------------
class FrameworkModel(BaseModel):
    id: str
    name: str
    short_name: str
    version: str
    kind: str
    publisher: str
    published: str
    source_url: str
    note: str | None


class ControlContributionModel(BaseModel):
    control_id: str
    name: str
    effectiveness: float
    category: str


class RequirementCoverageModel(BaseModel):
    id: str
    name: str
    objective: str
    function: str
    categories: list[str]
    references: list[str] = Field(description="Framework-native clauses this maps to")
    coverage: float
    status: str
    controls: list[ControlContributionModel]
    scenarios: list[str]
    exposure: float = Field(description="Modelled annual loss sitting in the related scenarios")
    closable_by: list[str] = Field(description="Investment candidates that would raise coverage")
    note: str | None


class FunctionCoverageModel(BaseModel):
    function: str
    coverage: float
    requirements: int
    gaps: int


class FrameworkCoverageModel(BaseModel):
    framework: FrameworkModel
    coverage: float
    counts: dict[str, int]
    gap_exposure: float
    functions: list[FunctionCoverageModel]
    requirements: list[RequirementCoverageModel]


class ComplianceReportModel(BaseModel):
    organization: str
    currency: str
    catalog_version: str
    overall_coverage: float
    frameworks: list[FrameworkCoverageModel]
    top_gaps: list[RequirementCoverageModel]
    unmapped_controls: list[str]
    unmapped_requirements: list[str]


class RequirementModel(BaseModel):
    """A canonical requirement in the internal ontology, with all its framework refs."""

    id: str
    name: str
    objective: str
    function: str
    categories: list[str]
    references: dict[str, list[str]]
    note: str | None
    controls: list[str]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class ToolCallModel(BaseModel):
    name: str
    arguments: dict[str, object]
    ok: bool
    result: dict[str, object]


class GroundingModel(BaseModel):
    grounded: bool
    unverified_numbers: list[str]
    note: str


class AskResponse(BaseModel):
    question: str
    answer: str
    provider: str
    model: str
    steps: int
    tool_calls: list[ToolCallModel]
    grounding: GroundingModel
    degraded: bool = Field(description="True when the deterministic engine answered")
    reason: str | None
    available_providers: list[str]


class AiToolModel(BaseModel):
    name: str
    description: str
    parameters: dict[str, object]


class AiStatusResponse(BaseModel):
    enabled: bool
    providers: list[dict[str, object]]
    active: list[str]
    fallback: str
    max_steps: int


# --- requests ---------------------------------------------------------------------------
class _RunParams(BaseModel):
    n_trials: int = Field(default=DEFAULT_TRIALS, ge=100, le=500_000)
    seed: int = Field(default=DEFAULT_SEED, ge=0)


# CP-SAT works in int64 and the objective is scaled by MONEY_SCALE (100), so a budget above
# roughly 9.2e16 overflows the solver's coefficient range and raises a TypeError. Rejecting
# it here turns a 500 into a clean 422. The cap is ~100x India's total annual IT security
# spend, so it cannot bite a real user.
MAX_BUDGET = 1e15


class SimulateRequest(_RunParams):
    controls: list[str] = Field(default_factory=list, description="Investment candidate ids")


class OptimizeRequest(_RunParams):
    budget: float = Field(
        gt=0,
        le=MAX_BUDGET,
        description="Total security budget in the organization currency",
    )


class DelayRequest(SimulateRequest):
    days: int = Field(default=30, ge=0, le=3650)


class CriticalityRequest(_RunParams):
    overrides: dict[str, int] = Field(
        description="Criticality dimensions to override (0-5 each)",
        json_schema_extra={"example": {"availability": 5, "confidentiality": 4}},
    )


# --- optimize / what-if responses --------------------------------------------------------
class OptimizationResultModel(BaseModel):
    selection: list[str]
    status: str
    surrogate_objective: float
    spend: float
    solver: str


class OptimizationResponse(BaseModel):
    budget: float
    currency: str
    result: OptimizationResultModel
    comparison: list[PortfolioOutcomeModel]
    best_strategy: str
    explanation: list[dict[str, object]]


class DelayImpactResponse(BaseModel):
    scenario_id: str
    days: int
    window_years: float
    selection: list[str]
    loss_if_delayed: float
    loss_if_remediated_now: float
    avoidable_loss: float
    baseline_eal: float
    hardened_eal: float
    currency: str
    method: str


class CriticalityImpactResponse(BaseModel):
    scenario_id: str
    asset_id: str
    before: CriticalityModel
    after: CriticalityModel
    eal_before: float
    eal_after: float
    eal_delta: float
    p95_before: float
    p95_after: float
    currency: str
