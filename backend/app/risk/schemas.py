"""Declarative scenario schemas (Pydantic v2) and compilation to the risk core.

A scenario JSON describes each FAIR factor as a distribution plus its provenance.
``ScenarioSpec.compile()`` turns it into a :class:`CompiledScenario` ready for simulation.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.risk.distributions import BetaPert, Constant, Lognormal
from app.risk.frequency import FrequencyModel
from app.risk.magnitude import (
    PRIMARY_COMPONENTS,
    SECONDARY_COMPONENTS,
    MagnitudeModel,
)
from app.risk.monte_carlo import (
    DEFAULT_SEED,
    DEFAULT_TRIALS,
    CompiledScenario,
    ScenarioResult,
    SimulationConfig,
    run_simulation,
)
from app.risk.provenance import MODEL_VERSION, Provenance, SourceType


class PertSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["pert"] = "pert"
    minimum: float
    mode: float
    maximum: float
    weight: float = 4.0

    @model_validator(mode="after")
    def _validate_range(self) -> PertSpec:
        if not (self.minimum <= self.mode <= self.maximum):
            raise ValueError("require minimum <= mode <= maximum")
        if self.weight <= 0:
            raise ValueError("weight must be positive")
        return self

    def build(self) -> BetaPert:
        return BetaPert(
            minimum=self.minimum,
            mode=self.mode,
            maximum=self.maximum,
            weight=self.weight,
        )


class LognormalSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["lognormal"] = "lognormal"
    mu: float
    sigma: float

    def build(self) -> Lognormal:
        return Lognormal(mu=self.mu, sigma=self.sigma)


class ConstantSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["constant"] = "constant"
    value: float

    def build(self) -> Constant:
        return Constant(value=self.value)


DistributionSpecModel = Annotated[
    PertSpec | LognormalSpec | ConstantSpec, Field(discriminator="kind")
]


class ProvenanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    source: str
    source_date: date | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    assumption_description: str | None = None
    model_version: str = MODEL_VERSION

    def build(self) -> Provenance:
        return Provenance(
            source_type=self.source_type,
            source=self.source,
            source_date=self.source_date,
            confidence=self.confidence,
            assumption_description=self.assumption_description,
            model_version=self.model_version,
        )


class Parameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distribution: DistributionSpecModel
    provenance: ProvenanceModel


class FrequencyModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_frequency: Parameter
    probability_of_action: Parameter
    threat_capability: Parameter
    resistance_strength: Parameter

    def iter_parameters(self) -> Iterator[Parameter]:
        yield from (
            self.contact_frequency,
            self.probability_of_action,
            self.threat_capability,
            self.resistance_strength,
        )

    def build(self) -> FrequencyModel:
        return FrequencyModel(
            contact_frequency=self.contact_frequency.distribution.build(),
            probability_of_action=self.probability_of_action.distribution.build(),
            threat_capability=self.threat_capability.distribution.build(),
            resistance_strength=self.resistance_strength.distribution.build(),
        )


def _validate_component_keys(
    components: dict[str, Parameter], allowed: tuple[str, ...], label: str
) -> None:
    if not components:
        raise ValueError(f"{label} loss must have at least one component")
    unknown = set(components) - set(allowed)
    if unknown:
        raise ValueError(f"unknown {label} loss components: {sorted(unknown)}")


class MagnitudeModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: dict[str, Parameter]
    secondary: dict[str, Parameter]
    secondary_loss_event_frequency: Parameter

    @model_validator(mode="after")
    def _validate_components(self) -> MagnitudeModelSpec:
        _validate_component_keys(self.primary, PRIMARY_COMPONENTS, "primary")
        _validate_component_keys(self.secondary, SECONDARY_COMPONENTS, "secondary")
        return self

    def iter_parameters(self) -> Iterator[Parameter]:
        yield from self.primary.values()
        yield from self.secondary.values()
        yield self.secondary_loss_event_frequency

    def build(self) -> MagnitudeModel:
        return MagnitudeModel(
            primary={name: p.distribution.build() for name, p in self.primary.items()},
            secondary={name: p.distribution.build() for name, p in self.secondary.items()},
            secondary_loss_event_frequency=self.secondary_loss_event_frequency.distribution.build(),
        )


class ScenarioSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str | None = None
    asset_id: str | None = None
    business_service: str | None = None
    currency: str = "INR"
    cve_ids: list[str] = Field(default_factory=list)
    attack_techniques: list[str] = Field(default_factory=list)
    frequency: FrequencyModelSpec
    magnitude: MagnitudeModelSpec

    def iter_parameters(self) -> Iterator[Parameter]:
        yield from self.frequency.iter_parameters()
        yield from self.magnitude.iter_parameters()

    def provenances(self) -> list[Provenance]:
        return [p.provenance.build() for p in self.iter_parameters()]

    def compile(self) -> CompiledScenario:
        return CompiledScenario(
            id=self.id,
            name=self.name,
            currency=self.currency,
            asset_id=self.asset_id,
            business_service=self.business_service,
            cve_ids=tuple(self.cve_ids),
            attack_techniques=tuple(self.attack_techniques),
            frequency=self.frequency.build(),
            magnitude=self.magnitude.build(),
            provenances=self.provenances(),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> ScenarioSpec:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_json(cls, text: str) -> ScenarioSpec:
        return cls.model_validate(json.loads(text))


def load_scenario(path: str | Path) -> ScenarioSpec:
    return ScenarioSpec.from_json_file(path)


def simulate(
    scenario: ScenarioSpec,
    *,
    n_trials: int = DEFAULT_TRIALS,
    seed: int = DEFAULT_SEED,
) -> ScenarioResult:
    """Compile and simulate a scenario in one call."""
    config = SimulationConfig(n_trials=n_trials, seed=seed)
    return run_simulation(scenario.compile(), config)
