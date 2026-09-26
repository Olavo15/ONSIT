import pytest
from app.models.models import IndicatorType
from app.collectors.cpf.receita_cpf import CPFCollector
from app.collectors.cnpj.receita import ReceitaFederalCollector
from app.collectors.phone.twilio import PhoneCollector
from app.collectors.email.hibp import HIBPCollector
from app.collectors.domain.rdap import DomainCollector
from app.evidence.provenance import ProvenanceRecord
from app.models.models import DisplayPolicy, VerificationStatus

@pytest.mark.asyncio
async def test_cpf_collector():
    collector = CPFCollector()
    norm = collector.normalize("072.378.543-05", IndicatorType.CPF)
    assert norm == "07237854305"
    
    results = await collector.fetch(IndicatorType.CPF, norm)
    assert len(results) >= 3

@pytest.mark.asyncio
async def test_cnpj_collector():
    collector = ReceitaFederalCollector()
    norm = collector.normalize("00.000.000/0001-91", IndicatorType.CNPJ)
    assert norm == "00000000000191"
    
    results = await collector.fetch(IndicatorType.CNPJ, norm)
    assert len(results) >= 2

@pytest.mark.asyncio
async def test_phone_collector():
    collector = PhoneCollector()
    norm = collector.normalize("88 99999-9999", IndicatorType.PHONE)
    assert norm.startswith("+55")

    results = await collector.fetch(IndicatorType.PHONE, norm)
    assert len(results) >= 2

def test_provenance_record():
    record = ProvenanceRecord(
        field="CPF",
        value="71645678912",
        source_name="DICT",
        display_policy=DisplayPolicy.MASKED
    )
    masked = record.format_value_for_display()
    assert "***" in masked
