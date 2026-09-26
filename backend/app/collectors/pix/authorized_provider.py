import re
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus
from app.core.config import settings

class PixCollector(BaseCollector):
    """
    Integração com o DICT (Diretório de Identificadores de Contas
    Transacionais do Pix) do Banco Central.

    IMPORTANTE: o DICT não é uma API pública. O acesso real de consulta de
    titularidade exige ser uma Instituição Participante do arranjo Pix (ou
    contratar um provedor autorizado/PSP que já tenha esse acesso), com
    autenticação mTLS por instituição. Não existe "chave de API" que um
    desenvolvedor individual possa gerar para isto — por isso este
    collector NUNCA inventa titularidade. Ele só classifica estruturalmente
    a chave e, quando `PIX_PROVIDER_BASE_URL` + `PIX_PROVIDER_TOKEN`
    estiverem configurados (integração via um PSP/parceiro autorizado),
    faz a chamada real a esse provedor.
    """

    name = "Classificador de Chave Pix (estrutural) / Provedor DICT autorizado"
    supported_types = [IndicatorType.PIX, IndicatorType.CPF, IndicatorType.PHONE, IndicatorType.EMAIL]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return value.strip()

    def detect_pix_key_type(self, key: str) -> str:
        clean = re.sub(r'\D', '', key)
        if "@" in key:
            return "EMAIL"
        elif len(clean) == 11 and not key.startswith("+"):
            return "CPF"
        elif len(clean) == 14:
            return "CNPJ"
        elif key.startswith("+") or (len(clean) >= 10 and len(clean) <= 13):
            return "PHONE"
        elif len(key) == 36 and "-" in key:
            return "EVP (Chave Aleatória)"
        return "CHAVE_GERAL"

    async def query_authorized_provider(self, key: str):
        """Chama um provedor/PSP autorizado real, se configurado. Retorna
        None quando não há integração configurada — nunca inventa dado."""
        if not (getattr(settings, "PIX_PROVIDER_BASE_URL", None) and getattr(settings, "PIX_PROVIDER_TOKEN", None)):
            return None
        import httpx
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    f"{settings.PIX_PROVIDER_BASE_URL.rstrip('/')}/dict/entries/{key}",
                    headers={"Authorization": f"Bearer {settings.PIX_PROVIDER_TOKEN}"}
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        key = self.normalize(value, indicator_type)
        results = []
        key_type = self.detect_pix_key_type(key)

        results.append(CollectorResult(
            field="Tipo de Chave Pix (classificação estrutural)",
            value=key_type,
            source_name="Análise estrutural local (regex, sem consulta externa)",
            confidence=0.9,
            verification_status=VerificationStatus.UNVERIFIED,
            display_policy=DisplayPolicy.FULL
        ))

        provider_data = await self.query_authorized_provider(key)

        if provider_data:
            results.append(CollectorResult(
                field="Titularidade Registrada no DICT",
                value=f"{provider_data.get('holder_name', 'N/D')} (documento: {provider_data.get('holder_document', 'N/D')})",
                source_name="Provedor Pix Autorizado (PSP integrado)",
                source_reference=provider_data.get("source", "AUTHORIZED_PIX_PROVIDER"),
                confidence=1.0,
                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                display_policy=DisplayPolicy.FULL
            ))
        else:
            results.append(CollectorResult(
                field="Status do Registro no DICT (Banco Central)",
                value=(
                    "Não verificado nesta instância. A consulta real de titularidade no DICT "
                    "exige integração com uma Instituição Participante do Pix ou um PSP/provedor "
                    "autorizado (autenticação mTLS por instituição financeira) — não é uma API "
                    "pública com chave de desenvolvedor. Configure PIX_PROVIDER_BASE_URL e "
                    "PIX_PROVIDER_TOKEN com as credenciais do seu provedor Pix contratado para "
                    "habilitar esta consulta."
                ),
                source_name=self.name,
                confidence=0.0,
                verification_status=VerificationStatus.UNVERIFIED,
                display_policy=DisplayPolicy.FULL
            ))

        return results
