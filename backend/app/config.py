from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings driven by environment variables."""

    PROJECT_NAME: str = "Wind Forecast Insights API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # CORS configuration: accept list of strings or comma-separated string
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Official Elexon Insights Solution base URL
    ELEXON_BASE_URL: str = "https://data.elexon.co.uk/bmrs/api/v1"

    # Sample Day-Ahead decision cutoff assumption (UTC)
    # Note: 09:50 UTC is a configurable N2EX sample, not a universal UK cutoff
    DEFAULT_DECISION_CUTOFF_TIME: str = "09:50"

    # Evaluation horizon: decisions made in January 2026
    DECISION_START_DATE: str = "2026-01-01"
    DECISION_END_DATE: str = "2026-01-31"

    # Corresponding day-ahead physical delivery dates (D+1)
    DELIVERY_START_DATE: str = "2026-01-02"
    DELIVERY_END_DATE: str = "2026-02-01"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return [str(v)]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
