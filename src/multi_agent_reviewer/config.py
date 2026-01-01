from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    redis_url: str = Field(default="", validation_alias="REDIS_URL")
    database_url: str = Field(default="", validation_alias="DATABASE_CONNECTION_MAIN")
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")

    github_app_secret: str = Field(default="", validation_alias="GITHUB_APP_SECRET")
    github_client_secret: str = Field(
        default="", validation_alias="GITHUB_APP_CLIENT_SECRET"
    )
    github_private_key: str = Field(
        default="", validation_alias="GITHUB_APP_PRIVATE_KEY"
    )
    github_app_id: str = Field(default="", validation_alias="GITHUB_APP_ID")

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
