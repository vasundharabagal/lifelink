"""Pydantic schemas for emergency triage and protocol classification (Spec §5.3)."""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ConditionCode, EmergencyType, Priority, ProtocolId, SkillCode


class TriageAnswers(BaseModel):
    """Structured responses to the 3 mandatory triage questions (Spec §5.2)."""
    awake: Optional[str] = Field(default=None, description="Citizen awake status: yes, no, or not_sure")
    breathing: Optional[str] = Field(default=None, description="Citizen breathing status: yes, no, abnormal, or not_sure")
    severe_bleeding: Optional[str] = Field(default=None, description="Severe bleeding present: yes, no, or not_sure")

    model_config = ConfigDict(extra="forbid")


class TriageInput(BaseModel):
    """Citizen emergency input payload submitted for triage evaluation."""
    quick_type: Optional[str] = Field(default=None, description="Optional quick-type chip selected by citizen")
    answers: Optional[TriageAnswers] = Field(default=None, description="3 rapid yes/no triage answers")
    description: Optional[str] = Field(default=None, description="Optional free-text emergency description")

    model_config = ConfigDict(extra="forbid")


class EvidenceItem(BaseModel):
    """Clinical or NLP evidence supporting detected condition."""
    condition: ConditionCode
    from_source: str = Field(description="Detection source: chip, answer, text, or rule")
    span: Optional[str] = Field(default=None, description="Specific matched keyword or phrase")

    model_config = ConfigDict(extra="forbid")


class RequiredSkill(BaseModel):
    """Mandatory skill capability for volunteer response."""
    skill: SkillCode
    min_level: int = Field(ge=1, le=3, description="Minimum qualification tier: 1=trained, 2=certified, 3=professional")

    model_config = ConfigDict(extra="forbid")


class TriageResult(BaseModel):
    """Deterministic output contract produced by triage evaluation (Spec §5.3)."""
    emergency_type: EmergencyType
    observed_conditions: List[ConditionCode]
    red_flags: List[ConditionCode]
    protocol_id: ProtocolId
    required_skills: List[RequiredSkill]
    priority: Priority
    ambulance_required: bool
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = Field(description="Classification pipeline: rules, llm, or hybrid")
    evidence: List[EvidenceItem]
    rules_version: str
    disclaimer_key: str = "decision_support_not_diagnosis"

    model_config = ConfigDict(extra="forbid")
