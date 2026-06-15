from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import secrets
from pathlib import Path
import re
from typing import Optional
import redis
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Allow reading from system environment variables if not found in .env
        case_sensitive=True 
    )

    PROJECT_NAME: str = "MADF User Management API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: Optional[str] = None
    CORS_ORIGINS: Optional[str] = None
    
    # LLM API Configuration
    API_KEY: Optional[str] = None
    MODEL_NAME: Optional[str] = None
    BASE_URL: Optional[str] = None
    
    # 火山引擎视觉大模型配置
    VOLC_API_KEY: Optional[str] = None
    VOLC_VISION_MODEL: Optional[str] = "doubao-vision-pro-12k"
    VOLC_BASE_URL: Optional[str] = "https://aquasearch.volces.com/api/v3/"
    
    @property
    def final_api_key(self) -> str:
        key = self.API_KEY or os.environ.get("API_KEY") or os.environ.get("ZHIPUAI_API_KEY")
        if not key:
            raise ValueError("API_KEY is not set. Please set API_KEY in .env or environment variables.")
        return key

    @property
    def final_model_name(self) -> str:
        return self.MODEL_NAME or os.environ.get("MODEL_NAME") or "glm-4.5"

    @property
    def final_base_url(self) -> str:
        return self.BASE_URL or os.environ.get("BASE_URL") or "https://open.bigmodel.cn/api/paas/v4/"

    @property
    def cors_allow_origins(self) -> list[str]:
        raw = self.CORS_ORIGINS or os.environ.get("CORS_ORIGINS")
        origins: list[str] = []

        if raw:
            for origin in re.split(r"[,\s]+", raw):
                cleaned = origin.strip().rstrip("/")
                if cleaned:
                    origins.append(cleaned)
        else:
            origins.extend([
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ])

        if self.FRONTEND_URL:
            frontend_origin = self.FRONTEND_URL.strip().rstrip("/")
            if frontend_origin:
                origins.append(frontend_origin)

        deduped: list[str] = []
        for origin in origins:
            if origin not in deduped:
                deduped.append(origin)
        return deduped
    
    # Search API Configuration
    SERPAPI_API_KEY: Optional[str] = None
    
    # Security
    SECRET_KEY: Optional[str] = None
    SECRET_KEY_FILE: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database Configuration
    TURSO_DATABASE_URL: Optional[str] = None
    TURSO_AUTH_TOKEN: Optional[str] = None
    DATABASE_URL_OVERRIDE: Optional[str] = None # Renamed from DATABASE_URL to avoid conflict
    
    # Redis Configuration
    # Default to localhost inside the same container or service mesh
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in {"prod", "production", "release"}

    @property
    def final_secret_key(self) -> str:
        default_insecure = "MADF_DEFAULT_INSECURE_SECRET_KEY_PLEASE_CHANGE_IN_PROD"

        if self.SECRET_KEY_FILE:
            key_path = Path(self.SECRET_KEY_FILE)
            if key_path.exists():
                secret = key_path.read_text(encoding="utf-8").strip()
                if secret and secret != default_insecure:
                    return secret

        key = (
            self.SECRET_KEY
            or os.environ.get("SECRET_KEY")
            or os.environ.get("JWT_SECRET_KEY")
            or os.environ.get("APP_SECRET_KEY")
        )
        if key and key != default_insecure:
            return key

        if self.is_production:
            raise ValueError(
                "SECRET_KEY must be set in production. "
                "Provide SECRET_KEY, SECRET_KEY_FILE, or APP_SECRET_KEY."
            )

        runtime_key = getattr(self, "_runtime_secret_key", None)
        if not runtime_key:
            runtime_key = secrets.token_urlsafe(48)
            setattr(self, "_runtime_secret_key", runtime_key)
            logger.warning(
                "SECRET_KEY is not set. Generated a temporary development key "
                "for this process only."
            )
        return runtime_key

    # Determine which database to use
    @property
    def DATABASE_URL(self) -> str:
        # 1. Check environment variable DATABASE_URL first
        env_db = os.environ.get("DATABASE_URL")
        if env_db:
            return env_db
            
        # 2. Turso (Legacy support)
        if self.TURSO_DATABASE_URL and self.TURSO_AUTH_TOKEN:
            return self.TURSO_DATABASE_URL
            
        # 3. Local SQLite (Dev/Docker default)
        if self.DATABASE_URL_OVERRIDE:
             return self.DATABASE_URL_OVERRIDE
        
        return "file:madf.db"

settings = Settings()

# Global Redis Client
redis_client: Optional[redis.Redis] = None

try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    redis_client.ping()
    logger.info(f"Redis connected to {settings.REDIS_URL}")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None
