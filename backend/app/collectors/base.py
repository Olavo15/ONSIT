from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus

class CollectorResult:
    def __init__(
        self,
        field: str,
        value: str,
        source_name: str,
        source_reference: str = None,
        confidence: float = 1.0,
        verification_status: VerificationStatus = VerificationStatus.SOURCE_CONFIRMED,
        display_policy: DisplayPolicy = DisplayPolicy.FULL,
        metadata: Dict[str, Any] = None
    ):
        self.field = field
        self.value = value
        self.source_name = source_name
        self.source_reference = source_reference
        self.confidence = confidence
        self.verification_status = verification_status
        self.display_policy = display_policy
        self.metadata = metadata or {}

class BaseCollector(ABC):
    name: str = "BaseCollector"
    supported_types: List[IndicatorType] = []

    @abstractmethod
    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        """Standardize indicator format (e.g. remove punctuation from CPF/CNPJ or format E.164 phone numbers)"""
        return value.strip()

    @abstractmethod
    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        """Perform lookup against public APIs or data sources and return standard findings"""
        pass
