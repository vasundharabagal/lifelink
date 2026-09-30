"""Unit tests for protocol library, input sanitizer, and triage rules engine (TRIAGE-01, TRIAGE-02, TRIAGE-03)."""
import pytest
from app.domain.enums import ConditionCode, EmergencyType, Priority, ProtocolId, SkillCode
from app.schemas.triage import TriageAnswers, TriageInput
from app.triage.protocols import protocol_library
from app.triage.rules import evaluate_rules
from app.triage.sanitizer import sanitize_description


def test_protocols_valid():
    """Verify all 7 MVP protocols exist, have valid fields, clinical citations, and contraindications (TRIAGE-01)."""
    protocols = protocol_library.list_protocols()
    assert len(protocols) == 7

    expected_ids = {
        ProtocolId.PROT_UNRESPONSIVE.value,
        ProtocolId.PROT_SEVERE_BLEEDING.value,
        ProtocolId.PROT_CHOKING.value,
        ProtocolId.PROT_SEIZURE.value,
        ProtocolId.PROT_BURNS.value,
        ProtocolId.PROT_TRAUMA_FALL.value,
        ProtocolId.PROT_GENERAL.value,
    }
    loaded_ids = {p.id.value for p in protocols}
    assert loaded_ids == expected_ids

    for p in protocols:
        assert p.status == "demo_unreviewed"
        assert p.call_emergency_first is True
        assert len(p.steps) >= 3
        assert p.source_citation is not None and len(p.source_citation) > 10
        assert len(p.do_not) >= 1
        # Step 1 must always be calling 112 / emergency services
        assert "112" in p.steps[0].text_key or "emergency" in p.steps[0].text_key.lower()


def test_input_sanitizer():
    """Verify sanitizer clamps to 500 chars, strips tags/control chars, and redacts PII (D-45)."""
    # 1. PII Redaction
    text = "Please call 9876543210 or +91-98765-43210 or email test.user@example.com immediately!"
    sanitized = sanitize_description(text)
    assert "9876543210" not in sanitized
    assert "test.user@example.com" not in sanitized
    assert "[REDACTED]" in sanitized

    # 2. HTML Tag Stripping
    html_text = "<script>alert('xss')</script><b>Emergency!</b> Bleeding heavily."
    sanitized = sanitize_description(html_text)
    assert "<script>" not in sanitized
    assert "<b>" not in sanitized
    assert "Emergency! Bleeding heavily." in sanitized

    # 3. Length Clamping
    long_text = "Severe pain in chest " * 50
    sanitized = sanitize_description(long_text, max_length=500)
    assert len(sanitized) <= 500


def test_rules_classification_cardiac_arrest():
    """Verify cardiac arrest / unresponsive inputs classify as P1_CRITICAL with PROT_UNRESPONSIVE (TRIAGE-02, TRIAGE-03)."""
    input_data = TriageInput(
        quick_type="UNRESPONSIVE",
        answers=TriageAnswers(awake="no", breathing="no", severe_bleeding="no"),
        description="Patient collapsed on sidewalk, completely unresponsive and not breathing",
    )
    result = evaluate_rules(input_data)

    assert result.priority == Priority.P1_CRITICAL
    assert result.ambulance_required is True
    assert result.protocol_id == ProtocolId.PROT_UNRESPONSIVE
    assert ConditionCode.UNRESPONSIVE in result.observed_conditions
    assert ConditionCode.NOT_BREATHING in result.observed_conditions
    assert ConditionCode.NOT_BREATHING in result.red_flags

    # Skills check: PROT_UNRESPONSIVE requires CPR/AED level 2
    assert any(s.skill == SkillCode.CPR_AED and s.min_level >= 2 for s in result.required_skills)


def test_rules_classification_severe_bleeding():
    """Verify severe bleeding classifies as P1_CRITICAL with PROT_SEVERE_BLEEDING (TRIAGE-02)."""
    input_data = TriageInput(
        quick_type="BLEEDING",
        answers=TriageAnswers(awake="yes", breathing="yes", severe_bleeding="yes"),
        description="Deep laceration to thigh, blood spurting heavily and won't stop",
    )
    result = evaluate_rules(input_data)

    assert result.priority == Priority.P1_CRITICAL
    assert result.ambulance_required is True
    assert result.protocol_id == ProtocolId.PROT_SEVERE_BLEEDING
    assert ConditionCode.SEVERE_BLEEDING in result.observed_conditions
    assert ConditionCode.SEVERE_BLEEDING in result.red_flags

    # Skills check: PROT_SEVERE_BLEEDING requires bleeding_control level 2
    assert any(s.skill == SkillCode.BLEEDING_CONTROL and s.min_level >= 2 for s in result.required_skills)


def test_precedence_and_red_flags():
    """Verify condition precedence hierarchy correctly selects primary protocol (TRIAGE-03)."""
    # 1. Unresponsive outranks Bleeding
    dual_input_1 = TriageInput(
        description="Person has severe arterial bleeding and is completely unresponsive and not waking up",
    )
    res_1 = evaluate_rules(dual_input_1)
    assert res_1.protocol_id == ProtocolId.PROT_UNRESPONSIVE
    assert ConditionCode.UNRESPONSIVE in res_1.observed_conditions
    assert ConditionCode.SEVERE_BLEEDING in res_1.observed_conditions

    # 2. Choking outranks Burns
    dual_input_2 = TriageInput(
        description="Patient is choking on food with blocked airway, and also suffered hot water scalded burn",
    )
    res_2 = evaluate_rules(dual_input_2)
    assert res_2.protocol_id == ProtocolId.PROT_CHOKING

    # 3. Severe Bleeding outranks Seizure
    dual_input_3 = TriageInput(
        description="Patient has active epileptic seizure convulsions and severe bleeding from head cut",
    )
    res_3 = evaluate_rules(dual_input_3)
    assert res_3.protocol_id == ProtocolId.PROT_SEVERE_BLEEDING

    # 4. Seizure outranks Fracture
    dual_input_4 = TriageInput(
        description="Patient fell from height, broke their arm and is having active convulsions",
    )
    res_4 = evaluate_rules(dual_input_4)
    assert res_4.protocol_id == ProtocolId.PROT_SEIZURE

    # 5. Fracture outranks Burns
    dual_input_5 = TriageInput(
        description="Motorcycle crash, bone sticking out fracture and exhaust pipe burn",
    )
    res_5 = evaluate_rules(dual_input_5)
    assert res_5.protocol_id == ProtocolId.PROT_TRAUMA_FALL


def test_fail_safe_escalation():
    """Verify low-confidence or empty input fails safe up to P2_SERIOUS with PROT_GENERAL (TRIAGE-03)."""
    # 1. Completely empty input
    empty_input = TriageInput()
    res_empty = evaluate_rules(empty_input)
    assert res_empty.priority == Priority.P2_SERIOUS
    assert res_empty.ambulance_required is True
    assert res_empty.protocol_id == ProtocolId.PROT_GENERAL

    # 2. Ambiguous 'not_sure' answers with vague text
    vague_input = TriageInput(
        answers=TriageAnswers(awake="not_sure", breathing="not_sure", severe_bleeding="not_sure"),
        description="I found someone lying on the ground, I am not sure what happened",
    )
    res_vague = evaluate_rules(vague_input)
    assert res_vague.priority == Priority.P2_SERIOUS
    assert res_vague.ambulance_required is True
    assert res_vague.protocol_id == ProtocolId.PROT_GENERAL


def test_explicit_p3_minor_stable():
    """Verify citizen explicit minor inquiry with all negative red-flags classifies as P3_STABLE (TRIAGE-02)."""
    minor_input = TriageInput(
        quick_type="OTHER",
        answers=TriageAnswers(awake="yes", breathing="yes", severe_bleeding="no"),
        description="Minor ankle twist while jogging in the park, stable and talking",
    )
    res_minor = evaluate_rules(minor_input)
    assert res_minor.priority == Priority.P3_STABLE
    assert res_minor.ambulance_required is False
    assert res_minor.protocol_id == ProtocolId.PROT_GENERAL


def test_hinglish_keyword_recognition():
    """Verify Indian English / Hinglish transliterated emergency terms trigger correct conditions."""
    # 1. Unresponsive in Hinglish
    res_behosh = evaluate_rules(TriageInput(description="Insaan behosh ho gaya hai aur koi harkat nahi hai"))
    assert ConditionCode.UNRESPONSIVE in res_behosh.observed_conditions
    assert res_behosh.priority == Priority.P1_CRITICAL

    # 2. Severe bleeding in Hinglish
    res_khoon = evaluate_rules(TriageInput(description="Accident me bohot khoon nikal raha hai"))
    assert ConditionCode.SEVERE_BLEEDING in res_khoon.observed_conditions
    assert res_khoon.priority == Priority.P1_CRITICAL

    # 3. Chest pain in Hinglish
    res_chhati = evaluate_rules(TriageInput(description="Seene me dard ho raha hai bohot tej"))
    assert ConditionCode.CHEST_PAIN in res_chhati.observed_conditions
    assert res_chhati.priority == Priority.P1_CRITICAL
