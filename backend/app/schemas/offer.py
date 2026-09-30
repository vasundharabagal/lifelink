"""Pydantic schemas for dispatch offers, responder action lifecycle, and pending queries (Spec §7.3, §10.3)."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import OfferAction


class OfferActionRequest(BaseModel):
    """Payload submitted by volunteer responder or ambulance operator to act on an offer."""
    action: OfferAction = Field(..., description="Action to perform: ACCEPT, DECLINE, ARRIVE, SCENE_UNSAFE, COMPLETE")
    decline_reason: Optional[str] = Field(default=None, max_length=100, description="Reason if action is DECLINE")
    actions_reported: List[str] = Field(default_factory=list, description="Checklist of completed first aid actions (e.g. pressure_applied, tourniquet)")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Responder scene notes or safety hazard details")

    model_config = ConfigDict(extra="forbid")


class DispatchOfferResponse(BaseModel):
    """Public projection of a dispatch offer tailored to responder or operator."""
    id: uuid.UUID
    emergency_id: uuid.UUID
    track: str
    target_kind: str
    responder_id: Optional[uuid.UUID] = None
    ambulance_id: Optional[uuid.UUID] = None
    rank: int
    status: str
    offered_at: datetime
    expires_at: datetime
    responded_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    eta_s: Optional[int] = None
    distance_m: Optional[float] = None
    actions_reported: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    scene_safety_warning: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    location_tier: str = Field(default="revoked", description="Location privacy level: exact, coarse, or revoked")
    location_revoked: bool = Field(default=False, description="True if coordinates are withheld due to non-active status")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class PendingOffersResponse(BaseModel):
    """Collection of active pending offers available to the authenticated responder."""
    offers: List[DispatchOfferResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
