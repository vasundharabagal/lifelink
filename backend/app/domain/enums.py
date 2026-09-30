"""Domain enumeration types for LIFELINK."""
from enum import Enum


class UserRole(str, Enum):
    """User account roles."""
    CITIZEN = "citizen"
    RESPONDER = "responder"
    AMBULANCE_OPERATOR = "ambulance_operator"
    AUTHORITY = "authority"


class EmergencyType(str, Enum):
    """Primary emergency classification codes."""
    BLEEDING = "BLEEDING"
    UNRESPONSIVE = "UNRESPONSIVE"
    CHOKING = "CHOKING"
    BURNS = "BURNS"
    SEIZURE = "SEIZURE"
    TRAUMA_FALL = "TRAUMA_FALL"
    CHEST_PAIN = "CHEST_PAIN"
    OTHER = "OTHER"


class ConditionCode(str, Enum):
    """Specific detected patient conditions."""
    NOT_BREATHING = "NOT_BREATHING"
    UNRESPONSIVE = "UNRESPONSIVE"
    SEVERE_BLEEDING = "SEVERE_BLEEDING"
    CHOKING = "CHOKING"
    SEIZURE = "SEIZURE"
    BURNS = "BURNS"
    FRACTURE_DISLOCATION = "FRACTURE_DISLOCATION"
    CHEST_PAIN = "CHEST_PAIN"
    HYPOTHERMIA_HEAT = "HYPOTHERMIA_HEAT"


class SkillCode(str, Enum):
    """Responder skill identifiers."""
    CPR_AED = "cpr_aed"
    BLEEDING_CONTROL = "bleeding_control"
    TRAUMA_RESPONSE = "trauma_response"
    BASIC_FIRST_AID = "basic_first_aid"
    ADVANCED_LIFE_SUPPORT = "advanced_life_support"


class ResponderCategory(str, Enum):
    """Professional or volunteer background categories."""
    DOCTOR = "doctor"
    NURSE = "nurse"
    PARAMEDIC = "paramedic"
    EMT = "emt"
    CERTIFIED_FIRST_AIDER = "certified_first_aider"
    MEDICAL_VOLUNTEER = "medical_volunteer"
    STUDENT_RESPONDER = "student_responder"
    SECURITY_PERSONNEL = "security_personnel"
    OTHER = "other"


class ResponderReadiness(str, Enum):
    """Responder availability state."""
    AVAILABLE = "available"
    OFF_DUTY = "off_duty"
    BUSY = "busy"


class CredentialStatus(str, Enum):
    """Verification lifecycle of a responder credential."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class AmbulanceUnitType(str, Enum):
    """Capability tier of ambulance units."""
    BASIC = "basic"
    ADVANCED = "advanced"


class AmbulanceUnitStatus(str, Enum):
    """Operational status of ambulance units."""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


class Priority(str, Enum):
    """Triage priority classification."""
    P1_CRITICAL = "P1_CRITICAL"
    P2_SERIOUS = "P2_SERIOUS"
    P3_STABLE = "P3_STABLE"


class EmergencyStatus(str, Enum):
    """Top-level emergency lifecycle status (Spec §12.1)."""
    CREATED = "CREATED"
    TRIAGED = "TRIAGED"
    DISPATCHING = "DISPATCHING"
    IN_PROGRESS = "IN_PROGRESS"
    HANDED_OVER = "HANDED_OVER"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_COVERAGE_CLOSED = "NO_COVERAGE_CLOSED"


class TrackStatus(str, Enum):
    """Community and professional dispatch track status (Spec §12.2)."""
    NOT_STARTED = "NOT_STARTED"
    SEARCHING = "SEARCHING"
    OFFERED = "OFFERED"
    ASSIGNED = "ASSIGNED"
    ON_SCENE = "ON_SCENE"
    DONE = "DONE"
    UNAVAILABLE = "UNAVAILABLE"
    CANCELLED = "CANCELLED"


class OfferStatus(str, Enum):
    """Dispatch offer lifecycle status (Spec §12.3)."""
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class OfferAction(str, Enum):
    """Actions responder or ambulance operator can take on a dispatch offer (Spec §7.3, CORE-04)."""
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"
    ARRIVE = "ARRIVE"
    SCENE_UNSAFE = "SCENE_UNSAFE"
    COMPLETE = "COMPLETE"


class AuditOutcome(str, Enum):
    """Security authorization decision outcomes."""
    ALLOW = "allow"
    DENY = "deny"


class TargetKind(str, Enum):
    """Dispatch target entity type."""
    RESPONDER = "responder"
    AMBULANCE = "ambulance"


class TrackKind(str, Enum):
    """Independent dispatch tracks."""
    COMMUNITY = "community"
    PROFESSIONAL = "professional"


class ProtocolId(str, Enum):
    """Pre-reviewed first-aid protocol identifiers (Spec §5.5)."""
    PROT_UNRESPONSIVE = "PROT_UNRESPONSIVE"
    PROT_SEVERE_BLEEDING = "PROT_SEVERE_BLEEDING"
    PROT_CHOKING = "PROT_CHOKING"
    PROT_SEIZURE = "PROT_SEIZURE"
    PROT_BURNS = "PROT_BURNS"
    PROT_TRAUMA_FALL = "PROT_TRAUMA_FALL"
    PROT_GENERAL = "PROT_GENERAL"


class EligibilityRejectionReason(str, Enum):
    """Machine-readable hard eligibility rejection reason codes (Spec §6.3, ORCH-01)."""
    NOT_VERIFIED = "NOT_VERIFIED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    ACTIVE_ASSIGNMENT = "ACTIVE_ASSIGNMENT"
    SKILL_MISMATCH = "SKILL_MISMATCH"
    LOCATION_STALE = "LOCATION_STALE"
    LOCATION_UNKNOWN = "LOCATION_UNKNOWN"
    OUTSIDE_SERVICE_RADIUS = "OUTSIDE_SERVICE_RADIUS"
    ALREADY_DECLINED_OR_EXPIRED = "ALREADY_DECLINED_OR_EXPIRED"
    IS_PATIENT = "IS_PATIENT"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    UNIT_NOT_AVAILABLE = "UNIT_NOT_AVAILABLE"
