from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DailyMail API"
    app_env: str = "local"
    debug: bool = True
    api_prefix: str = "/api"
    auto_create_tables: bool = True

    database_url: str = "postgresql+psycopg://postgres:password@db.project-ref.supabase.co:5432/postgres?sslmode=require"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    allowed_origins: str | list[str] = Field(
        default="http://localhost:5173,http://127.0.0.1:5173"
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def cors_allowed_origins(self) -> list[str]:
        if isinstance(self.allowed_origins, str):
            return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return self.allowed_origins


settings = Settings()
