"""Pydantic schemas for emergency incident creation, responses, and duplicate conflict errors (Spec §7.1, §10.3)."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EmergencyStatus, Priority, TrackStatus
from app.schemas.triage import TriageInput


class EmergencyCreateRequest(BaseModel):
    """Citizen emergency submission payload for initial SOS request (Spec §7.1)."""
    lat: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude coordinate")
    lng: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude coordinate")
    location_accuracy_m: float = Field(default=10.0, ge=0.0, description="GPS accuracy estimate in meters")
    location_hint: Optional[str] = Field(default=None, max_length=500, description="Optional landmark or apartment number")
    patient_is_reporter: bool = Field(default=True, description="True if caller is the patient, False if bystander")
    consent_share_medical: bool = Field(default=False, description="Consent to share pre-registered emergency medical profile")
    triage_input: TriageInput = Field(..., description="Structured triage inputs, quick chips, or free text")
    force_create: bool = Field(default=False, description="Bypass near-simultaneous deduplication check")
    demo_session_id: Optional[uuid.UUID] = Field(default=None, description="Optional tenant demo session scope")

    model_config = ConfigDict(extra="forbid")


class EmergencyAdvanceRequest(BaseModel):
    """Optional payload for explicit deterministic state advancement."""
    offset_seconds: int = Field(default=0, ge=0, description="Virtual seconds to advance clock before evaluating state machine")

    model_config = ConfigDict(extra="forbid")


class EmergencyCancelRequest(BaseModel):
    """Payload to cancel an ongoing emergency incident."""
    reason: Optional[str] = Field(default="REPORTER_CANCELLED", max_length=100)

    model_config = ConfigDict(extra="forbid")


class EmergencyResolveRequest(BaseModel):
    """Payload to mark an emergency incident as formally resolved/completed."""
    summary: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")


class DuplicateEmergencyErrorResponse(BaseModel):
    """Structured HTTP 409 response returned when a duplicate emergency is detected within 150m and 10min (Spec §7.1)."""
    error: str = Field(default="POSSIBLE_DUPLICATE")
    message: str = Field(default="A near-simultaneous emergency was reported within 150 meters in the last 10 minutes.")
    existing_emergency_id: uuid.UUID = Field(description="UUID of the existing active emergency")
    distance_m: float = Field(description="Distance in meters between the two incident reports")
    priority: str = Field(description="Priority classification of the existing incident")
    created_at: datetime = Field(description="Timestamp when the existing incident was created")
    can_force_create: bool = Field(default=True, description="Indicates whether client may re-submit with force_create=true")

    model_config = ConfigDict(extra="forbid")


class EmergencyEventResponse(BaseModel):
    """Timeline event representation for incident audit and client updates."""
    id: uuid.UUID
    emergency_id: uuid.UUID
    seq: int
    type: str
    actor_user_id: Optional[uuid.UUID] = None
    actor_role: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    visible_to: List[str] = Field(default_factory=list)
    at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EmergencyResponse(BaseModel):
    """Core emergency incident representation returned to API callers (Spec §10.3)."""
    id: uuid.UUID
    patient_user_id: uuid.UUID
    reported_by_user_id: uuid.UUID
    idempotency_key: str
    status: str
    community_track: str
    professional_track: str
    priority: str
    emergency_type: str
    triage: Dict[str, Any] = Field(default_factory=dict)
    dispatch_plan: Dict[str, Any] = Field(default_factory=dict)
    lat: Optional[float] = None
    lng: Optional[float] = None
    location_accuracy_m: float = 10.0
    location_hint: Optional[str] = None
    location_tier: str = Field(default="exact", description="Location privacy level: exact, coarse, or revoked")
    location_revoked: bool = Field(default=False, description="True if coordinates are withheld due to privacy revocation")
    patient_is_reporter: bool = True
    consent_share_medical: bool = False
    version: int = 1
    next_event_seq: int = 1
    demo_session_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    events: Optional[List[EmergencyEventResponse]] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
