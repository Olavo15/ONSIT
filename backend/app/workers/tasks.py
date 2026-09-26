import asyncio
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.investigation_service import InvestigationService

@celery_app.task(name="investigation.run_async")
def run_async_investigation(investigation_id: str):
    """
    Celery Task worker to execute multi-source lookup, entity correlation,
    and report generation asynchronously (Section 21 of architecture).
    """
    db = SessionLocal()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(InvestigationService.run_investigation(db, investigation_id))
        return {"status": "SUCCESS", "investigation_id": investigation_id}
    except Exception as exc:
        return {"status": "FAILED", "error": str(exc)}
    finally:
        db.close()
