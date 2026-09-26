from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import investigations, complaints, reports, sources, health

# Create database tables if not created
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(investigations.router, prefix=f"{settings.API_V1_STR}/investigations", tags=["Investigations"])
app.include_router(complaints.router, prefix=f"{settings.API_V1_STR}/complaints", tags=["Complaints"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["Reports"])
app.include_router(sources.router, prefix=f"{settings.API_V1_STR}/sources", tags=["Sources"])
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["Health"])

@app.get("/")
def root():
    return {
        "message": "Plataforma de OSINT, Antifraude e Correlação de Evidências (fraud-recon)",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR
    }
