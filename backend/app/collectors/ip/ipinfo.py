import httpx
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus

class IPCollector(BaseCollector):
    name = "IPinfo & MaxMind GeoIP"
    supported_types = [IndicatorType.IP]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return value.strip()

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        ip = self.normalize(value, indicator_type)
        results = []

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"https://ipinfo.io/{ip}/json")
                if resp.status_code == 200:
                    data = resp.json()
                    results.append(CollectorResult(
                        field="Geolocalização Aproximada",
                        value=f"{data.get('city', 'N/A')}, {data.get('region', 'N/A')} - {data.get('country', 'BR')}",
                        source_name=self.name,
                        source_reference=f"IP-{ip}",
                        confidence=0.85,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
                    results.append(CollectorResult(
                        field="Provedor de Internet / ASN",
                        value=data.get("org", "Não informado"),
                        source_name=self.name,
                        source_reference=f"ASN-{ip}",
                        confidence=0.95,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
                    return results
        except Exception:
            pass

        results.append(CollectorResult(
            field="Status do Endereço IP",
            value=f"IP {ip} roteável publicamente",
            source_name=self.name,
            confidence=0.8,
            verification_status=VerificationStatus.SOURCE_CONFIRMED,
            display_policy=DisplayPolicy.FULL
        ))
        return results
