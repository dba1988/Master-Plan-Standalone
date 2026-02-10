from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
import json


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://masterplan:masterplan_dev@localhost:5432/masterplan",
        env="DATABASE_URL"
    )

    # Auth
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    jwt_expire_minutes: int = Field(default=15, env="JWT_EXPIRE_MINUTES")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # CORS
    cors_origins_str: str = Field(
        default='["http://localhost:3001"]',
        env="CORS_ORIGINS"
    )

    @property
    def cors_origins(self) -> List[str]:
        return json.loads(self.cors_origins_str)

    # R2/S3 Storage (MinIO locally, R2 in production)
    r2_endpoint: str = Field(default="http://localhost:9000", env="R2_ENDPOINT")
    r2_access_key_id: str = Field(default="minioadmin", env="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str = Field(default="minioadmin", env="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="masterplan", env="R2_BUCKET")
    r2_region: str = Field(default="us-east-1", env="R2_REGION")

    # CDN (optional, for production)
    cdn_base_url: str = Field(default="", env="CDN_BASE_URL")
    cdn_hmac_secret: str = Field(default="dev-hmac-secret", env="CDN_HMAC_SECRET")

    @property
    def use_cdn(self) -> bool:
        return bool(self.cdn_base_url)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
