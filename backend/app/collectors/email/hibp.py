import logging
import httpx
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

class HIBPCollector(BaseCollector):
    name = "Have I Been Pwned"
    supported_types = [IndicatorType.EMAIL]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return value.strip().lower()

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        normalized_email = self.normalize(value, indicator_type)
        results = []

        if settings.HIBP_API_KEY:
            try:
                headers = {
                    "hibp-api-key": settings.HIBP_API_KEY,
                    "user-agent": "OSINT-AntiFraud-Platform"
                }
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        f"https://haveibeenpwned.com/api/v3/breachedaccount/{normalized_email}?truncateResponse=false",
                        headers=headers
                    )
                    if resp.status_code == 200:
                        breaches = resp.json()
                        results.append(CollectorResult(
                            field="Exposição de E-mail (Breaches)",
                            value=f"{len(breaches)} vazamentos conhecidos de dados",
                            source_name=self.name,
                            source_reference="HIBP-v3",
                            confidence=1.0,
                            verification_status=VerificationStatus.SOURCE_CONFIRMED,
                            display_policy=DisplayPolicy.FULL
                        ))
                        for breach in breaches[:5]:
                            results.append(CollectorResult(
                                field=f"Incidente de Exposição: {breach.get('Name')}",
                                value=f"Data: {breach.get('BreachDate')} | Dados: {', '.join(breach.get('DataClasses', []))}",
                                source_name=self.name,
                                source_reference=breach.get('Domain', 'N/A'),
                                confidence=1.0,
                                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                                display_policy=DisplayPolicy.FULL
                            ))
                        return results
                    elif resp.status_code == 404:
                        results.append(CollectorResult(
                            field="Exposição em Breaches",
                            value="Nenhuma exposição conhecida em incidentes de vazamento",
                            source_name=self.name,
                            confidence=1.0,
                            verification_status=VerificationStatus.SOURCE_CONFIRMED,
                            display_policy=DisplayPolicy.FULL
                        ))
                        return results
                    else:
                        logger.warning(
                            "HIBP respondeu status inesperado %s para %s", resp.status_code, normalized_email
                        )
            except Exception:
                logger.warning("Falha ao consultar HIBP para %s", normalized_email, exc_info=True)

        # Fallback gratuito e sem token: XposedOrNot (https://xposedornot.com/api_doc)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"https://api.xposedornot.com/v1/check-email/{normalized_email}")
                if resp.status_code in (200, 404):
                    breach_names = []
                    if resp.status_code == 200:
                        data = resp.json()
                        breach_groups = data.get("breaches", [])
                        # A API às vezes agrupa nomes em listas aninhadas, às vezes retorna
                        # uma lista plana de nomes — nunca itere "group" assumindo o formato.
                        for group in breach_groups:
                            if isinstance(group, str):
                                breach_names.append(group)
                            elif isinstance(group, (list, tuple)):
                                breach_names.extend(str(name) for name in group)
                            elif isinstance(group, dict):
                                name = group.get("breach") or group.get("name") or group.get("Name")
                                if name:
                                    breach_names.append(str(name))

                    if breach_names:
                        results.append(CollectorResult(
                            field="Exposição de E-mail (Breaches)",
                            value=f"{len(breach_names)} vazamento(s) conhecido(s): {', '.join(breach_names[:10])}",
                            source_name="XposedOrNot",
                            source_reference="xposedornot-v1",
                            confidence=0.85,
                            verification_status=VerificationStatus.SOURCE_CONFIRMED,
                            display_policy=DisplayPolicy.FULL
                        ))
                    else:
                        results.append(CollectorResult(
                            field="Exposição em Breaches",
                            value="Nenhuma exposição conhecida em incidentes de vazamento (consultado via XposedOrNot)",
                            source_name="XposedOrNot",
                            confidence=0.85,
                            verification_status=VerificationStatus.SOURCE_CONFIRMED,
                            display_policy=DisplayPolicy.FULL
                        ))
                    return results
                else:
                    logger.warning(
                        "XposedOrNot respondeu status inesperado %s para %s", resp.status_code, normalized_email
                    )
        except Exception:
            logger.warning("Falha ao consultar XposedOrNot para %s", normalized_email, exc_info=True)

        # Nenhuma fonte respondeu: não afirmar nada que não foi verificado
        results.append(CollectorResult(
            field="Exposição em Breaches",
            value="Não verificado: nenhuma fonte de vazamentos (HIBP/XposedOrNot) respondeu nesta consulta",
            source_name=self.name,
            confidence=0.0,
            verification_status=VerificationStatus.UNVERIFIED,
            display_policy=DisplayPolicy.FULL
        ))
        return results
