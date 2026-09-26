from typing import List
from sqlalchemy.orm import Session
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus, Complaint

class ComplaintsDBCollector(BaseCollector):
    name = "Banco Próprio de Denúncias"
    supported_types = [
        IndicatorType.PHONE, IndicatorType.EMAIL, IndicatorType.CPF,
        IndicatorType.CNPJ, IndicatorType.PIX, IndicatorType.URL, IndicatorType.DOMAIN
    ]

    def __init__(self, db_session: Session = None):
        self.db_session = db_session

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return value.strip()

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        normalized_val = self.normalize(value, indicator_type)
        results = []

        if self.db_session:
            complaints = self.db_session.query(Complaint).filter(
                Complaint.indicator == normalized_val
            ).all()

            if complaints:
                results.append(CollectorResult(
                    field="Denúncias Registradas na Base Colaborativa",
                    value=f"⚠ {len(complaints)} relato(s) associados a este identificador",
                    source_name=self.name,
                    confidence=0.7,
                    verification_status=VerificationStatus.USER_SUBMITTED,
                    display_policy=DisplayPolicy.FULL
                ))
                for c in complaints[:3]:
                    results.append(CollectorResult(
                        field=f"Denúncia [{c.report_type}]",
                        value=f"Relato: {c.description} (Data: {c.reported_at.strftime('%d/%m/%Y')})",
                        source_name=self.name,
                        confidence=0.6,
                        verification_status=VerificationStatus.USER_SUBMITTED,
                        display_policy=DisplayPolicy.FULL
                    ))
                return results

        # Default if clean
        results.append(CollectorResult(
            field="Histórico de Denúncias Internas",
            value="Nenhuma denúncia cadastrada para este identificador no banco próprio",
            source_name=self.name,
            confidence=1.0,
            verification_status=VerificationStatus.SOURCE_CONFIRMED,
            display_policy=DisplayPolicy.FULL
        ))
        return results
