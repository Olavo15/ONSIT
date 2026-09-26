from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus, SourceType, InvestigationStatus

# Indicator Schemas
class IndicatorCreate(BaseModel):
    type: IndicatorType
    value: str

class IndicatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: IndicatorType
    normalized_value: str
    display_value: str
    created_at: datetime

# Finding Schemas
class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field: str
    value: str
    source_name: str
    source_reference: Optional[str] = None
    confidence: float
    verification_status: VerificationStatus
    display_policy: DisplayPolicy
    retrieved_at: datetime

# Entity & Relationship Graph Schemas
class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    entity_type: str
    metadata_json: Optional[Dict[str, Any]] = None

class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    confidence: float

class GraphResponse(BaseModel):
    nodes: List[EntityResponse]
    edges: List[RelationshipResponse]

# Complaint Schemas
class ComplaintCreate(BaseModel):
    indicator_type: IndicatorType
    indicator: str
    report_type: str
    description: str
    evidence_urls: Optional[List[str]] = []

class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    indicator_type: IndicatorType
    indicator: str
    report_type: str
    description: str
    evidence_urls: List[str]
    reported_at: datetime
    verified: bool

# Investigation Schemas
class InvestigationCreate(BaseModel):
    title: Optional[str] = None
    subject_name: Optional[str] = None # Nome real do titular (opcional)
    api_key: Optional[str] = None # Chave de API do provedor (opcional)
    indicators: List[IndicatorCreate]

class InvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: Optional[str] = None
    status: InvestigationStatus
    progress: float
    created_at: datetime
    updated_at: datetime
    indicators: List[IndicatorResponse] = []
    findings: List[FindingResponse] = []

# Source Schemas
class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: SourceType
    active: bool
    terms_url: Optional[str] = None

# Report Schemas
class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    investigation_id: str
    format: str
    content: str
    created_at: datetime
