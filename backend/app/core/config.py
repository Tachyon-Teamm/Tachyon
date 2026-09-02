import os
from typing import List

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
        SECRET_KEY: str = os.getenv("SECRET_KEY", "unimm-super-secret-jwt-key-2026-cpcl-iocl-bpcl")
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
        
        # AI Models (Harmonized defaults: 384 for CPU/local, 1024 if BAAI/bge-m3 configured)
        EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        SPARSE_MODEL: str = os.getenv("SPARSE_MODEL", "naver/splade-v3")
        RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-large")
        VLLM_API_BASE: str = os.getenv("VLLM_API_BASE", "http://localhost:8000/v1")
        LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-14B-Instruct")
        
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
        EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        SPARSE_MODEL: str = os.getenv("SPARSE_MODEL", "naver/splade-v3")
        RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-large")
        VLLM_API_BASE: str = os.getenv("VLLM_API_BASE", "http://localhost:8000/v1")
        LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-14B-Instruct")
        CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]
        UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
        MAX_UPLOAD_SIZE_MB: int = 100
        WEIGHT_SEMANTIC: float = 0.40
        WEIGHT_ATTRIBUTE: float = 0.35
        WEIGHT_PROCUREMENT: float = 0.25
        THRESHOLD_HIGH: float = 0.90
        THRESHOLD_MEDIUM: float = 0.70
        AUTO_APPROVAL_THRESHOLD: float = float(os.getenv("AUTO_APPROVAL_THRESHOLD", "0.98"))
        CNMC_PREFIX: str = "CNMC"
        CNMC_DIGITS: int = 8

    settings = Settings()

