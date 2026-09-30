"""Deterministic table-driven triage rules engine (Spec §5.2, §5.4, TRIAGE-02, TRIAGE-03).

Classifies priority (P1_CRITICAL, P2_SERIOUS, P3_STABLE), ambulance requirement,
primary first-aid protocol, and required responder skills based on structured inputs
and keyword signals. Enforces strict condition precedence and fail-safe upward escalation.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.domain.enums import ConditionCode, EmergencyType, Priority, ProtocolId, SkillCode
from app.schemas.triage import EvidenceItem, RequiredSkill, TriageInput, TriageResult
from app.triage.protocols import protocol_library
from app.triage.sanitizer import sanitize_description

logger = logging.getLogger(__name__)

RULES_VERSION = "1.0.0"

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TAXONOMY_PATH = _PROJECT_ROOT / "shared" / "taxonomy.json"

# Red-flag conditions: presence of any red flag deterministically triggers P1_CRITICAL (Spec §5.4)
RED_FLAG_CONDITIONS: Set[ConditionCode] = {
    ConditionCode.NOT_BREATHING,
    ConditionCode.UNRESPONSIVE,
    ConditionCode.SEVERE_BLEEDING,
    ConditionCode.CHOKING,
    ConditionCode.CHEST_PAIN,
}

# Precedence hierarchy: determines which protocol takes precedence when multiple conditions are observed (Spec §5.4)
# UNRESPONSIVE / NOT_BREATHING > CHOKING > SEVERE_BLEEDING > SEIZURE > TRAUMA_FALL > BURNS > GENERAL
PRECEDENCE_TIERS: List[Tuple[Set[ConditionCode], ProtocolId, EmergencyType]] = [
    (
        {ConditionCode.UNRESPONSIVE, ConditionCode.NOT_BREATHING},
        ProtocolId.PROT_UNRESPONSIVE,
        EmergencyType.UNRESPONSIVE,
    ),
    (
        {ConditionCode.CHOKING},
        ProtocolId.PROT_CHOKING,
        EmergencyType.CHOKING,
    ),
    (
        {ConditionCode.SEVERE_BLEEDING},
        ProtocolId.PROT_SEVERE_BLEEDING,
        EmergencyType.BLEEDING,
    ),
    (
        {ConditionCode.SEIZURE},
        ProtocolId.PROT_SEIZURE,
        EmergencyType.SEIZURE,
    ),
    (
        {ConditionCode.FRACTURE_DISLOCATION},
        ProtocolId.PROT_TRAUMA_FALL,
        EmergencyType.TRAUMA_FALL,
    ),
    (
        {ConditionCode.BURNS},
        ProtocolId.PROT_BURNS,
        EmergencyType.BURNS,
    ),
    (
        {ConditionCode.CHEST_PAIN},
        ProtocolId.PROT_UNRESPONSIVE,
        EmergencyType.CHEST_PAIN,
    ),
    (
        {ConditionCode.HYPOTHERMIA_HEAT},
        ProtocolId.PROT_GENERAL,
        EmergencyType.OTHER,
    ),
]

# Clinical keyword regex dictionary (English + transliterated Indian English / Hinglish terms)
KEYWORD_PATTERNS: Dict[ConditionCode, List[re.Pattern]] = {
    ConditionCode.UNRESPONSIVE: [
        re.compile(r'\b(?:unresponsive|unconscious|fainted|passed\s+out|not\s+waking\s+up|knocked\s+out|collapsed|behosh|be\s*hosh|koi\s+harkat\s+nahi)\b', re.IGNORECASE),
    ],
    ConditionCode.NOT_BREATHING: [
        re.compile(r'\b(?:not\s+breathing|stopped\s+breathing|cannot\s+breathe|cant\s+breathe|gasping|no\s+pulse|saas\s+nahi|sans\s+nahi|saans\s+ruk|dam\s+ghut)\b', re.IGNORECASE),
    ],
    ConditionCode.SEVERE_BLEEDING: [
        re.compile(r'\b(?:severe\s+bleeding|bleeding\s+heavily|blood\s+spurting|gushing\s+blood|massive\s+blood|arterial|khoon\s+beh|khoon\s+nikal|bohot\s+khoon|rakt)\b', re.IGNORECASE),
    ],
    ConditionCode.CHOKING: [
        re.compile(r'\b(?:choking|food\s+stuck|throat\s+blocked|airway\s+blocked|cannot\s+speak\s+or\s+breathe|gale\s+me\s+atakk?|gala\s+ghut)\b', re.IGNORECASE),
    ],
    ConditionCode.CHEST_PAIN: [
        re.compile(r'\b(?:chest\s+pain|heart\s+attack|crushing\s+chest|cardiac|angina|chhati\s+me\s+dard|seene\s+me\s+dard)\b', re.IGNORECASE),
    ],
    ConditionCode.SEIZURE: [
        re.compile(r'\b(?:seizure|convulsions?|convulsing|epileptic|fits|shaking\s+violently|daura|dora|jhatke)\b', re.IGNORECASE),
    ],
    ConditionCode.BURNS: [
        re.compile(r'\b(?:burned|burning|chemical\s+burn|electrical\s+burn|scalded|scalding|jal\s+gaya|aag\s+lag)\b', re.IGNORECASE),
    ],
    ConditionCode.FRACTURE_DISLOCATION: [
        re.compile(r'\b(?:broken\s+bone|fracture|broken\s+leg|broken\s+arm|bone\s+sticking\s+out|dislocated|deformed\s+limb|haddee?\s+toot|fall\s+from\s+height|ladder\s+fall)\b', re.IGNORECASE),
    ],
    ConditionCode.HYPOTHERMIA_HEAT: [
        re.compile(r'\b(?:heat\s*stroke|hypothermia|freezing\s+cold|extreme\s+heat|loo\s+lag)\b', re.IGNORECASE),
    ],
}

# Quick-type chip mapping to initial condition and emergency type
QUICK_TYPE_MAP: Dict[str, Tuple[Optional[ConditionCode], EmergencyType]] = {
    "BLEEDING": (ConditionCode.SEVERE_BLEEDING, EmergencyType.BLEEDING),
    "UNRESPONSIVE": (ConditionCode.UNRESPONSIVE, EmergencyType.UNRESPONSIVE),
    "CHOKING": (ConditionCode.CHOKING, EmergencyType.CHOKING),
    "BURNS": (ConditionCode.BURNS, EmergencyType.BURNS),
    "SEIZURE": (ConditionCode.SEIZURE, EmergencyType.SEIZURE),
    "TRAUMA_FALL": (ConditionCode.FRACTURE_DISLOCATION, EmergencyType.TRAUMA_FALL),
    "CHEST_PAIN": (ConditionCode.CHEST_PAIN, EmergencyType.CHEST_PAIN),
    "OTHER": (None, EmergencyType.OTHER),
}


def _load_protocol_skills() -> Dict[str, List[RequiredSkill]]:
    """Load protocol skill requirements from shared/taxonomy.json."""
    if not _TAXONOMY_PATH.exists():
        # Fallback to defaults if taxonomy file is missing
        return {
            "PROT_UNRESPONSIVE": [RequiredSkill(skill=SkillCode.CPR_AED, min_level=2)],
            "PROT_SEVERE_BLEEDING": [RequiredSkill(skill=SkillCode.BLEEDING_CONTROL, min_level=2)],
            "PROT_CHOKING": [RequiredSkill(skill=SkillCode.BASIC_FIRST_AID, min_level=1)],
            "PROT_SEIZURE": [RequiredSkill(skill=SkillCode.BASIC_FIRST_AID, min_level=1)],
            "PROT_BURNS": [RequiredSkill(skill=SkillCode.BASIC_FIRST_AID, min_level=1)],
            "PROT_TRAUMA_FALL": [RequiredSkill(skill=SkillCode.TRAUMA_RESPONSE, min_level=2)],
            "PROT_GENERAL": [RequiredSkill(skill=SkillCode.BASIC_FIRST_AID, min_level=1)],
        }

    with open(_TAXONOMY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    reqs_map = data.get("protocol_skill_requirements", {})
    result: Dict[str, List[RequiredSkill]] = {}
    for prot_id, skills in reqs_map.items():
        result[prot_id] = [
            RequiredSkill(skill=SkillCode(s["skill"]), min_level=s["min_level"])
            for s in skills
        ]
    return result


_PROTOCOL_SKILLS = _load_protocol_skills()


def evaluate_rules(
    input_data: TriageInput,
    additional_conditions: Optional[Set[ConditionCode]] = None,
    source: str = "rules",
) -> TriageResult:
    """Evaluate triage input deterministically against clinical precedence tables.
    
    1. Extracts conditions from quick_type chip, yes/no answers, and description keywords.
    2. Incorporates any additional conditions (e.g. from Tier 2 LLM extractor).
    3. Detects red flags (P1_CRITICAL, ambulance_required=True).
    4. Evaluates condition precedence to select primary protocol.
    5. Maps mandatory responder skills from taxonomy.
    6. Applies fail-safe upward escalation for low-confidence or empty inputs.
    """
    observed_conditions: Set[ConditionCode] = set()
    evidence: List[EvidenceItem] = []
    confidence = 1.0
    emergency_type = EmergencyType.OTHER

    # 1. Process Quick-Type chip
    if input_data.quick_type:
        chip_code = input_data.quick_type.upper().strip()
        if chip_code in QUICK_TYPE_MAP:
            cond, em_type = QUICK_TYPE_MAP[chip_code]
            emergency_type = em_type
            if cond:
                observed_conditions.add(cond)
                evidence.append(EvidenceItem(condition=cond, from_source="chip", span=chip_code))

    # 2. Process Structured Answers (Outranks free-text NLP)
    if input_data.answers:
        ans = input_data.answers
        if ans.awake == "no":
            observed_conditions.add(ConditionCode.UNRESPONSIVE)
            evidence.append(EvidenceItem(condition=ConditionCode.UNRESPONSIVE, from_source="answer", span="awake=no"))
        elif ans.awake == "not_sure":
            confidence -= 0.15

        if ans.breathing == "no":
            observed_conditions.add(ConditionCode.NOT_BREATHING)
            evidence.append(EvidenceItem(condition=ConditionCode.NOT_BREATHING, from_source="answer", span="breathing=no"))
        elif ans.breathing == "abnormal":
            observed_conditions.add(ConditionCode.NOT_BREATHING)
            evidence.append(EvidenceItem(condition=ConditionCode.NOT_BREATHING, from_source="answer", span="breathing=abnormal"))
        elif ans.breathing == "not_sure":
            confidence -= 0.15

        if ans.severe_bleeding == "yes":
            observed_conditions.add(ConditionCode.SEVERE_BLEEDING)
            evidence.append(EvidenceItem(condition=ConditionCode.SEVERE_BLEEDING, from_source="answer", span="severe_bleeding=yes"))
        elif ans.severe_bleeding == "not_sure":
            confidence -= 0.15

    # 3. Process Description text via Regex Keyword Matcher
    sanitized_desc = sanitize_description(input_data.description)
    if sanitized_desc:
        for cond, patterns in KEYWORD_PATTERNS.items():
            for pat in patterns:
                m = pat.search(sanitized_desc)
                if m:
                    observed_conditions.add(cond)
                    evidence.append(EvidenceItem(condition=cond, from_source="text", span=m.group(0)))
                    break

    # 4. Merge any additional conditions (e.g. from LLM extractor)
    if additional_conditions:
        for c in additional_conditions:
            if c not in observed_conditions:
                observed_conditions.add(c)
                evidence.append(EvidenceItem(condition=c, from_source="llm", span=None))

    # 5. Extract red flags
    red_flags = sorted(
        [c for c in observed_conditions if c in RED_FLAG_CONDITIONS],
        key=lambda x: x.value,
    )

    # 6. Resolve Primary Protocol & Emergency Type via Precedence Hierarchy
    selected_protocol = ProtocolId.PROT_GENERAL
    for target_conditions, prot_id, em_type in PRECEDENCE_TIERS:
        if observed_conditions & target_conditions:
            selected_protocol = prot_id
            if emergency_type == EmergencyType.OTHER:
                emergency_type = em_type
            break

    # 7. Priority and Ambulance Requirement Determination
    # Spec §5.4:
    # - Red flags => P1_CRITICAL, ambulance_required = True
    # - P2 => non-red-flags without red flag, ambulance_required = True
    # - Low confidence (< 0.5) or no conditions => fail-safe up to P2_SERIOUS, PROT_GENERAL, ambulance_required = True
    # - P3 => only when citizen explicitly selected minor emergency and no conditions detected
    if red_flags:
        priority = Priority.P1_CRITICAL
        ambulance_required = True
    elif observed_conditions:
        priority = Priority.P2_SERIOUS
        ambulance_required = True
    else:
        # No conditions detected
        confidence = min(confidence, 0.4)
        if input_data.quick_type == "OTHER" and input_data.answers and input_data.answers.awake == "yes" and input_data.answers.breathing == "yes" and input_data.answers.severe_bleeding == "no":
            # Explicit citizen minor case
            priority = Priority.P3_STABLE
            ambulance_required = False
            selected_protocol = ProtocolId.PROT_GENERAL
            confidence = 0.9
        else:
            # Fail-safe upward escalation (Spec §5.4)
            priority = Priority.P2_SERIOUS
            ambulance_required = True
            selected_protocol = ProtocolId.PROT_GENERAL

    # Enforce minimum protocol existence in loaded library
    if protocol_library.get_protocol(selected_protocol.value) is None:
        selected_protocol = ProtocolId.PROT_GENERAL

    # 8. Required Skills Mapping
    required_skills = _PROTOCOL_SKILLS.get(selected_protocol.value, [
        RequiredSkill(skill=SkillCode.BASIC_FIRST_AID, min_level=1)
    ])

    confidence = max(0.1, min(1.0, round(confidence, 2)))

    return TriageResult(
        emergency_type=emergency_type,
        observed_conditions=sorted(list(observed_conditions), key=lambda x: x.value),
        red_flags=red_flags,
        protocol_id=selected_protocol,
        required_skills=required_skills,
        priority=priority,
        ambulance_required=ambulance_required,
        confidence=confidence,
        source=source,
        evidence=evidence,
        rules_version=RULES_VERSION,
        disclaimer_key="decision_support_not_diagnosis",
    )
