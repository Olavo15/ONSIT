import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import Investigation, Indicator, Finding, Entity, Relationship, InvestigationStatus
from app.schemas.schemas import (
    InvestigationCreate, InvestigationResponse, FindingResponse, GraphResponse,
    EntityResponse, RelationshipResponse
)
from app.services.investigation_service import InvestigationService

router = APIRouter()

@router.post("", response_model=InvestigationResponse, status_code=201)
async def create_investigation(
    data: InvestigationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if not data.indicators:
        raise HTTPException(status_code=400, detail="Pelo menos um identificador é necessário para iniciar a investigação")

    # Create Investigation record
    title = data.title or f"Investigação - {data.indicators[0].value}"
    inv = Investigation(title=title, status=InvestigationStatus.PENDING, progress=0.0)
    db.add(inv)
    db.commit()
    db.refresh(inv)

    # Add Indicators
    for ind_data in data.indicators:
        ind = Indicator(
            investigation_id=inv.id,
            type=ind_data.type,
            normalized_value=ind_data.value.strip(),
            display_value=ind_data.value.strip()
        )
        db.add(ind)
    
    db.commit()
    db.refresh(inv)

    # Schedule investigation background collection task
    background_tasks.add_task(
        InvestigationService.run_investigation,
        db,
        inv.id,
        data.subject_name,
        data.api_key
    )

    return inv

@router.get("/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigação não encontrada")
    return inv

@router.get("/{investigation_id}/findings", response_model=List[FindingResponse])
def get_investigation_findings(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigação não encontrada")
    
    findings = db.query(Finding).filter(Finding.investigation_id == investigation_id).all()
    return findings

@router.get("/{investigation_id}/graph", response_model=GraphResponse)
def get_investigation_graph(investigation_id: str, db: Session = Depends(get_db)):
    entities = db.query(Entity).filter(Entity.investigation_id == investigation_id).all()
    relationships = db.query(Relationship).filter(Relationship.investigation_id == investigation_id).all()

    nodes = [EntityResponse.model_validate(e) for e in entities]
    edges = [RelationshipResponse.model_validate(r) for r in relationships]

    return GraphResponse(nodes=nodes, edges=edges)
