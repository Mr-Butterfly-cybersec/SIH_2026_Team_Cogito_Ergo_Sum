"""Mapping from the organization's controls to the canonical requirement ontology.

This is the join that makes the ontology useful: every implemented control declares which
canonical requirements it contributes to, and the reverse index is derived from it. A
control that maps to no requirement is a control we are paying for without a compliance
story; a requirement with no control is a gap.
"""

from __future__ import annotations

from app.compliance.catalog import REQUIREMENTS_BY_ID

#: Which canonical requirements each control contributes evidence toward.
CONTROL_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "CTL-MFA-PRIV": ("REQ-IDENTITY-MFA", "REQ-PRIVILEGED-ACCESS", "REQ-ACCOUNT-MGMT"),
    "CTL-MFA-ALL": ("REQ-IDENTITY-MFA", "REQ-ACCOUNT-MGMT"),
    "CTL-PAM": ("REQ-PRIVILEGED-ACCESS", "REQ-ACCOUNT-MGMT", "REQ-LOG-MGMT"),
    "CTL-PATCH": ("REQ-VULN-MGMT", "REQ-PATCH-MGMT", "REQ-HARDENING"),
    "CTL-EDR": (
        "REQ-ENDPOINT-PROTECTION",
        "REQ-CONTINUOUS-MONITORING",
        "REQ-INCIDENT-RESPONSE",
        # Detection is a genuine precondition for breach notification, and endpoint telemetry
        # is part of what an AI-system security review would cover.
        "REQ-DPDP-BREACH",
        "REQ-AI-SECURITY",
    ),
    "CTL-SEG": ("REQ-NETWORK-SEGMENTATION", "REQ-RESILIENCE-BCP"),
    "CTL-WAF": ("REQ-APPLICATION-SECURITY", "REQ-NETWORK-DEFENCE", "REQ-AI-SECURITY"),
    "CTL-BACKUP": ("REQ-BACKUP-RECOVERY", "REQ-RESILIENCE-BCP"),
    "CTL-SIEM": (
        "REQ-LOG-MGMT",
        "REQ-CONTINUOUS-MONITORING",
        "REQ-INCIDENT-RESPONSE",
        "REQ-DPDP-BREACH",
        "REQ-AI-MONITORING",
    ),
    "CTL-EMAIL": ("REQ-EMAIL-PROTECTION",),
    "CTL-CSPM": (
        "REQ-CLOUD-SECURITY",
        "REQ-HARDENING",
        "REQ-DATA-PROTECTION",
        # Cloud posture management covers the storage and configuration holding AI data.
        "REQ-AI-DATA",
    ),
}


def _build_reverse_index() -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = {requirement_id: [] for requirement_id in REQUIREMENTS_BY_ID}
    for control_id, requirement_ids in CONTROL_REQUIREMENTS.items():
        for requirement_id in requirement_ids:
            index.setdefault(requirement_id, []).append(control_id)
    return {requirement_id: tuple(sorted(controls)) for requirement_id, controls in index.items()}


#: requirement id -> control ids that contribute to it
REQUIREMENT_CONTROLS: dict[str, tuple[str, ...]] = _build_reverse_index()


def requirements_for_control(control_id: str) -> tuple[str, ...]:
    return CONTROL_REQUIREMENTS.get(control_id, ())


def controls_for_requirement(requirement_id: str) -> tuple[str, ...]:
    return REQUIREMENT_CONTROLS.get(requirement_id, ())


def unmapped_controls(control_ids: list[str]) -> tuple[str, ...]:
    """Controls that contribute to no canonical requirement."""
    return tuple(sorted(cid for cid in control_ids if cid not in CONTROL_REQUIREMENTS))


def unmapped_requirements() -> tuple[str, ...]:
    """Canonical requirements that no configured control contributes to."""
    return tuple(
        sorted(
            requirement_id
            for requirement_id, controls in REQUIREMENT_CONTROLS.items()
            if not controls
        )
    )


__all__ = [
    "CONTROL_REQUIREMENTS",
    "REQUIREMENT_CONTROLS",
    "controls_for_requirement",
    "requirements_for_control",
    "unmapped_controls",
    "unmapped_requirements",
]
