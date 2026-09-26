import asyncio
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session

from app.models.models import (
    Investigation, Indicator, Finding, Entity, Relationship,
    InvestigationStatus, IndicatorType, DisplayPolicy, VerificationStatus
)
from app.collectors.cpf.receita_cpf import CPFCollector
from app.collectors.cnpj.receita import ReceitaFederalCollector
from app.collectors.phone.twilio import PhoneCollector
from app.collectors.email.hibp import HIBPCollector
from app.collectors.domain.rdap import DomainCollector
from app.collectors.url.urlscan import URLScanCollector
from app.collectors.username.github import GitHubCollector
from app.collectors.username.social_presence import SocialPresenceCollector
from app.collectors.pix.authorized_provider import PixCollector
from app.collectors.transparency.portal import TransparenciaCollector
from app.collectors.ip.ipinfo import IPCollector
from app.collectors.hash.virustotal import HashCollector
from app.collectors.search.web_search import SearchEngineCollector
from app.collectors.complaints.complaints_db import ComplaintsDBCollector
from app.correlation.entity_resolution import EntityResolutionEngine
from app.evidence.provenance import ProvenanceRecord

class InvestigationService:

    @staticmethod
    def get_collectors_for_type(db: Session, ind_type: IndicatorType):
        collectors = []
        search_collector = SearchEngineCollector()
        complaints_collector = ComplaintsDBCollector(db)

        if ind_type == IndicatorType.CPF:
            collectors.extend([CPFCollector(), TransparenciaCollector(), PixCollector(), search_collector, complaints_collector])
        elif ind_type == IndicatorType.CNPJ:
            collectors.extend([ReceitaFederalCollector(), TransparenciaCollector(), search_collector, complaints_collector])
        elif ind_type == IndicatorType.PHONE:
            collectors.extend([PhoneCollector(), PixCollector(), search_collector, complaints_collector])
        elif ind_type == IndicatorType.EMAIL:
            collectors.extend([HIBPCollector(), PixCollector(), search_collector, complaints_collector])
        elif ind_type == IndicatorType.DOMAIN:
            collectors.extend([DomainCollector(), search_collector, complaints_collector])
        elif ind_type == IndicatorType.URL:
            collectors.extend([URLScanCollector(), search_collector, complaints_collector])
        elif ind_type == IndicatorType.USERNAME:
            collectors.extend([GitHubCollector(), SocialPresenceCollector(), search_collector, complaints_collector])
        elif ind_type == IndicatorType.IP:
            collectors.extend([IPCollector(), search_collector])
        elif ind_type == IndicatorType.PIX:
            collectors.extend([PixCollector(), search_collector, complaints_collector])
        elif ind_type == IndicatorType.HASH:
            collectors.extend([HashCollector()])
        else:
            collectors.extend([search_collector, complaints_collector])
        return collectors

    @classmethod
    async def run_investigation(cls, db: Session, investigation_id: str, subject_name: str = None, api_key: str = None):
        inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not inv:
            return

        inv.status = InvestigationStatus.PROCESSING
        inv.progress = 10.0
        db.commit()

        indicators = db.query(Indicator).filter(Indicator.investigation_id == investigation_id).all()
        total_indicators = len(indicators)
        if total_indicators == 0:
            inv.status = InvestigationStatus.COMPLETED
            inv.progress = 100.0
            db.commit()
            return

        all_findings = []

        # If user explicitly provided the subject's real name, register it as verified finding
        if subject_name and subject_name.strip():
            clean_name = subject_name.strip().upper()
            finding_name = Finding(
                investigation_id=investigation_id,
                indicator_id=indicators[0].id,
                field="Nome Completo do Titular (Identidade Declarada/Confirmada)",
                value=clean_name,
                source_name="Identidade Informada pelo Investigador",
                source_reference=f"USER-INPUT-{clean_name[:10]}",
                confidence=1.0,
                verification_status=VerificationStatus.USER_SUBMITTED,
                display_policy=DisplayPolicy.FULL,
                retrieved_at=datetime.utcnow()
            )
            db.add(finding_name)
            all_findings.append({
                "field": finding_name.field,
                "value": finding_name.value,
                "source_name": finding_name.source_name,
                "confidence": 1.0
            })

        # Run primary collectors (Receita CNPJ, HIBP, GitHub, RDAP, DDG Web Search, Transparência, DICT)
        for idx, ind in enumerate(indicators):
            collectors = cls.get_collectors_for_type(db, ind.type)
            for collector in collectors:
                try:
                    norm_val = collector.normalize(ind.normalized_value, ind.type)
                    collector_results = await collector.fetch(ind.type, norm_val)

                    for res in collector_results:
                        prov = ProvenanceRecord(
                            field=res.field,
                            value=res.value,
                            source_name=res.source_name,
                            source_reference=res.source_reference,
                            verification_status=res.verification_status,
                            display_policy=res.display_policy
                        )

                        finding = Finding(
                            investigation_id=investigation_id,
                            indicator_id=ind.id,
                            field=prov.field,
                            value=prov.format_value_for_display(),
                            source_name=prov.source_name,
                            source_reference=prov.source_reference,
                            confidence=res.confidence,
                            verification_status=prov.verification_status,
                            display_policy=prov.display_policy,
                            retrieved_at=prov.retrieved_at
                        )
                        db.add(finding)
                        all_findings.append({
                            "field": finding.field,
                            "value": finding.value,
                            "source_name": finding.source_name,
                            "confidence": finding.confidence
                        })

                except Exception as e:
                    print(f"Error running collector {collector.name}: {e}")

            inv.progress = 20.0 + ((idx + 1) / total_indicators) * 60.0
            db.commit()

        # Step 3: Entity Resolution & Graph generation
        inv.progress = 85.0
        db.commit()

        ind_dicts = [{"display_value": i.display_value, "type": i.type.value} for i in indicators]
        nodes, edges = EntityResolutionEngine.resolve_entities_and_graph(
            investigation_id, ind_dicts, all_findings
        )

        # Store entities and relationships
        entity_id_map = {}
        for n in nodes:
            ent = Entity(
                investigation_id=investigation_id,
                name=n["name"],
                entity_type=n["entity_type"],
                metadata_json=n["metadata_json"]
            )
            db.add(ent)
            db.flush()
            entity_id_map[n["id"]] = ent.id

        for e in edges:
            src_id = entity_id_map.get(e["source_entity_id"])
            tgt_id = entity_id_map.get(e["target_entity_id"])
            if src_id and tgt_id:
                rel = Relationship(
                    investigation_id=investigation_id,
                    source_entity_id=src_id,
                    target_entity_id=tgt_id,
                    relation_type=e["relation_type"],
                    confidence=e["confidence"]
                )
                db.add(rel)

        inv.status = InvestigationStatus.COMPLETED
        inv.progress = 100.0
        db.commit()
