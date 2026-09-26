import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Boolean, Enum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class IndicatorType(str, PyEnum):
    CPF = "CPF"
    CNPJ = "CNPJ"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    PIX = "PIX"
    NAME = "NAME"
    URL = "URL"
    DOMAIN = "DOMAIN"
    USERNAME = "USERNAME"
    IP = "IP"
    HASH = "HASH"

class DisplayPolicy(str, PyEnum):
    FULL = "FULL"
    MASKED = "MASKED"
    HIDDEN = "HIDDEN"

class VerificationStatus(str, PyEnum):
    UNVERIFIED = "UNVERIFIED"
    SOURCE_CONFIRMED = "SOURCE_CONFIRMED"
    USER_SUBMITTED = "USER_SUBMITTED"
    CONTRADICTED = "CONTRADICTED"

class SourceType(str, PyEnum):
    PUBLIC = "PUBLIC"
    GOVERNMENT = "GOVERNMENT"
    AUTHORIZED_PROVIDER = "AUTHORIZED_PROVIDER"
    USER_SUBMITTED = "USER_SUBMITTED"

class InvestigationStatus(str, PyEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="ANALYST")
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(InvestigationStatus), default=InvestigationStatus.PENDING)
    progress = Column(Float, default=0.0) # 0.0 to 100.0
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    indicators = relationship("Indicator", back_populates="investigation", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="investigation", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="investigation", cascade="all, delete-orphan")
    relationships = relationship("Relationship", back_populates="investigation", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="investigation", cascade="all, delete-orphan")

class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    type = Column(Enum(IndicatorType), nullable=False, index=True)
    normalized_value = Column(String, nullable=False, index=True)
    display_value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="indicators")
    findings = relationship("Finding", back_populates="indicator")

class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    type = Column(Enum(SourceType), nullable=False)
    endpoint = Column(String, nullable=True)
    terms_url = Column(String, nullable=True)
    privacy_url = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Entity(Base):
    __tablename__ = "entities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False) # e.g. Person, Company, Domain, Account
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="entities")

class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    source_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    target_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    relation_type = Column(String, nullable=False) # e.g. HAS_PHONE, OWNS_DOMAIN, SHARES_IP
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="relationships")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    indicator_id = Column(String, ForeignKey("indicators.id"), nullable=True)
    entity_id = Column(String, ForeignKey("entities.id"), nullable=True)
    
    field = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    
    source_id = Column(String, ForeignKey("sources.id"), nullable=True)
    source_name = Column(String, nullable=False)
    source_reference = Column(String, nullable=True)
    
    confidence = Column(Float, default=1.0) # 0.0 to 1.0
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.UNVERIFIED)
    display_policy = Column(Enum(DisplayPolicy), default=DisplayPolicy.FULL)
    
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    investigation = relationship("Investigation", back_populates="findings")
    indicator = relationship("Indicator", back_populates="findings")

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    indicator_type = Column(Enum(IndicatorType), nullable=False)
    indicator = Column(String, nullable=False, index=True)
    report_type = Column(String, nullable=False) # e.g. SUSPECTED_SCAM, PHISHING, PIX_FRAUD
    description = Column(Text, nullable=False)
    evidence_urls = Column(JSON, default=list)
    reported_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    target = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    format = Column(String, default="JSON") # JSON, HTML, PDF
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="reports")
