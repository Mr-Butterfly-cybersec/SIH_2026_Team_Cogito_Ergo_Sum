"""MITRE ATT&CK STIX parsing."""

from __future__ import annotations

import httpx

from app.ingestion.mitre import MitreAttackClient, parse_attack_bundle


def test_parse_attack_bundle_filters_inactive(attack_bundle) -> None:
    catalog = parse_attack_bundle(attack_bundle)
    assert catalog.version == "19.2"
    assert set(catalog.techniques) == {"T1190"}  # revoked + deprecated filtered out
    assert catalog.mitigations == {"M1026": "Privileged Account Management"}
    assert catalog.tactics == ["initial-access"]

    technique = catalog.techniques["T1190"]
    assert technique.name == "Exploit Public-Facing Application"
    assert technique.tactics == ["initial-access"]
    assert "Linux" in technique.platforms
    assert catalog.technique_count == 1
    assert catalog.techniques_for_tactic("initial-access")[0].id == "T1190"
    assert catalog.techniques_for_tactic("exfiltration") == []


def test_fetch_enterprise(make_http, attack_bundle) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "enterprise-attack.json" in str(request.url)
        return httpx.Response(200, json=attack_bundle)

    catalog = MitreAttackClient(client=make_http(handler)).fetch_enterprise()
    assert catalog.technique_count == 1
