from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ROOT_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://lifelink_user:lifelink_password@localhost:5432/lifelink_db"
    APP_ENV: str = "development"
    DEMO_MODE_ENABLED: bool = True
    JWT_SECRET: str = "replace_with_min_32_character_secret_key_here"
    EMERGENCY_NUMBER: str = "112"
    DEMO_CENTER_LAT: float = 18.5204
    DEMO_CENTER_LNG: float = 73.8567
    DEFAULT_DEMO_SESSION_ID: str = "00000000-0000-0000-0000-000000000001"
    
    # LLM and Triage settings (TRIAGE-04, D-41, D-42, D-43)
    LLM_PROVIDER: str = "none"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 4.0
    LLM_RETRY_TIMEOUT_SECONDS: float = 1.5
    DEMO_DISABLE_LLM: bool = True

    # Response Orchestration constants (Spec §6.1, ORCH-01, ORCH-02, ORCH-04)
    OFFER_TTL_S: int = 30
    DEMO_OFFER_TTL_S: int = 20
    MAX_COMMUNITY_CANDIDATES: int = 5
    MAX_AMBULANCE_CANDIDATES: int = 3
    LOCATION_FRESHNESS_S: int = 300
    DETOUR_FACTOR: float = 1.35
    RESPONDER_SPEED_KMH: float = 25.0
    AMBULANCE_SPEED_KMH: float = 35.0
    ETA_CAP_S: int = 900
    COOLDOWN_AFTER_ASSIGNMENT_S: int = 120

    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR / ".env"), str(_ROOT_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Optional[str]) -> str:
        if not v:
            return "postgresql://lifelink_user:lifelink_password@localhost:5432/lifelink_db"
        
        # Normalize legacy postgres:// to postgresql://
        url = v.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
            
        # Ensure psycopg2 dialect driver is explicit if starting with plain postgresql://
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
            
        return url

    def get_sqlalchemy_database_url(self) -> str:
        return self.DATABASE_URL


settings = Settings()
