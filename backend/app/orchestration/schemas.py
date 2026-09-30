"""Pydantic schemas and data contracts for LIFELINK Response Orchestration."""
from datetime import datetime, date
from typing import Optional, List, Dict, Set, Any
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.domain.enums import (
    ResponderCategory,
    ResponderReadiness,
    CredentialStatus,
    AmbulanceUnitType,
    AmbulanceUnitStatus,
    Priority,
    EmergencyType,
    SkillCode,
    TargetKind,
    TrackKind,
    EligibilityRejectionReason,
)
from app.schemas.triage import RequiredSkill


class CandidateSkill(BaseModel):
    """Specific skill code and proficiency level held by a responder."""
    skill_code: SkillCode
    level: int = Field(..., ge=1, le=3, description="Proficiency level (1=trained, 2=certified, 3=professional)")

    model_config = ConfigDict(extra="forbid")


class CandidateCredential(BaseModel):
    """Credential verification record held by a responder."""
    credential_type: str
    status: CredentialStatus
    expires_on: date

    model_config = ConfigDict(extra="forbid")


class CandidateProfile(BaseModel):
    """In-memory representation of a candidate volunteer responder for orchestration."""
    user_id: uuid.UUID
    full_name: str
    category: ResponderCategory
    is_active: bool = True
    readiness: ResponderReadiness = ResponderReadiness.OFF_DUTY
    service_radius_m: int = Field(default=3000, ge=100)
    last_lat: Optional[float] = None
    last_lng: Optional[float] = None
    last_location_at: Optional[datetime] = None
    pinned_location: bool = False
    acceptance_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    responses_24h: int = Field(default=0, ge=0)
    cooldown_until: Optional[datetime] = None
    demo_session_id: Optional[uuid.UUID] = None
    skills: List[CandidateSkill] = Field(default_factory=list)
    credentials: List[CandidateCredential] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class AmbulanceCandidate(BaseModel):
    """In-memory representation of an ambulance unit candidate for professional dispatch."""
    id: uuid.UUID
    callsign: str
    unit_type: AmbulanceUnitType
    status: AmbulanceUnitStatus = AmbulanceUnitStatus.AVAILABLE
    lat: float
    lng: float
    demo_session_id: Optional[uuid.UUID] = None
    runs_24h: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class EmergencyContext(BaseModel):
    """Emergency incident snapshot and dispatch constraints needed for matching."""
    emergency_id: uuid.UUID
    lat: float
    lng: float
    priority: Priority
    emergency_type: EmergencyType
    protocol_id: str
    required_skills: List[RequiredSkill] = Field(default_factory=list)
    patient_user_id: uuid.UUID
    reported_by_user_id: uuid.UUID
    demo_session_id: Optional[uuid.UUID] = None
    excluded_responder_ids: Set[uuid.UUID] = Field(default_factory=set)
    excluded_ambulance_ids: Set[uuid.UUID] = Field(default_factory=set)
    active_responder_ids: Set[uuid.UUID] = Field(default_factory=set)
    active_ambulance_ids: Set[uuid.UUID] = Field(default_factory=set)

    model_config = ConfigDict(extra="forbid")


class ScoreBreakdown(BaseModel):
    """Itemized breakdown of community candidate scoring components (0-100 total)."""
    skill: float = Field(default=0.0, ge=0.0, le=30.0)
    eta: float = Field(default=0.0, ge=0.0, le=30.0)
    fairness: float = Field(default=0.0, ge=0.0, le=15.0)
    reliability: float = Field(default=0.0, ge=0.0, le=10.0)
    credential_tier: float = Field(default=0.0, ge=0.0, le=10.0)
    radius_headroom: float = Field(default=0.0, ge=0.0, le=5.0)

    model_config = ConfigDict(extra="forbid")


class AmbulanceScoreBreakdown(BaseModel):
    """Itemized breakdown of professional ambulance scoring components (0-100 total)."""
    eta: float = Field(default=0.0, ge=0.0, le=70.0)
    suitability: float = Field(default=0.0, ge=0.0, le=20.0)
    fairness: float = Field(default=0.0, ge=0.0, le=10.0)

    model_config = ConfigDict(extra="forbid")


class ScoredCandidate(BaseModel):
    """Ranked community volunteer candidate with total score, breakdowns, and explanation."""
    rank: int = Field(..., ge=1)
    candidate_id: uuid.UUID
    full_name: str
    category: ResponderCategory
    score_total: float = Field(..., ge=0.0, le=100.0)
    score_breakdown: ScoreBreakdown
    distance_m: float = Field(..., ge=0.0)
    eta_s: int = Field(..., ge=30)
    reasons: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ScoredAmbulance(BaseModel):
    """Ranked professional ambulance unit candidate with score and explanation."""
    rank: int = Field(..., ge=1)
    unit_id: uuid.UUID
    callsign: str
    unit_type: AmbulanceUnitType
    score_total: float = Field(..., ge=0.0, le=100.0)
    score_breakdown: AmbulanceScoreBreakdown
    distance_m: float = Field(..., ge=0.0)
    eta_s: int = Field(..., ge=30)
    reasons: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class RejectionDetail(BaseModel):
    """Record of an excluded responder or ambulance candidate with machine-readable reasons."""
    candidate_id: uuid.UUID
    target_kind: TargetKind
    name_or_callsign: str
    reason_codes: List[EligibilityRejectionReason]
    summary: str
    distance_m: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class MatchExplanation(BaseModel):
    """Complete transparent match explanation object for authority/demo oversight (Spec §6.5)."""
    emergency_id: uuid.UUID
    track: TrackKind
    computed_at: datetime
    rules_version: str = "1.0.0"
    weights: Dict[str, float]
    ranked: List[Dict[str, Any]] = Field(default_factory=list)
    rejected: List[RejectionDetail] = Field(default_factory=list)
    citizen_summary: str

    model_config = ConfigDict(extra="forbid")


class OrchestrationResult(BaseModel):
    """Output bundle from running response orchestration matching."""
    emergency_id: uuid.UUID
    computed_at: datetime
    community_plan: List[ScoredCandidate] = Field(default_factory=list)
    professional_plan: List[ScoredAmbulance] = Field(default_factory=list)
    community_explanation: MatchExplanation
    professional_explanation: MatchExplanation

    model_config = ConfigDict(extra="forbid")
