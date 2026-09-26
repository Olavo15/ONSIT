import re
import httpx
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus
from app.core.config import settings

class HashCollector(BaseCollector):
    """Consulta reputação de hash (MD5/SHA1/SHA256) via VirusTotal API v3.
    Requer VIRUSTOTAL_API_KEY (gratuita, com limite de 4 requisições/min).
    https://www.virustotal.com/gui/join-us
    """
    name = "VirusTotal (Threat Intelligence)"
    supported_types = [IndicatorType.HASH]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return re.sub(r'[^a-fA-F0-9]', '', value.strip())

    def _hash_kind(self, h: str) -> str:
        return {32: "MD5", 40: "SHA1", 64: "SHA256"}.get(len(h), "DESCONHECIDO")

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        file_hash = self.normalize(value, indicator_type)
        results = []
        kind = self._hash_kind(file_hash)

        results.append(CollectorResult(
            field="Formato do Hash",
            value=f"{kind} ({len(file_hash)} caracteres hexadecimais)" if kind != "DESCONHECIDO"
                  else "Formato não reconhecido (esperado MD5/SHA1/SHA256)",
            source_name="Validação estrutural local",
            confidence=1.0 if kind != "DESCONHECIDO" else 0.0,
            verification_status=VerificationStatus.SOURCE_CONFIRMED if kind != "DESCONHECIDO" else VerificationStatus.UNVERIFIED,
            display_policy=DisplayPolicy.FULL
        ))

        if kind == "DESCONHECIDO":
            return results

        if not settings.VIRUSTOTAL_API_KEY:
            results.append(CollectorResult(
                field="Reputação de Ameaça (VirusTotal)",
                value=(
                    "Não consultado: VIRUSTOTAL_API_KEY não configurada. "
                    "Crie uma chave gratuita em https://www.virustotal.com/gui/join-us "
                    "e defina VIRUSTOTAL_API_KEY no .env para habilitar esta verificação."
                ),
                source_name=self.name,
                confidence=0.0,
                verification_status=VerificationStatus.UNVERIFIED,
                display_policy=DisplayPolicy.FULL
            ))
            return results

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"https://www.virustotal.com/api/v3/files/{file_hash}",
                    headers={"x-apikey": settings.VIRUSTOTAL_API_KEY}
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {}).get("attributes", {})
                    stats = data.get("last_analysis_stats", {})
                    malicious = stats.get("malicious", 0)
                    suspicious = stats.get("suspicious", 0)
                    total = sum(stats.values()) if stats else 0

                    results.append(CollectorResult(
                        field="Veredito de Antivírus (VirusTotal)",
                        value=f"{malicious} maliciosos + {suspicious} suspeitos de {total} motores de análise",
                        source_name=self.name,
                        source_reference=f"https://www.virustotal.com/gui/file/{file_hash}",
                        confidence=1.0,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
                    if data.get("meaningful_name") or data.get("type_description"):
                        results.append(CollectorResult(
                            field="Identificação do Arquivo",
                            value=f"{data.get('meaningful_name', 'N/D')} ({data.get('type_description', 'N/D')})",
                            source_name=self.name,
                            confidence=0.95,
                            verification_status=VerificationStatus.SOURCE_CONFIRMED,
                            display_policy=DisplayPolicy.FULL
                        ))
                elif resp.status_code == 404:
                    results.append(CollectorResult(
                        field="Reputação de Ameaça (VirusTotal)",
                        value="Hash não encontrado na base do VirusTotal (arquivo nunca submetido/analisado)",
                        source_name=self.name,
                        confidence=0.8,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
                else:
                    results.append(CollectorResult(
                        field="Reputação de Ameaça (VirusTotal)",
                        value=f"Consulta falhou (HTTP {resp.status_code})",
                        source_name=self.name,
                        confidence=0.0,
                        verification_status=VerificationStatus.UNVERIFIED,
                        display_policy=DisplayPolicy.FULL
                    ))
        except Exception as e:
            results.append(CollectorResult(
                field="Reputação de Ameaça (VirusTotal)",
                value=f"Erro ao consultar API: {type(e).__name__}",
                source_name=self.name,
                confidence=0.0,
                verification_status=VerificationStatus.UNVERIFIED,
                display_policy=DisplayPolicy.FULL
            ))

        return results
