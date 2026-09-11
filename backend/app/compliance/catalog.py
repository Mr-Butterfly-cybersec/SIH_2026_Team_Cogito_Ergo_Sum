"""The internal control ontology.

**One internal ontology, not a module per framework.** Each canonical requirement is
defined once and carries its references into every framework we support, so adding a
framework is a data change rather than a new module.

Every requirement also declares which FAIR control categories typically satisfy it
(``categories``). That is what lets the platform answer the question a GRC checklist cannot:
*this requirement is a gap — which investment closes it, and how much risk does that remove?*
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.risk.control_effect import ControlCategory as Category


class SecurityFunction(StrEnum):
    """The NIST CSF 2.0 functions (SEBI CSCRF uses the same six plus Governance)."""

    GOVERNANCE = "Governance"
    IDENTIFY = "Identify"
    PROTECT = "Protect"
    DETECT = "Detect"
    RESPOND = "Respond"
    RECOVER = "Recover"


@dataclass(frozen=True)
class CanonicalRequirement:
    id: str
    name: str
    objective: str
    function: SecurityFunction
    categories: tuple[Category, ...]
    references: dict[str, tuple[str, ...]] = field(default_factory=dict)
    note: str | None = None

    def reference_for(self, framework_id: str) -> tuple[str, ...]:
        return self.references.get(framework_id, ())

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "objective": self.objective,
            "function": self.function.value,
            "categories": [category.value for category in self.categories],
            "references": {key: list(value) for key, value in self.references.items()},
            "note": self.note,
        }


def _req(
    id: str,
    name: str,
    objective: str,
    function: SecurityFunction,
    categories: tuple[Category, ...],
    references: dict[str, tuple[str, ...]],
    note: str | None = None,
) -> CanonicalRequirement:
    return CanonicalRequirement(
        id=id,
        name=name,
        objective=objective,
        function=function,
        categories=categories,
        references=references,
        note=note,
    )


REQUIREMENTS: tuple[CanonicalRequirement, ...] = (
    # --- Governance ---------------------------------------------------------------------
    _req(
        "REQ-GOV-RISK",
        "Cyber risk assessment and governance",
        "Cyber risk is assessed against business context, owned, and reviewed by management.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "nist_csf": ("GV.RM", "GV.OV"),
            "iso_27001": ("A.5.1",),
            "iso_42001": ("A.5",),
            "rbi_2023": ("IT governance and oversight", "IT risk assessment"),
            "sebi_cscrf": ("Governance",),
        },
        note=(
            "Governance is an organizational requirement — no technical control fully "
            "satisfies it. CIS v8.1 is out of scope (operational controls only)."
        ),
    ),
    _req(
        "REQ-GOV-POLICY",
        "Security policy and management oversight",
        "An approved security policy exists and management reviews control effectiveness.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "nist_csf": ("GV.PO", "GV.RR"),
            "iso_27001": ("A.5.1", "A.5.4"),
            "rbi_2023": ("IT governance and oversight", "Metrics and reporting"),
            "sebi_cscrf": ("Governance",),
        },
    ),
    _req(
        "REQ-ASSET-INVENTORY",
        "Asset inventory and ownership",
        "Hardware, software and data assets are inventoried, owned and kept current.",
        SecurityFunction.IDENTIFY,
        (),
        {
            "nist_csf": ("ID.AM",),
            "cis_v8": ("1.1", "2.1"),
            "iso_27001": ("A.5.9",),
            "dpdp_2023": ("Data Fiduciary obligations",),
            "rbi_2023": ("Asset and configuration management",),
            "sebi_cscrf": ("Identify",),
        },
    ),
    _req(
        "REQ-SUPPLIER-RISK",
        "Third-party and supply-chain risk",
        "Supplier and service-provider risk is assessed and monitored.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "nist_csf": ("GV.SC",),
            "cis_v8": ("15.1",),
            "iso_27001": ("A.5.19", "A.5.22"),
            "iso_42001": ("A.10",),
            "rbi_2023": ("Outsourcing and third-party risk",),
            "sebi_cscrf": ("Governance", "Identify"),
        },
    ),
    # --- Identify / Protect: vulnerability and platform ---------------------------------
    _req(
        "REQ-VULN-MGMT",
        "Continuous vulnerability management",
        "Vulnerabilities are continuously identified, prioritised and remediated.",
        SecurityFunction.IDENTIFY,
        (Category.RESISTIVE,),
        {
            "nist_csf": ("ID.RA", "PR.PS"),
            "cis_v8": ("7.1", "7.2"),
            "iso_27001": ("A.8.8",),
            "rbi_2023": ("Vulnerability assessment and penetration testing",),
            "sebi_cscrf": ("Identify", "Protect"),
        },
    ),
    _req(
        "REQ-PATCH-MGMT",
        "Patch and change management",
        "Patches are applied within defined windows and changes are controlled.",
        SecurityFunction.PROTECT,
        (Category.RESISTIVE,),
        {
            "nist_csf": ("PR.PS",),
            "cis_v8": ("7.3", "7.4"),
            "iso_27001": ("A.8.8", "A.8.32"),
            "rbi_2023": ("Change and patch management",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    _req(
        "REQ-PENTEST",
        "Adversarial testing",
        "Penetration tests and control validation are performed periodically.",
        SecurityFunction.IDENTIFY,
        (),
        {
            "nist_csf": ("ID.RA",),
            "cis_v8": ("18.1",),
            "iso_27001": ("A.8.34",),
            "rbi_2023": ("Vulnerability assessment and penetration testing",),
            "sebi_cscrf": ("Identify",),
        },
    ),
    _req(
        "REQ-HARDENING",
        "Secure configuration and hardening",
        "Assets and software are securely configured and hardened baselines are enforced.",
        SecurityFunction.PROTECT,
        (Category.RESISTIVE,),
        {
            "nist_csf": ("PR.PS",),
            "cis_v8": ("4.1",),
            "iso_27001": ("A.8.9",),
            "rbi_2023": ("Asset and configuration management",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    # --- Identity and access -------------------------------------------------------------
    _req(
        "REQ-IDENTITY-MFA",
        "Multi-factor authentication",
        "MFA is enforced, at minimum for privileged and remote access.",
        SecurityFunction.PROTECT,
        (Category.RESISTIVE,),
        {
            "nist_csf": ("PR.AA",),
            "cis_v8": ("6.3", "6.4", "6.5"),
            "iso_27001": ("A.8.5",),
            "rbi_2023": ("Access controls",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    _req(
        "REQ-PRIVILEGED-ACCESS",
        "Privileged access management",
        "Privileged accounts are inventoried, vaulted, and their use is monitored.",
        SecurityFunction.PROTECT,
        (Category.RESISTIVE,),
        {
            "nist_csf": ("PR.AA",),
            "cis_v8": ("5.4", "6.8"),
            "iso_27001": ("A.8.2",),
            "rbi_2023": ("Access controls", "Audit trails"),
            "sebi_cscrf": ("Protect",),
        },
    ),
    _req(
        "REQ-ACCOUNT-MGMT",
        "Account lifecycle management",
        "Accounts are provisioned, reviewed and revoked through a controlled lifecycle.",
        SecurityFunction.PROTECT,
        (Category.RESISTIVE,),
        {
            "nist_csf": ("PR.AA",),
            "cis_v8": ("5.1", "5.3"),
            "iso_27001": ("A.5.15", "A.5.16", "A.5.18"),
            "rbi_2023": ("Access controls",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    # --- Endpoint, network, application --------------------------------------------------
    _req(
        "REQ-ENDPOINT-PROTECTION",
        "Malware defence and endpoint detection",
        "Endpoints run malware defence and behaviour-based detection with response capability.",
        SecurityFunction.PROTECT,
        (Category.DETERRENT,),
        {
            "nist_csf": ("PR.PS", "DE.CM"),
            "cis_v8": ("10.1", "10.2", "10.7"),
            "iso_27001": ("A.8.7",),
            "rbi_2023": ("Cyber incident response and recovery",),
            "sebi_cscrf": ("Protect", "Detect"),
        },
    ),
    _req(
        "REQ-NETWORK-SEGMENTATION",
        "Network segmentation and segregation",
        "Critical tiers are segmented so compromise does not spread laterally.",
        SecurityFunction.PROTECT,
        (Category.AVOIDANCE,),
        {
            "nist_csf": ("PR.IR",),
            "cis_v8": ("12.2", "12.4"),
            "iso_27001": ("A.8.20", "A.8.22"),
            "rbi_2023": ("IT risk assessment", "Access controls"),
            "sebi_cscrf": ("Protect",),
        },
    ),
    _req(
        "REQ-NETWORK-DEFENCE",
        "Network monitoring and defence",
        "Network traffic is filtered, monitored and defended against attacks.",
        SecurityFunction.DETECT,
        (Category.DETERRENT, Category.AVOIDANCE),
        {
            "nist_csf": ("DE.CM", "PR.IR"),
            "cis_v8": ("12.6", "13.1"),
            "iso_27001": ("A.8.16", "A.8.21"),
            "rbi_2023": ("Cyber incident response and recovery",),
            "sebi_cscrf": ("Detect",),
        },
    ),
    _req(
        "REQ-APPLICATION-SECURITY",
        "Application security",
        "Applications are hardened, protected at the edge and securely coded.",
        SecurityFunction.PROTECT,
        (Category.AVOIDANCE,),
        {
            "nist_csf": ("PR.PS",),
            "cis_v8": ("16.1", "16.6"),
            "iso_27001": ("A.8.25", "A.8.26", "A.8.28"),
            "rbi_2023": ("Vulnerability assessment and penetration testing",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    _req(
        "REQ-EMAIL-PROTECTION",
        "Email and web protection",
        "Email and browser attack vectors are filtered and blocked.",
        SecurityFunction.PROTECT,
        (Category.AVOIDANCE,),
        {
            "nist_csf": ("PR.DS",),
            "cis_v8": ("9.1", "9.2", "9.5"),
            "iso_27001": ("A.8.23",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    _req(
        "REQ-DATA-PROTECTION",
        "Data protection and cryptography",
        "Sensitive data is classified, encrypted and protected in transit and at rest.",
        SecurityFunction.PROTECT,
        (Category.RESISTIVE,),
        {
            "nist_csf": ("PR.DS",),
            "cis_v8": ("3.1", "3.10", "3.11"),
            "iso_27001": ("A.8.24", "A.5.12", "A.5.13"),
            "dpdp_2023": ("Security safeguards",),
            "rbi_2023": ("Information and cyber security",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    _req(
        "REQ-CLOUD-SECURITY",
        "Cloud service security posture",
        "Cloud configuration is continuously assessed and misconfiguration is remediated.",
        SecurityFunction.PROTECT,
        (Category.DETERRENT,),
        {
            "nist_csf": ("PR.IR", "ID.AM"),
            "cis_v8": ("3.1", "4.1"),
            "iso_27001": ("A.5.23", "A.8.9"),
            "rbi_2023": ("Outsourcing and third-party risk",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    _req(
        "REQ-PRIVACY-DPDP",
        "Personal data protection",
        "Personal data handling meets statutory obligations, including breach reporting.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "nist_csf": ("GV.OC", "PR.DS"),
            "iso_27001": ("A.5.34",),
            "dpdp_2023": (
                "Notice",
                "Consent",
                "Data Protection Officer",
                "Grievance redressal",
            ),
            "rbi_2023": ("Information and cyber security",),
            "sebi_cscrf": ("Governance", "Protect"),
        },
        note=(
            "Indian statutory context is the DPDP Act 2023 with the 2025 Rules. Detailed "
            "obligations (notice, rights, retention, children's data, SDF duties) are carried "
            "by the dedicated REQ-DPDP-* requirements rather than duplicated here."
        ),
    ),
    _req(
        "REQ-AWARENESS",
        "Security awareness and training",
        "Staff are trained so that human attack vectors are reduced.",
        SecurityFunction.PROTECT,
        (Category.AVOIDANCE,),
        {
            "nist_csf": ("PR.AT",),
            "cis_v8": ("14.1", "14.2"),
            "iso_27001": ("A.6.3",),
            "iso_42001": ("A.4.4",),
            "dpdp_2023": ("Data Fiduciary obligations",),
            "rbi_2023": ("IT governance and oversight",),
            "sebi_cscrf": ("Protect",),
        },
    ),
    # --- Detect, respond, recover --------------------------------------------------------
    _req(
        "REQ-LOG-MGMT",
        "Audit logging and log retention",
        "Security-relevant events are logged centrally and retained.",
        SecurityFunction.DETECT,
        (Category.DETERRENT,),
        {
            "nist_csf": ("DE.CM", "DE.AE"),
            "cis_v8": ("8.1", "8.2", "8.10"),
            "iso_27001": ("A.8.15",),
            "dpdp_2023": ("Data Fiduciary obligations",),
            "rbi_2023": ("Audit trails",),
            "sebi_cscrf": ("Detect",),
        },
    ),
    _req(
        "REQ-CONTINUOUS-MONITORING",
        "Continuous monitoring and alerting",
        "Events are correlated into alerts and triaged in a timely manner.",
        SecurityFunction.DETECT,
        (Category.DETERRENT,),
        {
            "nist_csf": ("DE.CM", "DE.AE"),
            "cis_v8": ("8.11", "13.1"),
            "iso_27001": ("A.8.16",),
            "rbi_2023": ("Cyber incident response and recovery", "Metrics and reporting"),
            "sebi_cscrf": ("Detect",),
        },
    ),
    _req(
        "REQ-INCIDENT-RESPONSE",
        "Incident response and reporting",
        "Incidents are managed, reported to authorities and learned from.",
        SecurityFunction.RESPOND,
        (Category.RESPONSIVE,),
        {
            "nist_csf": ("RS.MA", "RS.AN", "RS.CO", "RS.MI"),
            "cis_v8": ("17.1", "17.4", "17.6", "17.7", "17.8"),
            "iso_27001": ("A.5.24", "A.5.25", "A.5.26", "A.5.27", "A.5.28"),
            "dpdp_2023": ("Breach notification",),
            "rbi_2023": ("Cyber incident response and recovery",),
            "sebi_cscrf": ("Respond",),
        },
        note="CERT-In Directions (Apr 2022) add six-hour reporting obligations.",
    ),
    _req(
        "REQ-BACKUP-RECOVERY",
        "Backup and data recovery",
        "Data is backed up, isolated from production, and restore is verified.",
        SecurityFunction.RECOVER,
        (Category.RESPONSIVE,),
        {
            "nist_csf": ("RC.RP", "PR.DS"),
            "cis_v8": ("11.1", "11.2", "11.3", "11.4", "11.5"),
            "iso_27001": ("A.8.13",),
            "rbi_2023": ("Business continuity and disaster recovery",),
            "sebi_cscrf": ("Recover",),
        },
    ),
    _req(
        "REQ-RESILIENCE-BCP",
        "Business continuity and resilience",
        "Continuity plans exist, are tested, and recovery objectives are defined.",
        SecurityFunction.RECOVER,
        (Category.RESPONSIVE,),
        {
            "nist_csf": ("RC.RP", "PR.IR"),
            "iso_27001": ("A.5.29", "A.5.30"),
            "rbi_2023": ("Business continuity and disaster recovery",),
            "sebi_cscrf": ("Recover", "Governance"),
        },
    ),
    # --- DPDP Act 2023: statutory obligations --------------------------------------------
    # These are obligations of the Act itself, not restatements of ISO 27001. Most are
    # organizational: no technical control discharges them, so they surface as gaps. That is
    # the honest result and the reason a data-protection programme is not a security tooling
    # purchase.
    _req(
        "REQ-DPDP-NOTICE",
        "Notice and lawful consent",
        "Personal data is processed only on a lawful basis, with itemised notice and consent.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "dpdp_2023": ("Notice", "Consent"),
            "nist_csf": ("GV.OC",),
            "iso_27001": ("A.5.34",),
        },
        note="Consent must be free, specific, informed and unambiguous — not a bundled term.",
    ),
    _req(
        "REQ-DPDP-RIGHTS",
        "Data principal rights and grievance redressal",
        "Access, correction, erasure and grievance requests are honoured within statutory time.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "dpdp_2023": (
                "Right to access",
                "Right to correction and erasure",
                "Grievance redressal",
            ),
            "nist_csf": ("GV.OC",),
            "iso_27001": ("A.5.34",),
        },
        note="A request workflow is process, not tooling — expect this to read as a gap.",
    ),
    _req(
        "REQ-DPDP-BREACH",
        "Personal data breach notification",
        "Breaches are detected, assessed, and notified to the Board and data principals.",
        SecurityFunction.RESPOND,
        (),
        {
            "dpdp_2023": ("Breach notification", "Data Fiduciary obligations"),
            "nist_csf": ("RS.CO", "DE.CM"),
            "iso_27001": ("A.5.24", "A.5.25", "A.5.26"),
            "rbi_2023": ("Cyber incident response and recovery",),
        },
        note=(
            "Detection controls (SIEM, EDR) genuinely contribute: an undetected breach cannot "
            "be notified. The assessment and notification itself remains a process gap."
        ),
    ),
    _req(
        "REQ-DPDP-RETENTION",
        "Purpose limitation, retention and erasure",
        "Data is retained only as long as necessary and erased when the purpose lapses.",
        SecurityFunction.PROTECT,
        (),
        {
            "dpdp_2023": ("Storage limitation", "Erasure on withdrawal of consent"),
            "nist_csf": ("PR.DS",),
            "iso_27001": ("A.5.33", "A.8.10"),
        },
    ),
    _req(
        "REQ-DPDP-CHILD",
        "Children's data and verifiable parental consent",
        "Verifiable parental consent is obtained and behavioural monitoring is not targeted.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "dpdp_2023": ("Children's data", "Verifiable parental consent"),
            "nist_csf": ("GV.OC",),
        },
        note=(
            "Material for a campus or edtech estate: student records are children's data, so "
            "this obligation applies where a generic security framework is silent."
        ),
    ),
    _req(
        "REQ-DPDP-SDF",
        "Significant Data Fiduciary obligations",
        "A DPO is appointed, a DPIA is performed, and an independent audit is completed.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "dpdp_2023": ("Significant Data Fiduciary", "Data Protection Officer"),
            "nist_csf": ("GV.RR", "GV.OV"),
            "iso_27001": ("A.5.2", "A.5.34"),
        },
    ),
    # --- ISO/IEC 42001: AI management system ---------------------------------------------
    # AI governance is genuinely new territory: the cyber frameworks above are silent on it.
    # These carry `iso_42001` references and, where a general governance obligation overlaps,
    # a NIST CSF reference too. An estate running no AI systems will show them all as gaps —
    # which is the correct answer, not a defect in the crosswalk.
    _req(
        "REQ-AI-POLICY",
        "AI policy, roles and responsibilities",
        "An AI policy exists with assigned accountability for responsible AI use.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "iso_42001": ("A.2", "A.3"),
            "nist_csf": ("GV.PO", "GV.RR"),
            "iso_27001": ("A.5.1",),
        },
    ),
    _req(
        "REQ-AI-IMPACT",
        "AI impact and risk assessment",
        "AI systems are impact-assessed before deployment and reassessed on material change.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "iso_42001": ("A.5", "A.6.1.2"),
            "nist_csf": ("GV.RM", "ID.RA"),
            "iso_27001": ("A.5.1",),
        },
        note="Distinct from cyber risk assessment: considers societal and individual impact.",
    ),
    _req(
        "REQ-AI-DATA",
        "Data governance for AI systems",
        "Training, fine-tuning and inference data is sourced lawfully, documented and "
        "quality-managed.",
        SecurityFunction.PROTECT,
        (),
        {
            "iso_42001": ("A.7", "A.4.3"),
            "nist_csf": ("PR.DS", "ID.AM"),
            "iso_27001": ("A.5.12", "A.5.13", "A.8.24"),
            "dpdp_2023": ("Purpose limitation",),
        },
        note="Overlaps DPDP where the data is personal — which is why both references appear.",
    ),
    _req(
        "REQ-AI-LIFECYCLE",
        "AI system lifecycle and verification",
        "AI systems are designed, verified, deployed, monitored and decommissioned in a "
        "managed cycle.",
        SecurityFunction.PROTECT,
        (),
        {
            "iso_42001": ("A.6", "A.9"),
            "nist_csf": ("PR.PS", "ID.RA"),
        },
    ),
    _req(
        "REQ-AI-TRANSPARENCY",
        "AI transparency, documentation and user information",
        "AI capabilities and limitations are documented and disclosed to affected parties.",
        SecurityFunction.GOVERNANCE,
        (),
        {
            "iso_42001": ("A.8", "A.9"),
            "nist_csf": ("GV.OC",),
        },
        note=(
            "This is the obligation our own system design addresses: the platform states "
            "which figures are engine-produced and which inputs are synthetic."
        ),
    ),
    _req(
        "REQ-AI-MONITORING",
        "Human oversight and AI monitoring",
        "AI system behaviour is monitored, drift is detected, and human review is retained.",
        SecurityFunction.DETECT,
        (),
        {
            "iso_42001": ("A.6.2.6", "A.9"),
            "nist_csf": ("DE.CM", "GV.OV"),
        },
    ),
    _req(
        "REQ-AI-SECURITY",
        "AI system security and robustness",
        "AI systems resist adversarial input, prompt injection and model or data tampering.",
        SecurityFunction.PROTECT,
        (),
        {
            "iso_42001": ("A.6.2.4", "A.7.5"),
            "nist_csf": ("PR.PS", "PR.DS"),
            "iso_27001": ("A.8.9",),
        },
        note=(
            "Applies to this platform too: the LLM layer is read-only and its output is "
            "grounding-checked precisely because a prompt-injected figure would be a safety "
            "failure, not just a bug."
        ),
    ),
)

REQUIREMENTS_BY_ID: dict[str, CanonicalRequirement] = {
    requirement.id: requirement for requirement in REQUIREMENTS
}

FUNCTIONS: tuple[SecurityFunction, ...] = tuple(SecurityFunction)


def get_requirement(requirement_id: str) -> CanonicalRequirement | None:
    return REQUIREMENTS_BY_ID.get(requirement_id)


def requirements_for_framework(framework_id: str) -> tuple[CanonicalRequirement, ...]:
    """Every canonical requirement that cross-references the given framework."""
    return tuple(
        requirement for requirement in REQUIREMENTS if requirement.reference_for(framework_id)
    )


__all__ = [
    "FUNCTIONS",
    "REQUIREMENTS",
    "REQUIREMENTS_BY_ID",
    "CanonicalRequirement",
    "SecurityFunction",
    "get_requirement",
    "requirements_for_framework",
]
