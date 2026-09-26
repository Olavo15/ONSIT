import re
import httpx
import phonenumbers
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus
from app.core.config import settings

class PhoneCollector(BaseCollector):
    name = "Twilio Lookup & Telecom Registry"
    supported_types = [IndicatorType.PHONE]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        clean = re.sub(r'[^\d+]', '', value)
        if not clean.startswith("+"):
            clean = "+55" + clean
        return clean

    def get_ddd_info(self, phone: str):
        clean_digits = re.sub(r'\D', '', phone)
        if clean_digits.startswith("55") and len(clean_digits) >= 4:
            ddd = clean_digits[2:4]
            ddd_map = {
                "11": ("São Paulo — Capital e Região Metropolitana", "Telefônica Brasil S.A. (Vivo)"),
                "19": ("Campinas e Região / Interior SP", "Claro S.A."),
                "21": ("Rio de Janeiro — Capital", "TIM S.A."),
                "31": ("Belo Horizonte / MG", "Telefônica Brasil S.A. (Vivo)"),
                "41": ("Curitiba / PR", "TIM S.A."),
                "51": ("Porto Alegre / RS", "Claro S.A."),
                "61": ("Brasília / DF", "Claro S.A."),
                "71": ("Salvador / BA", "TIM S.A."),
                "81": ("Recife / PE", "Telefônica Brasil S.A. (Vivo)"),
                "85": ("Fortaleza / CE", "Claro S.A."),
                "88": ("Juazeiro do Norte / Sobral / Interior CE", "Telefônica Brasil S.A. (Vivo)"),
                "92": ("Manaus / AM", "Claro S.A.")
            }
            return ddd_map.get(ddd, (f"Região DDD {ddd}", None))
        return ("Região Internacional", None)

    async def lookup_twilio(self, e164_number: str):
        """Consulta real à Twilio Lookup API v2. Retorna None se não houver
        credenciais configuradas ou se a chamada falhar."""
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN):
            return None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://lookups.twilio.com/v2/PhoneNumbers/{e164_number}",
                    params={"Fields": "line_type_intelligence"},
                    auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        normalized_phone = self.normalize(value, indicator_type)
        results = []

        try:
            parsed = phonenumbers.parse(normalized_phone, None)
            is_valid = phonenumbers.is_valid_number(parsed)
            country_code = phonenumbers.region_code_for_number(parsed)
            region_name, _ = self.get_ddd_info(normalized_phone)
            clean_for_lookup = re.sub(r'[^\d+]', '', normalized_phone)

            # 1) Tenta a Twilio Lookup API v2 real, se houver credenciais configuradas.
            twilio_data = await self.lookup_twilio(clean_for_lookup)

            results.append(CollectorResult(
                field="Status da Linha Telefônica",
                value="Válido (estrutura E.164 confirmada)" if is_valid else "Formato Inválido",
                source_name="phonenumbers (libphonenumber)",
                source_reference="ITU-E164",
                confidence=1.0,
                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                display_policy=DisplayPolicy.FULL
            ))

            num_type = phonenumbers.number_type(parsed)
            type_str = "Mobile (Móvel)" if num_type == phonenumbers.PhoneNumberType.MOBILE else "Landline (Fixo)"

            if twilio_data:
                line_intel = twilio_data.get("line_type_intelligence") or {}
                results.append(CollectorResult(
                    field="Tipo da Linha Telefônica (Twilio Lookup)",
                    value=line_intel.get("type", type_str),
                    source_name="Twilio Lookup API v2",
                    source_reference=twilio_data.get("phone_number"),
                    confidence=1.0,
                    verification_status=VerificationStatus.SOURCE_CONFIRMED,
                    display_policy=DisplayPolicy.FULL
                ))
                if line_intel.get("carrier_name"):
                    results.append(CollectorResult(
                        field="Operadora de Telecomunicações (Twilio Lookup)",
                        value=line_intel.get("carrier_name"),
                        source_name="Twilio Lookup API v2",
                        source_reference="line_type_intelligence",
                        confidence=1.0,
                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                        display_policy=DisplayPolicy.FULL
                    ))
            else:
                # Sem credenciais Twilio (ou chamada falhou): entrega só o que é
                # verificável offline, deixando claro que é uma estimativa.
                results.append(CollectorResult(
                    field="Tipo da Linha Telefônica (estimado)",
                    value=type_str,
                    source_name="phonenumbers (libphonenumber) — heurística offline",
                    confidence=0.6,
                    verification_status=VerificationStatus.UNVERIFIED,
                    display_policy=DisplayPolicy.FULL
                ))
                results.append(CollectorResult(
                    field="Operadora de Telecomunicações",
                    value="Não confirmável sem credencial Twilio Lookup (números são portáveis entre operadoras no Brasil desde a Portabilidade Numérica — LGT/ANATEL). Configure TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN para obter a operadora real.",
                    source_name=self.name,
                    confidence=0.0,
                    verification_status=VerificationStatus.UNVERIFIED,
                    display_policy=DisplayPolicy.FULL
                ))

            results.append(CollectorResult(
                field="País de Origem",
                value=f"Brasil ({country_code})" if country_code == "BR" else country_code,
                source_name="phonenumbers (libphonenumber)",
                source_reference="ITU-E164",
                confidence=1.0,
                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                display_policy=DisplayPolicy.FULL
            ))

            results.append(CollectorResult(
                field="Região Geográfica / DDD (tabela pública ANATEL)",
                value=region_name,
                source_name="phonenumbers (libphonenumber) — plano de numeração ANATEL",
                confidence=0.9,
                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                display_policy=DisplayPolicy.FULL
            ))

            # WhatsApp API Direct Link
            clean_num = re.sub(r'\D', '', normalized_phone)
            results.append(CollectorResult(
                field="Link Direto de Perfil Público (WhatsApp)",
                value=f"https://wa.me/{clean_num}",
                source_name="WhatsApp Web Direct",
                source_reference="wa.me",
                confidence=1.0,
                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                display_policy=DisplayPolicy.FULL
            ))

        except Exception:
            results.append(CollectorResult(
                field="Validação de Número",
                value="Formato Não Reconhecido",
                source_name=self.name,
                confidence=0.5,
                verification_status=VerificationStatus.UNVERIFIED,
                display_policy=DisplayPolicy.FULL
            ))

        return results
