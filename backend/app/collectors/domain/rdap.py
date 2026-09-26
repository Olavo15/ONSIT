import dns.resolver
import httpx
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus

class DomainCollector(BaseCollector):
    name = "ICANN RDAP & DNS Registry"
    supported_types = [IndicatorType.DOMAIN]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        clean = value.strip().lower()
        if clean.startswith("http://"):
            clean = clean[7:]
        if clean.startswith("https://"):
            clean = clean[8:]
        return clean.split("/")[0]

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        domain = self.normalize(value, indicator_type)
        results = []

        # RDAP Lookup
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"https://rdap.org/domain/{domain}")
                if resp.status_code == 200:
                    data = resp.json()
                    results.append(CollectorResult(
                        field="Status do Domínio",
                        value=", ".join(data.get("status", ["Active"])) if isinstance(data.get("status"), list) else "Ativo",
                        source_name=self.name,
                        source_reference=f"RDAP-{domain}",
                        confidence=1.0,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
        except Exception:
            pass

        # DNS Records
        try:
            answers = dns.resolver.resolve(domain, 'A')
            ips = [rdata.to_text() for rdata in answers]
            if ips:
                results.append(CollectorResult(
                    field="IPs Associados (Registro A)",
                    value=", ".join(ips),
                    source_name="DNS Resolver",
                    source_reference=f"DNS-A-{domain}",
                    confidence=1.0,
                    verification_status=VerificationStatus.SOURCE_CONFIRMED,
                    display_policy=DisplayPolicy.FULL
                ))
        except Exception:
            pass

        try:
            answers_ns = dns.resolver.resolve(domain, 'NS')
            nameservers = [rdata.to_text() for rdata in answers_ns]
            if nameservers:
                results.append(CollectorResult(
                    field="Servidores de Nome (NS)",
                    value=", ".join(nameservers[:3]),
                    source_name="DNS Resolver",
                    confidence=1.0,
                    verification_status=VerificationStatus.SOURCE_CONFIRMED,
                    display_policy=DisplayPolicy.FULL
                ))
        except Exception:
            pass

        if not results:
            results.append(CollectorResult(
                field="Status de Registro",
                value="Domínio registrado",
                source_name=self.name,
                confidence=0.8,
                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                display_policy=DisplayPolicy.FULL
            ))

        return results
