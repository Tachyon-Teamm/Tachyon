import os
from typing import List, Optional, Dict, Any

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False

def _load_env_file():
    for candidate in [".env", os.path.join(os.getcwd(), ".env"), os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))]:
        if os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass

_load_env_file()

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
        SECRET_KEY: str = os.getenv("SECRET_KEY", "unimm-super-secret-jwt-key-2026-national-platform")
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
        
        # AI Models (Production: BAAI/bge-base-en-v1.5 768-d + CrossEncoder + Gemini/OpenRouter)
        EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
        EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))
        RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
        OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
        LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
        LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
        VLLM_API_BASE: str = os.getenv("VLLM_API_BASE", "http://localhost:8000/v1")
        
        # CORS
        CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]
        
        # Uploads
        UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
        MAX_UPLOAD_SIZE_MB: int = 100
        
        # Matching Weights & Thresholds
        WEIGHT_SEMANTIC: float = 0.40
        WEIGHT_ATTRIBUTE: float = 0.35
        WEIGHT_PROCUREMENT: float = 0.25
        
        THRESHOLD_HIGH: float = 0.90
        THRESHOLD_MEDIUM: float = 0.70
        AUTO_APPROVAL_THRESHOLD: float = float(os.getenv("AUTO_APPROVAL_THRESHOLD", "0.98"))
        
        # CNMC Config
        CNMC_PREFIX: str = "CNMC"
        CNMC_DIGITS: int = 8

    settings = Settings()
else:
    class Settings:
        def __init__(self):
            for k, v in SettingsConfigDict().items() if False else {
                "PROJECT_NAME": "National Unified Material Master Framework (UniMM)",
                "VERSION": "0.1.0",
                "API_V1_STR": "/api/v1",
                "DATABASE_URL": os.getenv("DATABASE_URL", "postgresql+asyncpg://unimm:unimm_dev_password@localhost:5432/unimm_db"),
                "SYNC_DATABASE_URL": os.getenv("SYNC_DATABASE_URL", "postgresql://unimm:unimm_dev_password@localhost:5432/unimm_db"),
                "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                "SECRET_KEY": os.getenv("SECRET_KEY", "unimm-super-secret-jwt-key-2026-national-platform"),
                "ALGORITHM": "HS256",
                "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5"),
                "EMBEDDING_DIMENSION": int(os.getenv("EMBEDDING_DIMENSION", "768")),
                "RERANKER_MODEL": os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
                "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
                "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
                "LLM_PROVIDER": os.getenv("LLM_PROVIDER", "gemini"),
                "LLM_MODEL_NAME": os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash"),
                "VLLM_API_BASE": os.getenv("VLLM_API_BASE", "http://localhost:8000/v1"),
                "CORS_ORIGINS": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
                "UPLOAD_DIR": os.getenv("UPLOAD_DIR", "./uploads"),
                "MAX_UPLOAD_SIZE_MB": 100,
                "WEIGHT_SEMANTIC": 0.40,
                "WEIGHT_ATTRIBUTE": 0.35,
                "WEIGHT_PROCUREMENT": 0.25,
                "THRESHOLD_HIGH": 0.90,
                "THRESHOLD_MEDIUM": 0.70,
                "AUTO_APPROVAL_THRESHOLD": float(os.getenv("AUTO_APPROVAL_THRESHOLD", "0.98")),
                "CNMC_PREFIX": "CNMC",
                "CNMC_DIGITS": 8
            }.items():
                setattr(self, k, v)

    settings = Settings()

