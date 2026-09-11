"""Investment candidates: the remediation options the optimizer chooses between.

A candidate is "raise control X to its target effectiveness". Selecting it applies that
control at the target effectiveness in the evaluation harness instead of its current
measured effectiveness.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.optimization.context import PlanningContext
from app.risk.control_effect import ControlCategory

TARGET_EFFECTIVENESS = 0.85
AMORTIZATION_YEARS = 3.0

# Prerequisites between controls. In a production system this belongs in the control
# catalogue; here it is a small, documented configuration.
PREREQUISITES: dict[str, tuple[str, ...]] = {
    "CTL-MFA-ALL": ("CTL-MFA-PRIV",),
    "CTL-PAM": ("CTL-MFA-PRIV",),
    "CTL-CSPM": ("CTL-SIEM",),
    "CTL-SEG": ("CTL-EDR",),
}

IMPLEMENTATION_DAYS: dict[str, int] = {
    "CTL-MFA-PRIV": 45,
    "CTL-MFA-ALL": 90,
    "CTL-EDR": 60,
    "CTL-PATCH": 120,
    "CTL-SEG": 150,
    "CTL-WAF": 45,
    "CTL-BACKUP": 75,
    "CTL-SIEM": 120,
    "CTL-EMAIL": 30,
    "CTL-PAM": 90,
    "CTL-CSPM": 60,
}

OPERATIONAL_IMPACT: dict[str, str] = {
    "CTL-MFA-PRIV": "Sign-in friction for privileged users only",
    "CTL-MFA-ALL": "Sign-in friction for all staff and students",
    "CTL-EDR": "Endpoint agent overhead",
    "CTL-PATCH": "Maintenance windows and reboots",
    "CTL-SEG": "Firewall rule changes across critical tiers",
    "CTL-WAF": "Possible false positives on web forms",
    "CTL-BACKUP": "Storage cost and backup window",
    "CTL-SIEM": "Log ingestion volume and tuning effort",
    "CTL-EMAIL": "Quarantine tuning",
    "CTL-PAM": "Vaulting and session-broker rollout",
    "CTL-CSPM": "Cloud policy remediation",
}

# Controls that must be funded regardless of optimization outcome.
MANDATORY_CONTROLS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Candidate:
    id: str
    name: str
    control_id: str
    category: ControlCategory
    cost: float
    current_effectiveness: float
    target_effectiveness: float
    scenarios: tuple[str, ...]
    prerequisites: tuple[str, ...] = ()
    mandatory: bool = False
    implementation_days: int | None = None
    operational_impact: str | None = None

    @property
    def annualized_cost(self) -> float:
        return self.cost / AMORTIZATION_YEARS

    @property
    def effectiveness_gain(self) -> float:
        return self.target_effectiveness - self.current_effectiveness

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "control_id": self.control_id,
            "category": self.category.value,
            "cost": self.cost,
            "annualized_cost": round(self.annualized_cost, 2),
            "current_effectiveness": round(self.current_effectiveness, 4),
            "target_effectiveness": self.target_effectiveness,
            "effectiveness_gain": round(self.effectiveness_gain, 4),
            "scenarios": list(self.scenarios),
            "prerequisites": list(self.prerequisites),
            "mandatory": self.mandatory,
            "implementation_days": self.implementation_days,
            "operational_impact": self.operational_impact,
        }


def candidate_id_for(control_id: str) -> str:
    return f"INV-{control_id}"


def candidates_from_context(
    context: PlanningContext,
    *,
    target_effectiveness: float = TARGET_EFFECTIVENESS,
) -> list[Candidate]:
    """Build one investment candidate per control that has headroom and protects a scenario."""
    candidates: list[Candidate] = []
    for control in context.controls.values():
        if not control.protects:
            continue
        if control.effectiveness >= target_effectiveness:
            continue
        prerequisites = tuple(
            candidate_id_for(required)
            for required in PREREQUISITES.get(control.control_id, ())
            if required in context.controls
        )
        candidates.append(
            Candidate(
                id=candidate_id_for(control.control_id),
                name=f"Raise '{control.name}' to target effectiveness",
                control_id=control.control_id,
                category=control.category,
                cost=control.cost,
                current_effectiveness=control.effectiveness,
                target_effectiveness=target_effectiveness,
                scenarios=control.protects,
                prerequisites=prerequisites,
                mandatory=control.control_id in MANDATORY_CONTROLS,
                implementation_days=IMPLEMENTATION_DAYS.get(control.control_id),
                operational_impact=OPERATIONAL_IMPACT.get(control.control_id),
            )
        )
    return candidates


def candidates_by_id(candidates: list[Candidate]) -> dict[str, Candidate]:
    return {candidate.id: candidate for candidate in candidates}
