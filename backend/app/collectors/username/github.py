import httpx
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus

class GitHubCollector(BaseCollector):
    name = "GitHub Public API"
    supported_types = [IndicatorType.USERNAME]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        clean = value.strip().lstrip("@")
        return clean

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        username = self.normalize(value, indicator_type)
        results = []

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"https://api.github.com/users/{username}")
                if resp.status_code == 200:
                    data = resp.json()
                    results.append(CollectorResult(
                        field="Perfil Público GitHub",
                        value=f"Nome: {data.get('name') or username} | Login: @{data.get('login')}",
                        source_name=self.name,
                        source_reference=data.get("html_url"),
                        confidence=1.0,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
                    if data.get("company"):
                        results.append(CollectorResult(
                            field="Organização Declarada",
                            value=data.get("company"),
                            source_name=self.name,
                            confidence=0.9,
                            verification_status=VerificationStatus.USER_SUBMITTED,
                            display_policy=DisplayPolicy.FULL
                        ))
                    if data.get("location"):
                        results.append(CollectorResult(
                            field="Localização Declarada no Perfil",
                            value=data.get("location"),
                            source_name=self.name,
                            confidence=0.8,
                            verification_status=VerificationStatus.USER_SUBMITTED,
                            display_policy=DisplayPolicy.FULL
                        ))
                    if data.get("public_repos") is not None:
                        results.append(CollectorResult(
                            field="Repositórios Públicos",
                            value=str(data.get("public_repos")),
                            source_name=self.name,
                            confidence=1.0,
                            verification_status=VerificationStatus.SOURCE_CONFIRMED,
                            display_policy=DisplayPolicy.FULL
                        ))
                    return results
        except Exception:
            pass

        results.append(CollectorResult(
            field="Verificação de Usuário GitHub",
            value=f"Username @{username} não encontrado ou sem dados públicos",
            source_name=self.name,
            confidence=0.5,
            verification_status=VerificationStatus.UNVERIFIED,
            display_policy=DisplayPolicy.FULL
        ))
        return results
