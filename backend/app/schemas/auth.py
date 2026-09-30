"""Authentication request and response schemas."""
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from app.core.security import validate_password_strength


class UserRegisterRequest(BaseModel):
    """Registration payload restricted to citizen and responder roles (AUTH-01)."""
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    role: str = "citizen"
    demo_session_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        normalized = v.lower().strip()
        if normalized not in ("citizen", "responder"):
            raise ValueError("Only 'citizen' and 'responder' roles may self-register")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class UserLoginRequest(BaseModel):
    """Login payload with email and password."""
    email: EmailStr
    password: str

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    """Public user entity representation."""
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    demo_session_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    """Authentication response containing user data and JWT token."""
    user: UserResponse
    token: str


class ResponderProfileSummary(BaseModel):
    """Summary of responder profile attributes for /auth/me."""
    category: str
    readiness: str
    service_radius_m: int
    last_lat: Optional[float] = None
    last_lng: Optional[float] = None
    pinned_location: bool = False
    acceptance_rate: float
    responses_24h: int

    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(BaseModel):
    """User profile response for /auth/me."""
    user: UserResponse
    responder_profile: Optional[ResponderProfileSummary] = None
