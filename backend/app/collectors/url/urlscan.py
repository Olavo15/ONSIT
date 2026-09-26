import base64
import httpx
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus
from app.core.config import settings

class URLScanCollector(BaseCollector):
    name = "urlscan.io & VirusTotal"
    supported_types = [IndicatorType.URL]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        clean = value.strip()
        if not clean.startswith("http://") and not clean.startswith("https://"):
            clean = "https://" + clean
        return clean

    async def check_virustotal(self, url: str) -> List[CollectorResult]:
        """VirusTotal API v3 — reputação de URL entre ~70 motores de antivírus/anti-phishing.
        Requer VIRUSTOTAL_API_KEY (gratuita: https://www.virustotal.com/gui/join-us)."""
        results = []
        if not settings.VIRUSTOTAL_API_KEY:
            return results
        try:
            url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    f"https://www.virustotal.com/api/v3/urls/{url_id}",
                    headers={"x-apikey": settings.VIRUSTOTAL_API_KEY}
                )
                if resp.status_code == 200:
                    attrs = resp.json().get("data", {}).get("attributes", {})
                    stats = attrs.get("last_analysis_stats", {})
                    malicious = stats.get("malicious", 0)
                    suspicious = stats.get("suspicious", 0)
                    total = sum(stats.values()) if stats else 0
                    results.append(CollectorResult(
                        field="Reputação da URL (VirusTotal)",
                        value=f"{malicious} maliciosos + {suspicious} suspeitos de {total} motores de análise",
                        source_name="VirusTotal",
                        source_reference=f"https://www.virustotal.com/gui/url/{url_id}",
                        confidence=1.0,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
                elif resp.status_code == 404:
                    results.append(CollectorResult(
                        field="Reputação da URL (VirusTotal)",
                        value="URL ainda não indexada/analisada pelo VirusTotal",
                        source_name="VirusTotal",
                        confidence=0.7,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
        except Exception:
            pass
        return results

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        url = self.normalize(value, indicator_type)
        results = []

        results.extend(await self.check_virustotal(url))

        try:
            domain = url.split("//")[-1].split("/")[0]
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"https://urlscan.io/api/v1/search/?q=domain:{domain}")
                if resp.status_code == 200:
                    data = resp.json()
                    total = data.get("total", 0)
                    results.append(CollectorResult(
                        field="Histórico de Scans no urlscan.io",
                        value=f"{total} scans registrados",
                        source_name="urlscan.io",
                        source_reference=domain,
                        confidence=1.0,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
                    if data.get("results") and len(data["results"]) > 0:
                        first = data["results"][0]
                        page = first.get("page", {})
                        results.append(CollectorResult(
                            field="Título da Página Detectada",
                            value=page.get("title", "Sem título"),
                            source_name="urlscan.io",
                            confidence=0.9,
                            verification_status=VerificationStatus.SOURCE_CONFIRMED,
                            display_policy=DisplayPolicy.FULL
                        ))
                        results.append(CollectorResult(
                            field="Servidor de Hospedagem / IP",
                            value=f"{page.get('ip', 'N/A')} ({page.get('country', 'BR')})",
                            source_name="urlscan.io",
                            confidence=0.9,
                            verification_status=VerificationStatus.SOURCE_CONFIRMED,
                            display_policy=DisplayPolicy.FULL
                        ))
                    return results
        except Exception:
            pass

        results.append(CollectorResult(
            field="Histórico de Scans no urlscan.io",
            value="Consulta ao urlscan.io indisponível ou sem registros para este domínio no momento",
            source_name="urlscan.io",
            confidence=0.0,
            verification_status=VerificationStatus.UNVERIFIED,
            display_policy=DisplayPolicy.FULL
        ))
        return results
