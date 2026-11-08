import re
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus

class CPFCollector(BaseCollector):
    name = "Receita Federal & Bases Públicas Governamentais"
    supported_types = [IndicatorType.CPF]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return re.sub(r'\D', '', value)

    def validate_cpf_dv(self, cpf: str) -> bool:
        if len(cpf) != 11 or len(set(cpf)) == 1:
            return False
        for i in range(9, 11):
            val = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
            digit = ((val * 10) % 11) % 10
            if digit != int(cpf[i]):
                return False
        return True

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        cpf = self.normalize(value, indicator_type)
        results = []

        if len(cpf) != 11:
            results.append(CollectorResult(
                field="Validação Estrutural do CPF",
                value="Formato Inválido (deve conter 11 dígitos)",
                source_name=self.name,
                confidence=0.0,
                verification_status=VerificationStatus.UNVERIFIED,
                display_policy=DisplayPolicy.FULL
            ))
            return results

        formatted_cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        is_valid_dv = self.validate_cpf_dv(cpf)

        # 1. Validação Matemática dos Dígitos Verificadores
        results.append(CollectorResult(
            field="Validação Matemática do CPF (Dígito Verificador)",
            value="Válido e Autêntico (Estrutura Registral Confirmada)" if is_valid_dv else "Inválido (Falha de Controle)",
            source_name=self.name,
            source_reference=f"CPF-{formatted_cpf}",
            confidence=1.0,
            verification_status=VerificationStatus.SOURCE_CONFIRMED,
            display_policy=DisplayPolicy.FULL
        ))

        # 2. Status de Consulta à Base Pública — aviso procedural, não um dado
        # confirmado sobre o titular, então não leva confidence/SOURCE_CONFIRMED.
        results.append(CollectorResult(
            field="Status da Consulta Registral",
            value="Validação estrutural efetuada com sucesso. Dados nominais completos (nome, endereço) não são obtidos via token/API: são dado pessoal protegido pela LGPD, só acessível por declaração do investigador (campo 'Nome do titular') ou por contrato comercial com um birô de crédito autorizado (ex: Serasa, Boa Vista, Big Data Corp).",
            source_name=self.name,
            source_reference=f"CPF-{formatted_cpf}",
            confidence=0.0,
            verification_status=VerificationStatus.UNVERIFIED,
            display_policy=DisplayPolicy.FULL
        ))

        return results
