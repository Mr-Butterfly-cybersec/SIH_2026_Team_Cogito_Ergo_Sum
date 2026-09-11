"""Scenario schema validation."""

import json

import pytest
from pydantic import ValidationError

from app.risk.demo import EXAMPLE
from app.risk.schemas import ScenarioSpec

RAW = json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_scenario_parses_and_compiles() -> None:
    spec = ScenarioSpec.model_validate(RAW)
    compiled = spec.compile()
    assert compiled.id == RAW["id"]
    assert len(compiled.provenances) == len(list(spec.iter_parameters())) == 14
    assert compiled.attack_techniques == ("T1190", "T1486")


def test_inverted_range_is_rejected() -> None:
    raw = json.loads(json.dumps(RAW))
    raw["frequency"]["contact_frequency"]["distribution"] = {
        "kind": "pert",
        "minimum": 10,
        "mode": 5,
        "maximum": 1,
    }
    with pytest.raises(ValidationError):
        ScenarioSpec.model_validate(raw)


def test_unknown_component_is_rejected() -> None:
    raw = json.loads(json.dumps(RAW))
    raw["magnitude"]["primary"]["made_up_component"] = raw["magnitude"]["primary"]["downtime"]
    with pytest.raises(ValidationError):
        ScenarioSpec.model_validate(raw)


def test_unknown_field_is_rejected() -> None:
    raw = json.loads(json.dumps(RAW))
    raw["unexpected"] = True
    with pytest.raises(ValidationError):
        ScenarioSpec.model_validate(raw)
