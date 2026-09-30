"""Authentication API endpoints (Spec §8.1)."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    set_session_cookie,
    clear_session_cookie,
)
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User, MedicalProfile
from app.models.responder import ResponderProfile
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    AuthResponse,
    UserResponse,
    UserMeResponse,
    ResponderProfileSummary,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen or responder account",
)
def register(
    body: UserRegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Register a new user account.
    
    Only 'citizen' and 'responder' roles are allowed to self-register (AUTH-01).
    """
    existing_user = db.query(User).filter(User.email == body.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "CONFLICT", "message": "Email is already registered"}},
        )

    pwd_hash = hash_password(body.password)
    user = User(
        email=body.email,
        password_hash=pwd_hash,
        full_name=body.full_name,
        phone=body.phone,
        role=body.role,
        demo_session_id=body.demo_session_id,
        is_active=True,
    )
    db.add(user)
    db.flush()

    if body.role == "responder":
        profile = ResponderProfile(
            user_id=user.id,
            category="other",
            readiness="off_duty",
            service_radius_m=3000,
            acceptance_rate=1.0,
            responses_24h=0,
        )
        db.add(profile)
    elif body.role == "citizen":
        med = MedicalProfile(
            user_id=user.id,
            contacts=[],
            share_during_emergency=False,
        )
        db.add(med)

    db.commit()
    db.refresh(user)

    token = create_access_token(
        user_id=user.id,
        role=user.role,
        demo_session_id=user.demo_session_id,
    )
    set_session_cookie(response, token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=token,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate via email and password",
)
def login(
    body: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate and receive session cookie and token (AUTH-02)."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Invalid email or password"}},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Account is suspended or deactivated"}},
        )

    token = create_access_token(
        user_id=user.id,
        role=user.role,
        demo_session_id=user.demo_session_id,
    )
    set_session_cookie(response, token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=token,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out and clear session cookie",
)
def logout(response: Response):
    """Clear session cookie."""
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get(
    "/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user details and profile",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Return authenticated user profile."""
    resp_profile = None
    if current_user.responder_profile:
        resp_profile = ResponderProfileSummary.model_validate(current_user.responder_profile)

    return UserMeResponse(
        user=UserResponse.model_validate(current_user),
        responder_profile=resp_profile,
    )
