import os
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Plataforma OSINT & Antifraude (fraud-recon)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-osint-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./osint_dev.db")
    
    # Redis & Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # API Credentials (Optional with fallback mocks)
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    HIBP_API_KEY: Optional[str] = os.getenv("HIBP_API_KEY")
    URLSCAN_API_KEY: Optional[str] = os.getenv("URLSCAN_API_KEY")
    VIRUSTOTAL_API_KEY: Optional[str] = os.getenv("VIRUSTOTAL_API_KEY")
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    TRANSPARENCIA_API_KEY: Optional[str] = os.getenv("TRANSPARENCIA_API_KEY")
    GOOGLE_SEARCH_API_KEY: Optional[str] = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_SEARCH_CX: Optional[str] = os.getenv("GOOGLE_SEARCH_CX")

    # Provedor Pix autorizado (PSP/participante do arranjo Pix) — NÃO é uma
    # API pública. Só preencha se você tiver um contrato real com um provedor
    # que ofereça acesso ao DICT (ex.: um PSP que já é participante do Pix).
    PIX_PROVIDER_BASE_URL: Optional[str] = os.getenv("PIX_PROVIDER_BASE_URL")
    PIX_PROVIDER_TOKEN: Optional[str] = os.getenv("PIX_PROVIDER_TOKEN")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    class Config:
        case_sensitive = True

settings = Settings()
