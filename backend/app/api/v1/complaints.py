from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import Complaint
from app.schemas.schemas import ComplaintCreate, ComplaintResponse

router = APIRouter()

@router.post("", response_model=ComplaintResponse, status_code=201)
def create_complaint(data: ComplaintCreate, db: Session = Depends(get_db)):
    complaint = Complaint(
        indicator_type=data.indicator_type,
        indicator=data.indicator.strip(),
        report_type=data.report_type,
        description=data.description,
        evidence_urls=data.evidence_urls or []
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint

@router.get("", response_model=List[ComplaintResponse])
def list_complaints(db: Session = Depends(get_db)):
    return db.query(Complaint).order_by(Complaint.reported_at.desc()).limit(50).all()
