"""Framework registry — the standards and regulations we map against.

Curated and versioned. **No LLM-generated mappings**: every reference in this package is
transcribed from published sources, and each framework records the version it was read
from so a stale mapping is visible rather than silently wrong.

References are kept at the level the source publishes them at. NIST CSF 2.0 is referenced
by category (e.g. ``PR.AA``), CIS v8.1 by control number, and ISO/IEC 27001:2022 by Annex A
control. RBI and SEBI are referenced by the thematic area named in the direction/framework
rather than by invented clause numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class FrameworkKind(StrEnum):
    STANDARD = "standard"
    REGULATION = "regulation"


@dataclass(frozen=True)
class Framework:
    id: str
    name: str
    short_name: str
    version: str
    kind: FrameworkKind
    publisher: str
    published: date
    source_url: str
    note: str | None = None

    @property
    def is_regulation(self) -> bool:
        return self.kind is FrameworkKind.REGULATION

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "version": self.version,
            "kind": self.kind.value,
            "publisher": self.publisher,
            "published": self.published.isoformat(),
            "source_url": self.source_url,
            "note": self.note,
        }


CATALOG_VERSION = "2026.10"

FRAMEWORKS: tuple[Framework, ...] = (
    Framework(
        id="nist_csf",
        name="NIST Cybersecurity Framework 2.0",
        short_name="NIST CSF 2.0",
        version="2.0",
        kind=FrameworkKind.STANDARD,
        publisher="NIST",
        published=date(2024, 2, 26),
        source_url="https://www.nist.gov/cyberframework",
        note="Referenced at category level (GV/ID/PR/DE/RS/RC).",
    ),
    Framework(
        id="cis_v8",
        name="CIS Critical Security Controls v8.1",
        short_name="CIS v8.1",
        version="8.1",
        kind=FrameworkKind.STANDARD,
        publisher="Center for Internet Security",
        published=date(2024, 6, 25),
        source_url="https://www.cisecurity.org/controls",
        note="Referenced by control number (1-18).",
    ),
    Framework(
        id="iso_27001",
        name="ISO/IEC 27001:2022 Annex A",
        short_name="ISO 27001:2022",
        version="2022",
        kind=FrameworkKind.STANDARD,
        publisher="ISO/IEC",
        published=date(2022, 10, 25),
        source_url="https://www.iso.org/standard/27001",
        note="Referenced by Annex A control (A.5-A.8).",
    ),
    Framework(
        id="iso_42001",
        name="ISO/IEC 42001:2023 Artificial Intelligence Management System",
        short_name="ISO 42001:2023",
        version="2023",
        kind=FrameworkKind.STANDARD,
        publisher="ISO/IEC",
        published=date(2023, 12, 18),
        source_url="https://www.iso.org/standard/42001",
        note=(
            "Referenced by Annex A control group (A.2-A.10). AI-specific obligations: "
            "an estate with no AI systems in scope will legitimately show as a gap."
        ),
    ),
    Framework(
        id="rbi_2023",
        name="RBI Master Direction on IT Governance, Risk, Controls and Assurance Practices",
        short_name="RBI IT Governance 2023",
        version="2023",
        kind=FrameworkKind.REGULATION,
        publisher="Reserve Bank of India",
        published=date(2023, 11, 7),
        source_url="https://www.rbi.org.in/",
        note="Referenced by the thematic area named in the direction.",
    ),
    Framework(
        id="sebi_cscrf",
        name="SEBI Cybersecurity and Cyber Resilience Framework",
        short_name="SEBI CSCRF",
        version="2024",
        kind=FrameworkKind.REGULATION,
        publisher="Securities and Exchange Board of India",
        published=date(2024, 8, 20),
        source_url="https://www.sebi.gov.in/",
        note=(
            "Referenced by cybersecurity function "
            "(Governance/Identify/Protect/Detect/Respond/Recover)."
        ),
    ),
    Framework(
        id="dpdp_2023",
        name="Digital Personal Data Protection Act, 2023 (with the 2025 Rules)",
        short_name="DPDP Act 2023",
        version="2023",
        kind=FrameworkKind.REGULATION,
        publisher="Ministry of Electronics and Information Technology, India",
        published=date(2023, 8, 11),
        source_url="https://www.meity.gov.in/",
        note=(
            "Referenced by the obligation named in the Act (notice, consent, rights, "
            "breach, retention) rather than by invented section numbers."
        ),
    ),
)

FRAMEWORKS_BY_ID: dict[str, Framework] = {framework.id: framework for framework in FRAMEWORKS}

#: Indian regulatory overlays are the ones a domestic regulated entity is audited against.
INDIAN_REGULATORS: frozenset[str] = frozenset({"rbi_2023", "sebi_cscrf", "dpdp_2023"})


def get_framework(framework_id: str) -> Framework | None:
    return FRAMEWORKS_BY_ID.get(framework_id)


__all__ = [
    "CATALOG_VERSION",
    "FRAMEWORKS",
    "FRAMEWORKS_BY_ID",
    "INDIAN_REGULATORS",
    "Framework",
    "FrameworkKind",
    "get_framework",
]
