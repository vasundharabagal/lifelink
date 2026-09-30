"""FastAPI request dependencies for authentication and database sessions."""
from typing import Optional
import uuid
from fastapi import Depends, HTTPException, Request, Response
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.user import User


def set_session_cookie(response: Response, token: str) -> None:
    """Attach secure httpOnly JWT session cookie to response (AUTH-02, D-26)."""
    is_prod = settings.APP_ENV == "production"
    response.set_cookie(
        key="ll_session",
        value=token,
        max_age=12 * 3600,
        httponly=True,
        path="/",
        secure=is_prod,
        samesite="strict" if is_prod else "lax",
    )


def clear_session_cookie(response: Response) -> None:
    """Clear httpOnly session cookie on logout."""
    is_prod = settings.APP_ENV == "production"
    response.delete_cookie(
        key="ll_session",
        path="/",
        httponly=True,
        secure=is_prod,
        samesite="strict" if is_prod else "lax",
    )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Extract authenticated user via dual cookie/Bearer transport and verify in DB (AUTH-02, D-25, D-27)."""
    token: Optional[str] = request.cookies.get("ll_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer ") :].strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Authentication required"}},
        )

    try:
        payload = decode_access_token(token)
    except PyJWTError:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Invalid or expired session token"}},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Malformed session token"}},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Invalid user identifier in token"}},
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "User not found"}},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Account is suspended or deactivated"}},
        )

    return user
