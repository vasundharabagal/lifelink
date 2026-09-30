from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    set_session_cookie,
    clear_session_cookie,
)
from app.core.clock import Clock, get_clock
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
from app.services.audit import (
    extract_client_ip,
    log_login_attempt,
    log_security_event,
)
from app.services.rate_limiter import check_login_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen or responder account",
)
def register(
    body: UserRegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
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

    log_security_event(
        action="auth_register",
        resource_type="user",
        resource_id=user.email,
        outcome="allow",
        actor_user_id=user.id,
        actor_role=user.role,
        client_ip=extract_client_ip(request),
        at=clock.now(user.demo_session_id, db),
        db=db,
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
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate via email and password",
)
def login(
    body: UserLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    """Authenticate and receive session cookie and token (AUTH-02, AUTH-06)."""
    normalized_email = body.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    demo_session_id = user.demo_session_id if user else None

    # Check login rate limit (AUTH-06, D-31)
    check_login_rate_limit(normalized_email, db, clock, demo_session_id=demo_session_id)

    if not user or not verify_password(body.password, user.password_hash):
        log_login_attempt(
            email=normalized_email,
            success=False,
            user=user,
            request=request,
            clock=clock,
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Invalid email or password"}},
        )

    if not user.is_active:
        log_login_attempt(
            email=normalized_email,
            success=False,
            user=user,
            request=request,
            clock=clock,
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Account is suspended or deactivated"}},
        )

    log_login_attempt(
        email=normalized_email,
        success=True,
        user=user,
        request=request,
        clock=clock,
        db=db,
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
def logout(request: Request, response: Response):
    """Clear session cookie."""
    clear_session_cookie(response)
    log_security_event(
        action="auth_logout",
        resource_type="session",
        resource_id="session",
        outcome="allow",
        client_ip=extract_client_ip(request),
    )
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
