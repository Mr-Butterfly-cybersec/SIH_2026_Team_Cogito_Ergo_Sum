"""MITRE ATT&CK client (STIX 2.1 enterprise bundle).

The bundle is ~51 MB, so it is fetched once per release and reduced to a compact
catalog. Revoked and deprecated objects are filtered out.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ingestion.base import HttpClient
from app.normalization.taxonomy import attack_technique_id

ATTACK_ENTERPRISE_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data"
    "/master/enterprise-attack/enterprise-attack.json"
)
_ATTACK_SOURCE = "mitre-attack"


class AttackTechnique(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    tactics: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    is_subtechnique: bool = False


class AttackCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str | None = None
    tactics: list[str] = Field(default_factory=list)
    techniques: dict[str, AttackTechnique] = Field(default_factory=dict)
    mitigations: dict[str, str] = Field(default_factory=dict)

    @property
    def technique_count(self) -> int:
        return len(self.techniques)

    def techniques_for_tactic(self, tactic: str) -> list[AttackTechnique]:
        return [t for t in self.techniques.values() if tactic in t.tactics]


def _external_id(obj: dict[str, Any]) -> str | None:
    for reference in obj.get("external_references", []) or []:
        if reference.get("source_name") == _ATTACK_SOURCE:
            return reference.get("external_id")
    return None


def _is_active(obj: dict[str, Any]) -> bool:
    return not obj.get("revoked") and not obj.get("x_mitre_deprecated")


def parse_attack_bundle(bundle: dict[str, Any]) -> AttackCatalog:
    catalog = AttackCatalog()
    for obj in bundle.get("objects", []) or []:
        obj_type = obj.get("type")
        if obj_type == "x-mitre-collection":
            catalog.version = obj.get("x_mitre_version")
        if not _is_active(obj):
            continue
        if obj_type == "x-mitre-tactic":
            shortname = obj.get("x_mitre_shortname")
            if shortname:
                catalog.tactics.append(shortname)
        elif obj_type == "attack-pattern":
            technique_id = attack_technique_id(_external_id(obj))
            if not technique_id:
                continue
            tactics = [
                phase.get("phase_name")
                for phase in obj.get("kill_chain_phases", []) or []
                if phase.get("phase_name")
            ]
            catalog.techniques[technique_id] = AttackTechnique(
                id=technique_id,
                name=obj.get("name", technique_id),
                tactics=tactics,
                platforms=obj.get("x_mitre_platforms", []) or [],
                is_subtechnique=bool(obj.get("x_mitre_is_subtechnique")),
            )
        elif obj_type == "course-of-action":
            mitigation_id = _external_id(obj)
            if mitigation_id:
                catalog.mitigations[mitigation_id] = obj.get("name", mitigation_id)
    catalog.tactics = sorted(set(catalog.tactics))
    return catalog


class MitreAttackClient:
    def __init__(
        self, *, client: HttpClient | None = None, transport: Any = None, sleep: Any = time.sleep
    ) -> None:
        self._client = client or HttpClient(transport=transport, sleep=sleep)

    def fetch_enterprise(self) -> AttackCatalog:
        return parse_attack_bundle(self._client.get_json(ATTACK_ENTERPRISE_URL))

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> MitreAttackClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
