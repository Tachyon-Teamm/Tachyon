from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import async_engine, Base, sync_engine
from app.api.v1.router import api_router
from app.db.init_db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema is created and seeded
    try:
        from app.models.models import Base
        Base.metadata.create_all(bind=sync_engine)
        init_db()
        print("[UniMM Backend] Database initialized and seeded successfully.")
    except Exception as e:
        print(f"[UniMM Backend] Database startup check: {e}")
    yield
    # Shutdown
    await async_engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise National Unified Material Master Framework (Zero-Training Neuro-Symbolic Multi-CPSE Architecture)",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local Docker and dev workflows
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "Zero-Training Neuro-Symbolic Engine"
    }
