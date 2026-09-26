from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("")
def health_check():
    return {
        "status": "healthy",
        "service": "OSINT & Anti-fraud Platform (fraud-recon)",
        "timestamp": datetime.utcnow().isoformat()
    }
