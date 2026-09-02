import os
from typing import List

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False

if HAS_PYDANTIC_SETTINGS:
    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            case_sensitive=True,
            env_file=".env",
            extra="allow"
        )
        
        PROJECT_NAME: str = "National Unified Material Master Framework (UniMM)"
        VERSION: str = "0.1.0"
        API_V1_STR: str = "/api/v1"
        
        # Database
        DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://unimm:unimm_dev_password@localhost:5432/unimm_db")
        SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "postgresql://unimm:unimm_dev_password@localhost:5432/unimm_db")
        
        # Redis
        REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Auth
        SECRET_KEY: str = os.getenv("SECRET_KEY", "unimm-super-secret-jwt-key-2026-cpcl-iocl-bpcl")
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
        
        # Embedding
        EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        EMBEDDING_DIMENSION: int = 384
        
        # CORS
        CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
        
        # Uploads
        UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
        MAX_UPLOAD_SIZE_MB: int = 100
        
        # Matching Weights
        WEIGHT_SEMANTIC: float = 0.40
        WEIGHT_ATTRIBUTE: float = 0.35
        WEIGHT_PROCUREMENT: float = 0.25
        
        THRESHOLD_HIGH: float = 0.90
        THRESHOLD_MEDIUM: float = 0.70
        
        # CNMC Config
        CNMC_PREFIX: str = "CNMC"
        CNMC_DIGITS: int = 8

    settings = Settings()
else:
    class Settings:
        PROJECT_NAME: str = "National Unified Material Master Framework (UniMM)"
        VERSION: str = "0.1.0"
        API_V1_STR: str = "/api/v1"
        DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://unimm:unimm_dev_password@localhost:5432/unimm_db")
        SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "postgresql://unimm:unimm_dev_password@localhost:5432/unimm_db")
        REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        SECRET_KEY: str = os.getenv("SECRET_KEY", "unimm-super-secret-jwt-key-2026-cpcl-iocl-bpcl")
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
        EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        EMBEDDING_DIMENSION: int = 384
        CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
        UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
        MAX_UPLOAD_SIZE_MB: int = 100
        WEIGHT_SEMANTIC: float = 0.40
        WEIGHT_ATTRIBUTE: float = 0.35
        WEIGHT_PROCUREMENT: float = 0.25
        THRESHOLD_HIGH: float = 0.90
        THRESHOLD_MEDIUM: float = 0.70
        CNMC_PREFIX: str = "CNMC"
        CNMC_DIGITS: int = 8

    settings = Settings()
