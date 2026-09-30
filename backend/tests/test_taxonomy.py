"""Tests verifying shared taxonomy schema validity and Python StrEnum parity."""
import json
from pathlib import Path
import pytest
from app.domain.enums import (
    EmergencyType,
    ConditionCode,
    SkillCode,
    ResponderCategory,
)


def get_taxonomy_path() -> Path:
    """Find monorepo root shared/taxonomy.json."""
    # From backend/tests/test_taxonomy.py -> root/shared/taxonomy.json
    root = Path(__file__).resolve().parent.parent.parent
    path = root / "shared" / "taxonomy.json"
    assert path.exists(), f"Taxonomy file not found at {path}"
    return path


def test_taxonomy_file_structure():
    """Verify taxonomy.json parses and contains required top-level keys."""
    taxonomy_path = get_taxonomy_path()
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "version" in data
    assert "emergency_types" in data
    assert "conditions" in data
    assert "skills" in data
    assert "responder_categories" in data
    assert "protocol_skill_requirements" in data

    assert len(data["emergency_types"]) == 8
    assert len(data["conditions"]) == 9
    assert len(data["skills"]) == 5
    assert len(data["responder_categories"]) == 9
    assert len(data["protocol_skill_requirements"]) == 7


def test_emergency_types_parity():
    """Verify emergency types in taxonomy match EmergencyType enum exactly."""
    taxonomy_path = get_taxonomy_path()
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_codes = {item["code"] for item in data["emergency_types"]}
    enum_codes = {member.value for member in EmergencyType}
    assert json_codes == enum_codes


def test_conditions_parity():
    """Verify conditions in taxonomy match ConditionCode enum exactly."""
    taxonomy_path = get_taxonomy_path()
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_codes = {item["code"] for item in data["conditions"]}
    enum_codes = {member.value for member in ConditionCode}
    assert json_codes == enum_codes


def test_skills_parity():
    """Verify skills in taxonomy match SkillCode enum exactly."""
    taxonomy_path = get_taxonomy_path()
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_codes = {item["code"] for item in data["skills"]}
    enum_codes = {member.value for member in SkillCode}
    assert json_codes == enum_codes

    # Each skill must define levels 1, 2, and 3
    for skill in data["skills"]:
        assert "levels" in skill
        assert set(skill["levels"].keys()) == {"1", "2", "3"}


def test_responder_categories_parity():
    """Verify responder categories in taxonomy match ResponderCategory enum exactly."""
    taxonomy_path = get_taxonomy_path()
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_categories = set(data["responder_categories"])
    enum_categories = {member.value for member in ResponderCategory}
    assert json_categories == enum_categories


def test_protocol_skill_requirements_validity():
    """Verify protocol skill requirements reference valid skill codes and min_levels 1..3."""
    taxonomy_path = get_taxonomy_path()
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid_skills = {item["code"] for item in data["skills"]}
    for proto_id, requirements in data["protocol_skill_requirements"].items():
        assert proto_id.startswith("PROT_")
        for req in requirements:
            assert req["skill"] in valid_skills
            assert 1 <= req["min_level"] <= 3
