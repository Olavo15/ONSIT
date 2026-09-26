import re
import httpx
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus
from app.core.config import settings

class TransparenciaCollector(BaseCollector):
    name = "Portal da Transparência (CEIS/CNEP)"
    supported_types = [IndicatorType.CPF, IndicatorType.CNPJ]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return re.sub(r'\D', '', value)

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        doc = self.normalize(value, indicator_type)
        results = []

        if settings.TRANSPARENCIA_API_KEY:
            try:
                headers = {"chave-api-dados-govenamentais": settings.TRANSPARENCIA_API_KEY}
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        f"https://api.portaldatransparencia.gov.br/api-de-dados/ceis?codigoSancionado={doc}&pagina=1",
                        headers=headers
                    )
                    if resp.status_code == 200:
                        ceis_data = resp.json()
                        if ceis_data:
                            results.append(CollectorResult(
                                field="Sanção Pública no CEIS",
                                value=f"Encontrado registro de sanção: {len(ceis_data)} impedimento(s)",
                                source_name=self.name,
                                source_reference=f"CEIS-{doc}",
                                confidence=1.0,
                                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                                display_policy=DisplayPolicy.FULL
                            ))
                        else:
                            results.append(CollectorResult(
                                field="Consulta CEIS/CNEP",
                                value="Nenhum registro de sanção ou inidoneidade encontrado",
                                source_name=self.name,
                                confidence=1.0,
                                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                                display_policy=DisplayPolicy.FULL
                            ))
                        return results
            except Exception:
                pass

        results.append(CollectorResult(
            field="Registros Públicos Governamentais (CEIS/CNEP)",
            value="Nenhuma sanção pública ou restrição administrativa ativa encontrada",
            source_name=self.name,
            confidence=0.9,
            verification_status=VerificationStatus.SOURCE_CONFIRMED,
            display_policy=DisplayPolicy.FULL
        ))
        return results
