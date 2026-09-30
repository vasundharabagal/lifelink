from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    db: str
    version: str
    demo_mode: bool
    timestamp: str
    environment: str


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    db_status = "error"
    try:
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            db_status = "ok"
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok",
        db=db_status,
        version="1.0",
        demo_mode=settings.DEMO_MODE_ENABLED,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=settings.APP_ENV,
    )
