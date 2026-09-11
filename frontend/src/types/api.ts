export interface Health {
  status: string;
  app: string;
  version: string;
  environment: string;
}

export interface DbHealth {
  database: string;
}

export interface Organization {
  id: string;
  name: string;
  sector: string | null;
  currency: string;
  description: string | null;
  framework_scope: string[];
}

export interface Criticality {
  dimensions: Record<string, number>;
  score: number;
  band: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  weights: Record<string, number>;
}

export interface Posture {
  baseline_eal: number;
  p90: number;
  p95: number;
  currency: string;
  n_scenarios: number;
  n_trials: number;
  seed: number;
}

export interface EvidenceMix {
  proportions: Record<string, number>;
  confidence_score: number;
  band: "HIGH" | "MEDIUM" | "LOW";
  counts: Record<string, number>;
}

export interface Overview {
  organization: Organization;
  counts: Record<string, number>;
  criticality_bands: Record<string, number>;
  posture: Posture;
  evidence_mix: EvidenceMix;
  model_version: string;
}

export interface AssetSummary {
  asset_id: string;
  name: string;
  category: string;
  service_id: string | null;
  service_name: string | null;
  business_unit: string | null;
  owner: string | null;
  internet_exposed: boolean;
  criticality: Criticality;
  finding_count: number;
  scenario_count: number;
  tags: string[];
}

export interface FindingSummary {
  finding_id: string;
  asset_id: string;
  asset_name: string;
  cve_id: string | null;
  title: string | null;
  source: string;
  raw_severity: string | null;
  status: string;
  cvss_base_score: number | null;
  cvss_severity: string | null;
  epss: number | null;
  kev: boolean;
  kev_ransomware: boolean;
}

export interface ControlSummary {
  control_id: string;
  name: string;
  category: string;
  effectiveness: number;
  cost: number;
  evidence: Record<string, number | null>;
  protects: string[];
  factor: {
    factor: string;
    multiplier: number;
    shift: number;
    description: string;
  };
}

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string | null;
  asset_id: string | null;
  asset_name: string | null;
  service_id: string | null;
  category: string | null;
  cve_ids: string[];
  attack_techniques: string[];
  max_cvss: number | null;
  max_epss: number | null;
  baseline_eal: number | null;
  baseline_p90: number | null;
  baseline_p95: number | null;
}

export interface LossSummary {
  currency: string;
  eal: number;
  median: number;
  p50: number;
  p90: number;
  p95: number;
  p99: number;
  var_95: number;
  cvar_95: number;
  min: number;
  max: number;
}

export interface Histogram {
  bins: number[];
  counts: number[];
}

export interface ExceedanceCurve {
  loss: number[];
  probability: number[];
}

export interface SimulationResponse {
  scenario_id: string;
  scenario_name: string;
  asset_id: string | null;
  business_service: string | null;
  summary: LossSummary;
  frequency: { mean_tef: number; vulnerability: number; mean_lef: number };
  simulation: {
    n_trials: number;
    seed: number;
    model_version: string;
    library_versions: Record<string, string>;
  };
  evidence_mix: EvidenceMix;
  histogram: Histogram;
  loss_exceedance: ExceedanceCurve;
}

export interface Candidate {
  id: string;
  name: string;
  control_id: string;
  category: string;
  cost: number;
  annualized_cost: number;
  current_effectiveness: number;
  target_effectiveness: number;
  effectiveness_gain: number;
  scenarios: string[];
  prerequisites: string[];
  mandatory: boolean;
  implementation_days: number | null;
  operational_impact: string | null;
}

export interface PortfolioOutcome {
  label: string;
  selection: string[];
  spend: number;
  annualized_cost: number;
  currency: string;
  baseline_eal: number;
  eal: number;
  p90: number;
  p95: number;
  risk_reduction: number;
  risk_reduction_pct: number | null;
  rosi: number | null;
  risk_removed_per_rupee: number | null;
  n_scenarios: number;
  n_trials: number;
  seed: number;
  scenarios: {
    scenario_id: string;
    name: string;
    eal: number;
    p90: number;
    p95: number;
  }[];
}

export interface OptimizationResponse {
  budget: number;
  currency: string;
  result: {
    selection: string[];
    status: string;
    surrogate_objective: number;
    spend: number;
    solver: string;
  };
  comparison: PortfolioOutcome[];
  best_strategy: string;
  explanation: {
    candidate_id: string;
    control_id: string;
    name: string;
    category: string;
    factor: string;
    factor_effect: string;
    scenarios: string[];
    scenario_count: number;
    standalone_reduction: number;
    cost: number;
    annualized_cost: number;
    risk_removed_per_rupee: number | null;
    prerequisites: string[];
    implementation_days: number | null;
    operational_impact: string | null;
    chain: string[];
  }[];
}

export interface RunParams {
  n_trials?: number;
  seed?: number;
}

// --- compliance --------------------------------------------------------------------------
export interface Framework {
  id: string;
  name: string;
  short_name: string;
  version: string;
  kind: "standard" | "regulation";
  publisher: string;
  published: string;
  source_url: string;
  note: string | null;
}

export interface ControlContribution {
  control_id: string;
  name: string;
  effectiveness: number;
  category: string;
}

export type CoverageStatus = "COVERED" | "PARTIAL" | "GAP" | "NOT_APPLICABLE";

export interface RequirementCoverage {
  id: string;
  name: string;
  objective: string;
  function: string;
  categories: string[];
  references: string[];
  coverage: number;
  status: CoverageStatus;
  controls: ControlContribution[];
  scenarios: string[];
  exposure: number;
  closable_by: string[];
  note: string | null;
}

export interface FunctionCoverage {
  function: string;
  coverage: number;
  requirements: number;
  gaps: number;
}

export interface FrameworkCoverage {
  framework: Framework;
  coverage: number;
  counts: { covered: number; partial: number; gaps: number; requirements: number };
  gap_exposure: number;
  functions: FunctionCoverage[];
  requirements: RequirementCoverage[];
}

export interface ComplianceReport {
  organization: string;
  currency: string;
  catalog_version: string;
  overall_coverage: number;
  frameworks: FrameworkCoverage[];
  top_gaps: RequirementCoverage[];
  unmapped_controls: string[];
  unmapped_requirements: string[];
}
