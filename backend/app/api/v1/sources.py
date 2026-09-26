from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.get("")
def list_sources():
    """Catálogo inicial de fontes e APIs (Seção 27 da arquitetura)"""
    return [
        {"name": "Receita Federal", "type": "GOVERNMENT", "utilidade": "CNPJ, Razão Social, CNAE, Endereço Empresarial"},
        {"name": "Portal da Transparência", "type": "GOVERNMENT", "utilidade": "CEIS, CNEP, Sanções e Inidoneidades públicas"},
        {"name": "DICT / BCB", "type": "AUTHORIZED_PROVIDER", "utilidade": "Consulta de chaves Pix e titularidade autorizada"},
        {"name": "Twilio Lookup", "type": "AUTHORIZED_PROVIDER", "utilidade": "Validação de linha, país, operadora e tipo"},
        {"name": "Have I Been Pwned", "type": "PUBLIC", "utilidade": "Verificação de vazamento de e-mails em incidentes"},
        {"name": "ICANN RDAP / DNS", "type": "PUBLIC", "utilidade": "Registro de domínios, nameservers e IPs A"},
        {"name": "urlscan.io & VirusTotal", "type": "PUBLIC", "utilidade": "Análise de segurança de URLs, Phishing e Threat Intel"},
        {"name": "GitHub Public API", "type": "PUBLIC", "utilidade": "Perfis públicos, organizações e localização declarada"},
        {"name": "IPinfo / GeoIP", "type": "PUBLIC", "utilidade": "ASN, Provedor e geolocalização aproximada de IPs"},
        {"name": "Banco Próprio de Denúncias", "type": "USER_SUBMITTED", "utilidade": "Relatos de usuários sobre suspeitas de fraudes"}
    ]
