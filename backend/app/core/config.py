from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://lifelink_user:lifelink_password@localhost:5432/lifelink_db"
    APP_ENV: str = "development"
    DEMO_MODE_ENABLED: bool = True
    JWT_SECRET: str = "replace_with_min_32_character_secret_key_here"
    EMERGENCY_NUMBER: str = "112"
    DEMO_CENTER_LAT: float = 18.5204
    DEMO_CENTER_LNG: float = 73.8567
    DEFAULT_DEMO_SESSION_ID: str = "00000000-0000-0000-0000-000000000001"

    model_config = SettingsConfigDict(
        env_file=".env",
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
